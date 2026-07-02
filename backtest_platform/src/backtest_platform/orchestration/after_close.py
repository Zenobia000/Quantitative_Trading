"""After-close scheduler core — the last blocker to collecting live OOS.

The paper daily-flow chain (ETL→signals→risk→orders→log) has been *replay*-proven
end-to-end (``runtime.paper_daemon`` / ``runtime.market_reader``). What was missing
is the **forward, real-calendar** trigger: fire the chain once, after each session
close, on real wall-clock time. Per the PRD (v4.0) that trigger is a plain
cron / systemd-timer level concern — no Prefect. This module is the small, fully
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
    ALREADY_DONE = "already_done"
    DRY_RUN = "dry_run"
    SUCCESS = "success"
    FAILED = "failed"


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
        return 1 if self.status is AfterCloseStatus.FAILED else 0


# --------------------------------------------------------------------------- #
# default seams (all overridable per call for testing)                        #
# --------------------------------------------------------------------------- #
def _now_taipei() -> datetime:
    return datetime.now(_TWT)


def default_is_trading_day(d: date) -> bool:
    """Production trading-day gate (XTAI if installed, else weekday fallback)."""
    return is_taiwan_trading_day(d)


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
    except Exception as exc:  # noqa: BLE001 — missing token / network → log & continue
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
    except Exception as exc:  # noqa: BLE001 — side channel: log, never crash the run
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
) -> AfterCloseResult:
    """Run the after-close pipeline for ``(strategy, as_of)`` through the guards.

    Order: trading-day → after-close time → idempotency → (dry-run report | run).
    Returns an :class:`AfterCloseResult`; only ``FAILED`` yields a non-zero
    ``exit_code``. On a real run the daily flow is executed via ``session_runner``
    (required unless ``dry_run``), its success is recorded as a done-marker, and a
    Discord digest / error alert is pushed.
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
    if session_runner is None:
        raise ValueError("session_runner is required for a real (non-dry-run) after-close run")

    return _execute(strategy, as_of, label, session_runner, notifier, marker_path)


def _execute(
    strategy: str,
    as_of: date,
    label: str,
    session_runner: Callable[[str, date], SessionSummary],
    notifier: Callable[[str, bool], None],
    marker_path: Path | str,
) -> AfterCloseResult:
    """Run the daily flow and turn its outcome into a result + alert + marker."""
    try:
        summary = session_runner(strategy, as_of)
    except Exception as exc:  # noqa: BLE001 — surface loudly (alert + exit 1), never silent
        detail = f"raised {type(exc).__name__}: {exc}"
        _notify(notifier, f"[after-close] {label} FAILED — {detail}", ok=False)
        return _result(AfterCloseStatus.FAILED, strategy, as_of, f"after-close {label} FAILED: {detail}")

    body = summary.summary()
    if summary.ok:
        record_done(strategy, as_of, ok=True, detail=body, path=marker_path)
        _notify(notifier, f"[after-close] {label} OK\n{body}", ok=True)
        return _result(AfterCloseStatus.SUCCESS, strategy, as_of, f"after-close {label} OK\n{body}")

    _notify(notifier, f"[after-close] {label} FAILED\n{body}", ok=False)
    return _result(AfterCloseStatus.FAILED, strategy, as_of, f"after-close {label} FAILED\n{body}")


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


def build_session_runner(
    strategy: str, universe: str | None, equity: float | None
) -> Callable[[str, date], Any]:
    """Assemble the production per-session runner over the proven live-panel path.

    Wires ``market_reader.live_config_for_date`` → ``run_forward_session`` so one
    session reads a fresh FinLab EOD panel through ``as_of`` and runs the inst_flow
    chain forward through the real RiskGate + PaperBroker + TimescaleDB sink.

    Only ``inst_flow`` is wired today (the sole validated-shape edge); an unknown
    strategy fails loud rather than silently running the wrong thing. LIMITATION:
    each CLI process starts a fresh ``PaperBroker`` — the per-session signals /
    fills / equity ARE persisted via the sink, but in-process portfolio state is
    not yet rehydrated from the DB across daily restarts (that belongs to the db
    hardening work package). This is sufficient for observing daily live signals.
    """
    if strategy != "inst_flow":
        raise ValueError(
            f"after-close production runner only wires 'inst_flow'; got {strategy!r}. "
            "Wire its live config_for_date before scheduling it."
        )
    symbols = _resolve_universe(universe)
    cash = _resolve_equity(equity)

    from backtest_platform.adapters.brokers.paper_broker import PaperBroker
    from backtest_platform.runtime.market_reader import (
        live_config_for_date,
        run_forward_session,
    )
    from backtest_platform.strategies.inst_flow.strategy import InstFlowConfig

    broker = PaperBroker(initial_cash=cash)
    cfg = InstFlowConfig()
    run_id = f"afterclose_{strategy}"

    def _run(strat: str, as_of: date) -> Any:
        config_for_date = live_config_for_date(
            symbols, cfg, broker, run_id=run_id, strategy_id=strat, equity=cash,
        )
        return run_forward_session(as_of, config_for_date)

    return _run
