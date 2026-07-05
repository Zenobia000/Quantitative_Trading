"""After-close scheduler core — the last blocker to collecting live OOS.

The paper daily-flow chain (ETL→signals→risk→orders→log) has been *replay*-proven
end-to-end (``runtime.paper_daemon`` / ``runtime.market_reader``). What was missing
is the **forward, real-calendar** trigger: fire the chain once, after each session
close, on real wall-clock time. Per the PRD (v4.0) that trigger is a plain
systemd-timer / CLI deployment concern. This module is the small, fully
*injectable* orchestration the timer invokes:

    trading-day gate → after-close time gate → idempotency → run → notify

Every side-effectful seam (clock, calendar, session runner, Discord notifier,
done-marker store) is injected, so the whole decision path is unit-testable with
no real time, no network and no DB. The production wiring
(``build_session_runner``) lazily assembles the proven live-panel path; the CLI
(``orchestration.cli after-close``) maps a run's status onto an exit code.

Failure is never swallowed: a failed / raising daily flow returns ``FAILED``
(exit 1) *and* pushes a Discord error alert. Discord itself is a side channel —
a missing token or a network hiccup is logged and the run continues (it must not
mask the real trading outcome).
"""
from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from loguru import logger

from backtest_platform.runtime.market_data_errors import NoMarketDataError
from backtest_platform.runtime.trading_calendar import is_taiwan_trading_day

#: Taiwan has no DST since 1980 → a fixed UTC+8 offset (mirrors collaborators._TWT).
_TWT = timezone(timedelta(hours=8))
#: Earliest local time the scheduler will run — a buffer past the 13:30 TWSE close
#: for EOD data to settle. ``--force`` overrides it (see ``_is_after_close``).
AFTER_CLOSE_TIME = time(14, 30)
#: Append-only idempotency ledger (JSONL, mirrors research.runs_store's convention).
DEFAULT_MARKER_PATH = Path("reports") / "after_close_markers.jsonl"
_DEFAULT_EQUITY = 10_000_000.0


class AfterCloseStatus(str, Enum):
    """Outcome of one after-close attempt — drives the CLI exit code."""

    NON_TRADING_DAY = "non_trading_day"
    TOO_EARLY = "too_early"
    NOT_ENROLLED = "not_enrolled"      # ADR-033: no active觀察艙 berth → refuse to run
    WATCH_EXPIRED = "watch_expired"    # ADR-033: berth expired → refuse, prompt re-eval
    PAUSED = "watch_paused"            # ADR-033: app-level pause → benign skip (exit 0)
    ALREADY_DONE = "already_done"
    DRY_RUN = "dry_run"
    NO_DATA = "no_data"                # calendar said trading day but source had no as-of row
    SUCCESS = "success"
    FAILED = "failed"


#: Statuses that surface a non-zero CLI exit: a genuine failure or a refused
#: precondition an operator must fix (an unenrolled / expired berth). A NO_DATA skip
#: is a benign no-op (exit 0), like a non-trading day.
_NONZERO_EXIT = frozenset(
    {AfterCloseStatus.FAILED, AfterCloseStatus.NOT_ENROLLED, AfterCloseStatus.WATCH_EXPIRED}
)


class SessionSummary(Protocol):
    """The subset of ``paper_daemon.ReplaySummary`` the scheduler reads."""

    @property
    def ok(self) -> bool: ...

    def summary(self) -> str: ...


@dataclass(frozen=True)
class AfterCloseResult:
    """Immutable record of one attempt. ``exit_code`` is non-zero only on FAILED."""

    status: AfterCloseStatus
    strategy: str
    as_of: date
    message: str

    @property
    def exit_code(self) -> int:
        return 1 if self.status in _NONZERO_EXIT else 0


# --------------------------------------------------------------------------- #
# default seams (all overridable per call for testing)                        #
# --------------------------------------------------------------------------- #
def _now_taipei() -> datetime:
    return datetime.now(_TWT)


def default_is_trading_day(d: date) -> bool:
    """Production trading-day gate (XTAI if installed, else weekday fallback)."""
    return is_taiwan_trading_day(d)


