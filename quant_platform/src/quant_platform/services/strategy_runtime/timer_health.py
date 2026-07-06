"""After-close timer health — fold the done-marker JSONL into a liveness verdict.

The after-close scheduler本体 lives in systemd (ADR-033 / PRD v4.0): the OS
guarantees it fires punctually. The GUI's補 role is to make that liveness *visible* —
a silently dead timer is the worst failure mode, because paper OOS just stops
accruing with no alert. This module is the pure, injectable read that powers the
Monitor-zone觀察艙 card's timer-health block:

    read markers → last *successful* session → compare against the last closed
    trading day (calendar-aware) → ok | stale | never_ran

The after-close store only writes a marker on a *successful* session
(``record_done(..., ok=True)``); a FAILED / NO_DATA / paused day writes none. So
"the last success is the last closed trading day" is the honest liveness signal.
The calendar is injected (same seam as the scheduler), so ``昨天是假日 → 沒 marker``
reads as ok, not stale: ``last_trading_day`` walks back over weekends / holidays to
the last real TWSE session that *should* have produced a marker.

Dependency-free (stdlib only); the default marker path mirrors ``after_close``.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from quant_platform.services.strategy_runtime.after_close import DEFAULT_MARKER_PATH

TradingDayFn = Callable[[date], bool]

#: How far back ``previous_trading_day`` will walk before giving up (a safety bound
#: against a pathological calendar that reports no open day — never hit in practice;
#: TWSE has no gap longer than the lunar-new-year break of ~1 week).
_MAX_LOOKBACK_DAYS = 30


@dataclass(frozen=True)
class SessionMarker:
    """One after-close session as the GUI timeline renders it."""

    date: date
    status: str  # "OK" | "FAILED" (markers only persist successes today; forward-safe)
    recorded_at: str | None


@dataclass(frozen=True)
class TimerHealth:
    """Folded liveness verdict for one strategy's after-close timer."""

    state: str  # "ok" | "stale" | "never_ran"
    last_success_date: date | None
    last_recorded_at: str | None
    last_trading_day: date
    recent: list[SessionMarker]


def previous_trading_day(as_of: date, is_trading_day: TradingDayFn) -> date:
    """The last TWSE session strictly *before* ``as_of`` (walks over weekends /
    holidays). This is the day a healthy timer's newest marker should carry: today's
    own session may not have fired yet (before the 14:30 after-close gate), so a
    strictly-earlier reference avoids a false ``stale`` on a normal morning."""
    d = as_of - timedelta(days=1)
    for _ in range(_MAX_LOOKBACK_DAYS):
        if is_trading_day(d):
            return d
        d -= timedelta(days=1)
    return as_of - timedelta(days=1)  # calendar reported nothing open — best effort


def read_markers(strategy: str, *, path: Path | str = DEFAULT_MARKER_PATH) -> list[SessionMarker]:
    """All after-close markers for ``strategy``, oldest→newest by session date.

    A corrupt / unparseable line is skipped (never crashes the read, never hides a
    good marker) — same defense-in-depth as ``after_close.already_done``.
    """
    p = Path(path)
    if not p.exists():
        return []
    rows: list[SessionMarker] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("strategy") != strategy or not rec.get("date"):
            continue
        try:
            d = date.fromisoformat(str(rec["date"]))
        except ValueError:
            continue
        status = "OK" if rec.get("ok") else "FAILED"
        rows.append(SessionMarker(date=d, status=status, recorded_at=rec.get("recorded_at")))
    rows.sort(key=lambda m: m.date)
    return rows


def timer_health(
    strategy: str,
    *,
    as_of: date,
    is_trading_day: TradingDayFn,
    marker_path: Path | str = DEFAULT_MARKER_PATH,
    recent_n: int = 10,
) -> TimerHealth:
    """Fold the marker log into a three-state liveness verdict + recent timeline.

    * ``never_ran``  — no marker at all (freshly enrolled, or the timer never installed)
    * ``ok``         — the last *successful* session ≥ the last closed trading day
    * ``stale``      — the last success falls behind it (a session was missed)

    A FAILED marker does not count as a success (so a run that fires but errors still
    reads stale for liveness — the timer ran, but no OOS was collected). ``recent`` is
    the newest-first, capped-at-``recent_n`` timeline the card renders.
    """
    markers = read_markers(strategy, path=marker_path)
    last_trading_day = previous_trading_day(as_of, is_trading_day)
    recent = list(reversed(markers))[:recent_n]

    successes = [m for m in markers if m.status == "OK"]
    if not markers:
        return TimerHealth(
            state="never_ran", last_success_date=None, last_recorded_at=None,
            last_trading_day=last_trading_day, recent=recent,
        )
    last_success = successes[-1] if successes else None
    last_success_date = last_success.date if last_success else None
    # ok iff the newest success reaches the last closed session (holiday-aware).
    state = "ok" if (last_success_date is not None and last_success_date >= last_trading_day) else "stale"
    return TimerHealth(
        state=state,
        last_success_date=last_success_date,
        last_recorded_at=last_success.recorded_at if last_success else None,
        last_trading_day=last_trading_day,
        recent=recent,
    )
