"""Paper-Watch 觀察艙 registry (ADR-033 enforcement) — event-sourced JSONL.

ADR-033 fixed the觀察艙's rules — a 3-month observation window, at most 2 berths,
and a one-shot re-entry bar (an expired candidate may not re-enter without fresh
evidence) — but left them to discipline. This registry makes them machine-enforced:
``enroll`` is the gate that decides *which* strategy may collect live OOS, and the
after-close scheduler refuses any strategy that is not holding an active berth.

Append-only JSONL, same philosophy as ``runs_store`` / ``promotion_store``: the
event log *is* the immutable audit — an enrollment or an expiry can never be
silently un-recorded, and who/when/why is always recoverable. Current state
(active / expired / exited) is *folded* from the ordered events, never mutated in
place. Dependency-free (stdlib + the gate's band constants); the read helpers
(``status`` / ``active_watches``) are pure and path-injectable so a future GUI /
HTTP reader can consume them unchanged.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backtest_platform.validation.two_stage_gate import DSR_MIN, PAPER_WATCH_DSR_MIN

#: Append-only ledger (JSONL), mirrors ``runs_store`` / ``promotion_store``.
DEFAULT_WATCH_PATH = Path("reports") / "watch_registry.jsonl"
#: ADR-033 §3.3 — at most this many concurrent observation berths.
MAX_ACTIVE_WATCHES = 2
#: ADR-033 §3.3 — the observation window, in *calendar* days (≈ 3 months).
OBSERVATION_DAYS = 90
#: ~trading days spanned by the window — the "N/~60" target on the Discord line.
NOMINAL_TRADING_DAYS = 60

_TWT = timezone(timedelta(hours=8))  # Taiwan has no DST → fixed UTC+8


# --------------------------------------------------------------------------- #
# errors — subclass ValueError so callers may catch broadly or precisely       #
# --------------------------------------------------------------------------- #
class WatchRegistryError(ValueError):
    """Base for every observation-cabin admission refusal."""


class NotPaperWatchError(WatchRegistryError):
    """The verdict DSR is not in the Paper-Watch band [0.90, 0.95)."""


class CabinFullError(WatchRegistryError):
    """All berths are occupied (ADR-033 §3.3 cap)."""


class ReEnrollBlockedError(WatchRegistryError):
    """A strategy that already expired / exited cannot re-enter without evidence."""


class AlreadyActiveError(WatchRegistryError):
    """The strategy already holds an active berth (duplicate enrollment)."""


@dataclass(frozen=True)
class WatchStatus:
    """Immutable folded view of one strategy's berth as of a given date."""

    strategy: str
    state: str  # "active" | "paused" | "expired" | "exited"
    enrolled_on: date
    verdict_dsr: float
    expiry_date: date
    observed_trading_days: int
    days_remaining: int
    re_enroll_evidence: str | None = None


TradingDayFn = Callable[[date], bool]


# --------------------------------------------------------------------------- #
# store primitives                                                            #
# --------------------------------------------------------------------------- #
def _resolve(path: Path | str | None) -> Path:
    return Path(path) if path is not None else DEFAULT_WATCH_PATH


def _now_iso() -> str:
    return datetime.now(_TWT).isoformat(timespec="seconds")


def _today() -> date:
    return datetime.now(_TWT).date()


def _default_trading_day() -> TradingDayFn:
    from backtest_platform.runtime.trading_calendar import is_taiwan_trading_day

    return is_taiwan_trading_day