def default_watch_status(strategy: str, as_of: date) -> Any:
    """Production觀察艙 read — the strategy's berth status from the real registry.

    Lazily imported so the scheduler core stays free of pandas / the gate band
    constants at import; returns a ``WatchStatus`` or None (never enrolled)."""
    from backtest_platform.governance.watch_registry import status

    return status(strategy, as_of=as_of)


def default_expire_watches(as_of: date) -> list[str]:
    """Production expiry sweep — mark due berths expired, return newly expired ones."""
    from backtest_platform.governance.watch_registry import expire_due

    return expire_due(as_of)


def _watch_line(watch: Any) -> str:
    """One-line observation digest for the Discord success message (empty if no berth)."""
    if watch is None:
        return ""
    from backtest_platform.governance.watch_registry import NOMINAL_TRADING_DAYS

    return (
        f"[paper-watch] 觀察日 {watch.observed_trading_days}/~{NOMINAL_TRADING_DAYS}"
        f" · 到期 {watch.expiry_date}(剩 {watch.days_remaining} 天)"
    )


def safe_discord_notify(message: str, ok: bool) -> None:
    """Send a Discord alert, swallowing a missing token / network error.

    Success → INFO digest, failure → ERROR alert. A blow-up here (no
    ``DISCORD_BOT_TOKEN``, network down) is logged and NOT re-raised — the alert
    is a side channel and must never mask or abort the trading outcome.
    """
    try:
        from backtest_platform.monitoring.discord_notifier import notify_error, notify_info

        if ok:
            notify_info(message)
        else:
            notify_error("after-close", message)
    except Exception as exc:
        logger.warning("Discord after-close alert skipped (ok={ok}): {e}", ok=ok, e=exc)


# --------------------------------------------------------------------------- #
# idempotency — lightweight done-marker JSONL (no clean telemetry key exists)  #
# --------------------------------------------------------------------------- #
def _marker_key(strategy: str, as_of: date) -> str:
    return f"{strategy}@{as_of.isoformat()}"


def already_done(strategy: str, as_of: date, *, path: Path | str = DEFAULT_MARKER_PATH) -> bool:
    """True iff a *successful* marker for ``(strategy, as_of)`` exists.

    Only ``ok=True`` markers block a re-run, so a failed session stays retryable.
    """
    p = Path(path)
    if not p.exists():
        return False
    key = _marker_key(strategy, as_of)
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue  # a corrupt line must not hide a real marker or crash the gate
        if rec.get("key") == key and rec.get("ok"):
            return True
    return False