def _read_events(path: Path | str | None) -> list[dict[str, Any]]:
    p = _resolve(path)
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def _append(event: dict[str, Any], path: Path | str | None) -> dict[str, Any]:
    p = _resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def _events_for(strategy: str, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [e for e in events if e.get("strategy") == strategy]


# --------------------------------------------------------------------------- #
# folding — reconstruct state from the ordered event log                      #
# --------------------------------------------------------------------------- #
def _count_trading_days(start: date, end: date, is_trading_day: TradingDayFn) -> int:
    """Trading days in ``(start, end]`` (enrollment day excluded)."""
    if end <= start:
        return 0
    n = 0
    d = start + timedelta(days=1)
    while d <= end:
        if is_trading_day(d):
            n += 1
        d += timedelta(days=1)
    return n


def _fold(
    strategy: str,
    events: list[dict[str, Any]],
    *,
    as_of: date,
    is_trading_day: TradingDayFn,
) -> WatchStatus | None:
    """Fold a strategy's events into its current status, or None if never enrolled.

    Only the *latest* enrollment matters (a re-enrollment starts a fresh berth);
    any ``expire`` / ``exit`` recorded after it decides the terminal state, while
    ``pause`` / ``resume`` toggle the reversible active⇄paused axis. ``expire`` /
    ``exit`` are terminal (sticky): a stray ``resume`` cannot un-expire a berth, and
    ``pause`` only bites an active one — so the fold stays a well-defined machine.
    """
    evs = _events_for(strategy, events)
    enroll_idx = _last_enroll_index(evs)
    if enroll_idx is None:
        return None

    enroll_ev = evs[enroll_idx]
    enrolled_on = date.fromisoformat(enroll_ev["enrolled_on"])
    verdict_dsr = float(enroll_ev["verdict_dsr"])
    evidence = enroll_ev.get("re_enroll_evidence")

    state = "active"
    for e in evs[enroll_idx + 1:]:
        ev = e.get("event")
        if ev == "expire":
            state = "expired"
        elif ev == "exit":
            state = "exited"
        elif ev == "pause" and state == "active":
            state = "paused"
        elif ev == "resume" and state == "paused":
            state = "active"

    expiry_date = enrolled_on + timedelta(days=OBSERVATION_DAYS)
    observed = _count_trading_days(enrolled_on, min(as_of, expiry_date), is_trading_day)
    return WatchStatus(
        strategy=strategy,
        state=state,
        enrolled_on=enrolled_on,
        verdict_dsr=verdict_dsr,
        expiry_date=expiry_date,
        observed_trading_days=observed,
        days_remaining=(expiry_date - as_of).days,
        re_enroll_evidence=evidence,
    )


def _last_enroll_index(evs: list[dict[str, Any]]) -> int | None:
    for i in range(len(evs) - 1, -1, -1):
        if evs[i].get("event") == "enroll":
            return i
    return None


# --------------------------------------------------------------------------- #
# reads — pure, path-injectable (clean seam for a future GUI / HTTP reader)     #
# --------------------------------------------------------------------------- #
def status(
    strategy: str,
    *,
    as_of: date | None = None,
    is_trading_day: TradingDayFn | None = None,
    path: Path | str | None = None,
) -> WatchStatus | None:
    """Current berth status for one strategy (None if never enrolled)."""
    as_of = as_of or _today()
    itd = is_trading_day or _default_trading_day()
    return _fold(strategy, _read_events(path), as_of=as_of, is_trading_day=itd)


def active_watches(
    *,
    as_of: date | None = None,
    is_trading_day: TradingDayFn | None = None,
    path: Path | str | None = None,
) -> list[WatchStatus]:
    """All strategies currently holding an *active* berth, strategy-sorted."""
    as_of = as_of or _today()
    itd = is_trading_day or _default_trading_day()
    events = _read_events(path)
    strategies = sorted({e.get("strategy") for e in events if e.get("strategy")})
    folded = (_fold(s, events, as_of=as_of, is_trading_day=itd) for s in strategies)
    return [w for w in folded if w is not None and w.state == "active"]


def all_watches(
    *,
    as_of: date | None = None,
    is_trading_day: TradingDayFn | None = None,
    path: Path | str | None = None,
) -> list[WatchStatus]:
    """Every strategy's latest folded berth, any state, strategy-sorted.

    Unlike :func:`active_watches` (the after-close gate's active-only view), this is
    the GUI overview read: it surfaces paused / expired / exited berths too, so an
    operator sees the full cabin — who is collecting OOS, who is paused, and who has
    matured and awaits a re-eval.
    """
    as_of = as_of or _today()
    itd = is_trading_day or _default_trading_day()
    events = _read_events(path)
    strategies = sorted({e.get("strategy") for e in events if e.get("strategy")})
    folded = (_fold(s, events, as_of=as_of, is_trading_day=itd) for s in strategies)
    return [w for w in folded if w is not None]


# --------------------------------------------------------------------------- #
# writes                                                                       #
# --------------------------------------------------------------------------- #
def enroll(
    strategy: str,
    verdict_dsr: float,
    enrolled_on: date,
    *,
    re_enroll_evidence: str | None = None,
    is_trading_day: TradingDayFn | None = None,
    path: Path | str | None = None,
) -> WatchStatus:
    """Admit a strategy to the觀察艙, enforcing every ADR-033 admission clause.

    Order of refusals: (1) the verdict DSR must land in the Paper-Watch band
    [0.90, 0.95) — a REJECTED-band or a REAL (deployable) DSR is a category error;
    (2) no duplicate of an already-active berth; (3) an expired / exited strategy
    may not re-enter unless it carries fresh evidence (the one-shot bar); (4) the
    cabin must have a free berth (cap ``MAX_ACTIVE_WATCHES``). All refusals raise;
    on success one ``enroll`` event is appended and the folded status returned.
    """
    itd = is_trading_day or _default_trading_day()
    _assert_admissible(strategy, verdict_dsr, enrolled_on, re_enroll_evidence, itd, path)
    _append(
        {
            "strategy": strategy,
            "event": "enroll",
            "verdict_dsr": verdict_dsr,
            "enrolled_on": enrolled_on.isoformat(),
            "re_enroll_evidence": re_enroll_evidence,
            "at": _now_iso(),
        },
        path,
    )
    result = status(strategy, as_of=enrolled_on, is_trading_day=itd, path=path)
    assert result is not None  # we just enrolled it
    return result


def _assert_admissible(
    strategy: str,
    verdict_dsr: float,
    enrolled_on: date,
    re_enroll_evidence: str | None,
    is_trading_day: TradingDayFn,
    path: Path | str | None,
) -> None:
    """Raise the matching ``WatchRegistryError`` if any ADR-033 admission clause fails."""
    if not (PAPER_WATCH_DSR_MIN <= verdict_dsr < DSR_MIN):
        raise NotPaperWatchError(
            f"DSR {verdict_dsr:.4g} is not in the Paper-Watch band "
            f"[{PAPER_WATCH_DSR_MIN:.2f}, {DSR_MIN:.2f}) — only a PAPER_WATCH verdict "
            "may enter the觀察艙 (< 0.90 is REJECTED, ≥ 0.95 is REAL/deployable)"
        )
    current = _fold(strategy, _read_events(path), as_of=enrolled_on, is_trading_day=is_trading_day)
    if current is not None and current.state == "active":
        raise AlreadyActiveError(f"{strategy} already holds an active觀察艙 berth")
    if current is not None and current.state in ("expired", "exited") and not re_enroll_evidence:
        raise ReEnrollBlockedError(
            f"{strategy} already {current.state} once — the ADR-033 one-shot bar "
            "requires fresh evidence to re-enter (pass re_enroll_evidence)"
        )
    active = active_watches(as_of=enrolled_on, is_trading_day=is_trading_day, path=path)
    if len(active) >= MAX_ACTIVE_WATCHES:
        raise CabinFullError(
            f"觀察艙 full: {len(active)}/{MAX_ACTIVE_WATCHES} berths occupied "
            f"({', '.join(w.strategy for w in active)})"
        )


def expire_due(
    as_of: date,
    *,
    is_trading_day: TradingDayFn | None = None,
    path: Path | str | None = None,
) -> list[str]:
    """Mark every active berth whose window has closed as expired; return the newly
    expired strategies. Idempotent — an already-expired berth is left untouched, so
    a repeat call returns an empty list."""
    itd = is_trading_day or _default_trading_day()
    events = _read_events(path)
    strategies = sorted({e.get("strategy") for e in events if e.get("strategy")})
    expired_now: list[str] = []
    for s in strategies:
        st = _fold(s, events, as_of=as_of, is_trading_day=itd)
        if st is not None and st.state == "active" and as_of >= st.expiry_date:
            _append({"strategy": s, "event": "expire", "as_of": as_of.isoformat(), "at": _now_iso()}, path)
            expired_now.append(s)
    return expired_now


def record_exit(
    strategy: str,
    *,
    reason: str = "",
    path: Path | str | None = None,
) -> None:
    """Record a strategy leaving the觀察艙 (promoted after re-eval, or dropped).

    Terminal like ``expire`` for the one-shot bar: an exited strategy may not
    re-enter without fresh evidence."""
    _append({"strategy": strategy, "event": "exit", "reason": reason, "at": _now_iso()}, path)


# --------------------------------------------------------------------------- #
# app-level pause / resume — the GUI's reversible "stop collecting OOS" switch  #
# --------------------------------------------------------------------------- #
def pause(
    strategy: str,
    *,
    is_trading_day: TradingDayFn | None = None,
    path: Path | str | None = None,
) -> WatchStatus:
    """Pause an active berth (app-level): after-close will skip it while it keeps
    its enrollment / expiry clock. Idempotent — pausing an already-paused berth
    appends no second event. Only an *active* berth may pause: a missing berth or a
    terminal (expired / exited) one raises ``WatchRegistryError``."""
    itd = is_trading_day or _default_trading_day()
    current = _fold(strategy, _read_events(path), as_of=_today(), is_trading_day=itd)
    if current is None:
        raise WatchRegistryError(f"{strategy} 未進觀察艙，無法暫停 (no berth to pause)")
    if current.state == "paused":
        return current  # idempotent — already paused, no duplicate event
    if current.state != "active":
        raise WatchRegistryError(
            f"{strategy} 狀態為 {current.state} — 只有 active 艙位可暫停 "
            "(only an active berth may be paused)"
        )
    _append({"strategy": strategy, "event": "pause", "at": _now_iso()}, path)
    result = _fold(strategy, _read_events(path), as_of=_today(), is_trading_day=itd)
    assert result is not None  # we just appended a pause to an existing berth
    return result


def resume(
    strategy: str,
    *,
    is_trading_day: TradingDayFn | None = None,
    path: Path | str | None = None,
) -> WatchStatus:
    """Resume a paused berth back to active (app-level). Idempotent — resuming an
    already-active berth appends no event. A missing or terminal berth raises."""
    itd = is_trading_day or _default_trading_day()
    current = _fold(strategy, _read_events(path), as_of=_today(), is_trading_day=itd)
    if current is None:
        raise WatchRegistryError(f"{strategy} 未進觀察艙，無法恢復 (no berth to resume)")
    if current.state == "active":
        return current  # idempotent — already active, no duplicate event
    if current.state != "paused":
        raise WatchRegistryError(
            f"{strategy} 狀態為 {current.state} — 只有 paused 艙位可恢復 "
            "(only a paused berth may be resumed)"
        )
    _append({"strategy": strategy, "event": "resume", "at": _now_iso()}, path)
    result = _fold(strategy, _read_events(path), as_of=_today(), is_trading_day=itd)
    assert result is not None  # we just appended a resume to an existing berth
    return result