def record_done(
    strategy: str,
    as_of: date,
    *,
    ok: bool,
    detail: str = "",
    path: Path | str = DEFAULT_MARKER_PATH,
    clock: Callable[[], datetime] = _now_taipei,
) -> None:
    """Append one JSONL marker for ``(strategy, as_of)`` (creates parent dirs)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "key": _marker_key(strategy, as_of),
        "strategy": strategy,
        "date": as_of.isoformat(),
        "ok": bool(ok),
        "detail": detail,
        "recorded_at": clock().isoformat(),
    }
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------- #
# orchestration                                                               #
# --------------------------------------------------------------------------- #
def _is_after_close(as_of: date, now: datetime, force: bool) -> bool:
    """True if it is safe to run ``as_of`` now: forced, a past session, or today
    past the after-close gate. A future ``as_of`` (data not out) is never ready."""
    if force:
        return True
    local = now.astimezone(_TWT)
    if as_of < local.date():
        return True  # back-fill of an earlier session — trivially after its close
    if as_of > local.date():
        return False  # future date: the session hasn't happened yet
    return local.time() >= AFTER_CLOSE_TIME


def _notify(notifier: Callable[[str, bool], None], message: str, *, ok: bool) -> None:
    """Call the notifier, guarding against a raising notifier (defense in depth)."""
    try:
        notifier(message, ok)
    except Exception as exc:
        logger.warning("after-close notification failed (continuing): {e}", e=exc)


def _result(status: AfterCloseStatus, strategy: str, as_of: date, message: str) -> AfterCloseResult:
    return AfterCloseResult(status=status, strategy=strategy, as_of=as_of, message=message)


def run_after_close(
    strategy: str,
    as_of: date,
    *,
    dry_run: bool = False,
    force: bool = False,
    now: datetime | None = None,
    is_trading_day: Callable[[date], bool] = default_is_trading_day,
    session_runner: Callable[[str, date], SessionSummary] | None = None,
    notifier: Callable[[str, bool], None] = safe_discord_notify,
    marker_path: Path | str = DEFAULT_MARKER_PATH,
    watch_status: Callable[[str, date], Any] = default_watch_status,
    expire_watches: Callable[[date], list[str]] = default_expire_watches,
) -> AfterCloseResult:
    """Run the after-close pipeline for ``(strategy, as_of)`` through the guards.

    Order: trading-day → after-close time → idempotency → dry-run report →
    **觀察艙 enrollment (ADR-033)** → run. The觀察艙 gate makes "who may run paper"
    a machine decision: a real session is refused (non-zero exit, flow never fires)
    unless the strategy holds an active berth; an expired berth is refused with a
    re-eval prompt; an app-level *paused* berth is a benign skip (exit 0, no Discord).
    A dry-run is a wiring smoke test that touches no data and
    collects no OOS, so it short-circuits *before* the gate. Returns an
    :class:`AfterCloseResult`; a real run executes the daily flow via
    ``session_runner``, records success as a done-marker, sweeps expiries, and
    pushes a Discord digest / alert. A no-data session (``NoMarketDataError``)
    degrades to a benign skip, not a FAILED alert.
    """
    now = now or _now_taipei()
    label = _marker_key(strategy, as_of)

    if not is_trading_day(as_of):
        return _result(AfterCloseStatus.NON_TRADING_DAY, strategy, as_of,
                       f"{as_of} is not a TWSE trading day — nothing to do.")
    if not _is_after_close(as_of, now, force):
        return _result(AfterCloseStatus.TOO_EARLY, strategy, as_of,
                       f"Refusing: before the {AFTER_CLOSE_TIME:%H:%M} Asia/Taipei "
                       f"after-close gate for {as_of} (pass --force to override).")
    if already_done(strategy, as_of, path=marker_path):
        return _result(AfterCloseStatus.ALREADY_DONE, strategy, as_of,
                       f"{label} already completed — skipping (idempotent).")
    if dry_run:
        return _result(AfterCloseStatus.DRY_RUN, strategy, as_of,
                       f"DRY_RUN: would run the after-close session for {label} "
                       f"(daily flow NOT triggered).")
    # 觀察艙 enrollment gate — only real (OOS-collecting) sessions are enforced.
    refusal = _watch_gate(watch_status(strategy, as_of), strategy, as_of)
    if refusal is not None:
        return refusal
    if session_runner is None:
        raise ValueError("session_runner is required for a real (non-dry-run) after-close run")

    return _execute(strategy, as_of, label, session_runner, notifier, marker_path,
                    watch_status, expire_watches)


def _watch_gate(watch: Any, strategy: str, as_of: date) -> AfterCloseResult | None:
    """ADR-033 enrollment gate: None ⇒ admitted (active berth); else a skip/refusal.

    A *paused* berth (app-level pause via the GUI / ``watch pause``) is a benign skip
    (exit 0, no Discord — a paused berth every day would be pure noise, a log line
    suffices). An *expired* berth is refused with a re-eval prompt (exit 1); anything
    else without an active berth (never enrolled, or already exited) is refused with
    an enroll hint (exit 1).
    """
    state = getattr(watch, "state", None) if watch is not None else None
    if state == "active":
        return None
    if state == "paused":
        logger.info(
            "after-close {}: 觀察艙已暫停 (app-level pause) → skip {} — no Discord (log only)",
            strategy, as_of,
        )
        return _result(
            AfterCloseStatus.PAUSED, strategy, as_of,
            f"{strategy} 觀察艙已暫停(app-level pause)— skipping {as_of}. "
            "Resume via the Monitor觀察艙 card or `... orchestration.cli watch resume "
            f"--strategy {strategy}`.",
        )
    if watch is not None and getattr(watch, "state", None) == "expired":
        return _result(
            AfterCloseStatus.WATCH_EXPIRED, strategy, as_of,
            f"Refusing: {strategy}'s觀察艙 berth expired on {getattr(watch, 'expiry_date', '?')}"
            " — 請執行含 live 證據的重評 (re-eval with the accumulated live OOS; 晉升仍需 "
            "DSR ≥ 0.95) before scheduling further sessions.",
        )
    return _result(
        AfterCloseStatus.NOT_ENROLLED, strategy, as_of,
        f"Refusing: {strategy} holds no active觀察艙 berth — enroll it first: "
        f"`... orchestration.cli watch enroll --strategy {strategy} --dsr <DSR>`. "
        "Only enrolled strategies may run paper (ADR-033).",
    )


def _execute(
    strategy: str,
    as_of: date,
    label: str,
    session_runner: Callable[[str, date], SessionSummary],
    notifier: Callable[[str, bool], None],
    marker_path: Path | str,
    watch_status: Callable[[str, date], Any],
    expire_watches: Callable[[date], list[str]],
) -> AfterCloseResult:
    """Run the daily flow and turn its outcome into a result + alert + marker."""
    try:
        summary = session_runner(strategy, as_of)
    except NoMarketDataError as exc:  # explicit no-data → benign skip, NOT a failure
        detail = exc.detail or "no market data for this session"
        _notify(notifier, f"[after-close] {label} SKIPPED — no market data ({detail})", ok=True)
        return _result(AfterCloseStatus.NO_DATA, strategy, as_of,
                       f"after-close {label} skipped: no market data ({detail}) — "
                       "approximate-calendar false positive / TWSE halt, not a failure.")
    except Exception as exc:
        detail = f"raised {type(exc).__name__}: {exc}"
        _notify(notifier, f"[after-close] {label} FAILED — {detail}", ok=False)
        return _result(AfterCloseStatus.FAILED, strategy, as_of, f"after-close {label} FAILED: {detail}")

    body = summary.summary()
    if summary.ok:
        record_done(strategy, as_of, ok=True, detail=body, path=marker_path)
        _notify_success(strategy, as_of, label, body, notifier, watch_status, expire_watches)
        return _result(AfterCloseStatus.SUCCESS, strategy, as_of, f"after-close {label} OK\n{body}")

    _notify(notifier, f"[after-close] {label} FAILED\n{body}", ok=False)
    return _result(AfterCloseStatus.FAILED, strategy, as_of, f"after-close {label} FAILED\n{body}")


def _notify_success(
    strategy: str,
    as_of: date,
    label: str,
    body: str,
    notifier: Callable[[str, bool], None],
    watch_status: Callable[[str, date], Any],
    expire_watches: Callable[[date], list[str]],
) -> None:
    """Push the OK digest (with the觀察日 line) then sweep + notify any expiry.

    The observation line is read BEFORE the sweep so the expiry-day session still
    reports its final N/~60; the maturity notice then fires once as INFO on the
    crossing — never an error alert (a matured berth is an expected milestone)."""
    watch_line = _watch_line(watch_status(strategy, as_of))
    ok_msg = f"[after-close] {label} OK\n{body}"
    if watch_line:
        ok_msg += f"\n{watch_line}"
    _notify(notifier, ok_msg, ok=True)

    for expired in expire_watches(as_of):
        if expired == strategy:
            _notify(
                notifier,
                f"[paper-watch] {strategy} 觀察期滿({as_of})— 請執行含 live 證據的重評"
                "(晉升仍需 DSR ≥ 0.95)",
                ok=True,
            )


# --------------------------------------------------------------------------- #
# production wiring — lazily assemble the proven live-panel forward runner     #
# --------------------------------------------------------------------------- #
def _resolve_universe(universe: str | None) -> list[str]:
    raw = universe if universe is not None else os.environ.get("AFTER_CLOSE_UNIVERSE", "")
    symbols = [s.strip() for s in str(raw).split(",") if s.strip()]
    if not symbols:
        raise ValueError(
            "no universe configured — pass --universe 2330,2317,... or set AFTER_CLOSE_UNIVERSE"
        )
    return symbols


def _resolve_equity(equity: float | None) -> float:
    if equity is not None:
        return float(equity)
    raw = os.environ.get("AFTER_CLOSE_EQUITY")
    return float(raw) if raw else _DEFAULT_EQUITY


def _default_state_loader(strategy: str) -> Any:
    """Production restore seam: read the strategy's last-persisted book from telemetry.

    Lazily imports ``db_reader`` so the DB dependency is only pulled in when a real
    session actually restores (keeps assembly + DB-less tests clean). A DB failure
    propagates by design — see ``_build_broker``."""
    from backtest_platform.data.db_reader import load_broker_state

    return load_broker_state(strategy)


def _build_broker(
    strategy: str,
    cash: float,
    *,
    fresh: bool = False,
    state_loader: Callable[[str], Any] | None = None,
) -> Any:
    """Build the session's ``PaperBroker``, rehydrating yesterday's book when present.

    Restore precedence:
      * ``fresh`` → skip restore entirely, start from an empty book at ``cash``
        (explicit escape hatch; the loader is never consulted).
      * loader returns ``None`` (first session) → a fresh broker at ``cash``.
      * loader returns a ``BrokerState`` → seed cash + holdings so the portfolio
        risk gates see the real cross-day exposure (EX-002 / EX-004 / EX-007).

    A DB failure inside the loader **propagates** (never a silent empty book):
    the caller runs this inside the after-close try/except, turning it into a
    FAILED result + Discord alert rather than dishonest empty-book OOS.
    """
    from backtest_platform.adapters.brokers.paper_broker import PaperBroker

    if fresh:
        logger.info("after-close {}: --fresh → empty book, cash={}", strategy, cash)
        return PaperBroker(initial_cash=cash)

    loader = state_loader or _default_state_loader
    state = loader(strategy)  # DB error propagates — fail loud, never fake-empty
    if state is None:
        logger.info("after-close {}: no prior telemetry (first session) → fresh cash={}",
                    strategy, cash)
        return PaperBroker(initial_cash=cash)

    seed = {sid: (p.qty, p.cost_basis) for sid, p in state.positions.items()}
    logger.info("after-close {}: restored {} positions + cash={} from telemetry",
                strategy, len(seed), state.cash)
    return PaperBroker.from_seed(state.cash, seed)


def build_session_runner(
    strategy: str,
    universe: str | None,
    equity: float | None,
    *,
    fresh: bool = False,
    state_loader: Callable[[str], Any] | None = None,
) -> Callable[[str, date], Any]:
    """Assemble the production per-session runner over the proven live-panel path.

    Wires ``market_reader.live_config_for_date`` → ``run_forward_session`` so one
    session reads a fresh FinLab EOD panel through ``as_of`` and runs the inst_flow
    chain forward through the real RiskGate + PaperBroker + TimescaleDB sink.

    Only ``inst_flow`` is wired today (the sole validated-shape edge); an unknown
    strategy fails loud rather than silently running the wrong thing. The broker is
    (re)built inside the returned runner via :func:`_build_broker`, so each session
    rehydrates the latest persisted book from telemetry — closing the PR #151
    cross-day gap. ``fresh`` skips restore (empty-book escape hatch); ``state_loader``
    is injected in tests. Assembly touches neither FinLab nor the DB (both are hit
    only when the returned callable runs).
    """
    if strategy != "inst_flow":
        raise ValueError(
            f"after-close production runner only wires 'inst_flow'; got {strategy!r}. "
            "Wire its live config_for_date before scheduling it."
        )
    symbols = _resolve_universe(universe)
    cash = _resolve_equity(equity)

    from backtest_platform.runtime.market_reader import (
        check_panel_freshness,
        live_config_for_date,
        read_live_panel,
        run_forward_session,
    )
    from backtest_platform.strategies.inst_flow.strategy import InstFlowConfig

    cfg = InstFlowConfig()
    run_id = f"afterclose_{strategy}"

    def _run(strat: str, as_of: date) -> Any:
        broker = _build_broker(strat, cash, fresh=fresh, state_loader=state_loader)
        # Pre-flight no-data guard: an approximate-calendar false positive (weekday
        # holiday) returns a panel whose newest row is the prior session. Detect it
        # BEFORE running the chain (which would place orders on stale data) and let
        # the NoMarketDataError propagate — the scheduler degrades it to a skip.
        # FinLab caches ``data.get`` in-process, so this read is effectively free.
        close, _flow, _volume = read_live_panel(symbols, as_of)
        check_panel_freshness(close, as_of, strategy=strat)
        config_for_date = live_config_for_date(
            symbols, cfg, broker, run_id=run_id, strategy_id=strat, equity=cash,
        )
        return run_forward_session(as_of, config_for_date)

    return _run
