"""``/monitor/watch`` — Paper-Watch 觀察艙 overview + app-level pause/resume (ADR-033).

The觀察艙 enforcement (enrollment gate + after-close scheduler) shipped in PR #161;
its timer本体 stays in systemd (the OS guarantees punctuality per PRD v4.0). This
router is the GUI's "see and manage" surface — the补 for review defect #17 (the
paper stage had near-zero interface coverage):

* ``GET  /monitor/watch``                 — every berth's status / observation
  progress / expiry / DSR, plus a **timer-health** verdict (is the systemd timer
  actually firing?) folded from the after-close done-markers, and a recent session
  timeline.
* ``POST /monitor/watch/{strategy}/pause``  — app-level pause (after-close skips it,
  keeps the enrollment clock); ``.../resume`` reverses it.

All reads are path/clock/calendar-injectable (see ``api.deps``), so this stays
DB-free and unit-testable. Responses use the uniform envelope (doc 25); a refused
pause/resume raises ``HTTPException`` and the app-level handler re-wraps it as a
structured error. ``meta.data_source="watch_registry"`` marks the live source
(distinct from the M4-pending Monitor stubs).
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from quant_platform.apps.api.deps import (
    get_after_close_marker_path,
    get_watch_registry_path,
    get_watch_today,
    get_watch_trading_day_fn,
)
from quant_platform.apps.api.envelope import DataSource, Envelope, ok

router = APIRouter(prefix="/monitor/watch", tags=["monitor-watch"])


def _status_dict(st: Any) -> dict[str, Any]:
    """Serialize a ``WatchStatus`` for the envelope (dates → ISO strings)."""
    return {
        "strategy": st.strategy,
        "status": st.state,
        "enrolled_on": st.enrolled_on.isoformat(),
        "verdict_dsr": st.verdict_dsr,
        "observed_trading_days": st.observed_trading_days,
        "expiry_date": st.expiry_date.isoformat(),
        "days_remaining": st.days_remaining,
    }


@router.get("", response_model=Envelope)
def watch_overview(
    reg_path: Path = Depends(get_watch_registry_path),
    marker_path: Path = Depends(get_after_close_marker_path),
    today: date = Depends(get_watch_today),
    is_trading_day: Callable[[date], bool] = Depends(get_watch_trading_day_fn),
) -> Envelope:
    """觀察艙 overview: every berth (any state) + timer health + recent sessions.

    Each row carries the folded berth (status / 觀察日 N/~60 / expiry / DSR) enriched
    with the after-close **timer health** (``ok`` / ``stale`` / ``never_ran``) so the
    operator can see at a glance whether the systemd timer is still firing — a silent
    dead timer would otherwise stall OOS collection with no alert.
    """
    from quant_platform.services.governance_release.watch_registry import NOMINAL_TRADING_DAYS, all_watches
    from quant_platform.services.strategy_runtime.timer_health import timer_health

    berths = all_watches(as_of=today, is_trading_day=is_trading_day, path=reg_path)
    rows: list[dict[str, Any]] = []
    for st in berths:
        health = timer_health(
            st.strategy, as_of=today, is_trading_day=is_trading_day, marker_path=marker_path,
        )
        row = _status_dict(st)
        row |= {
            "nominal_trading_days": NOMINAL_TRADING_DAYS,
            "timer_health": health.state,
            "last_session_date": (
                health.last_success_date.isoformat() if health.last_success_date else None
            ),
            "last_session_at": health.last_recorded_at,
            "last_trading_day": health.last_trading_day.isoformat(),
            "sessions": [
                {"date": m.date.isoformat(), "status": m.status} for m in health.recent
            ],
        }
        rows.append(row)
    return ok(rows, meta={"data_source": DataSource.WATCH_REGISTRY, "ttl": 60, "total": len(rows)})


def _toggle(strategy: str, reg_path: Path, is_trading_day: Callable[[date], bool], *, resume: bool) -> Envelope:
    """Shared pause/resume body: run the registry write, map a refusal to a 400."""
    from quant_platform.services.governance_release.watch_registry import WatchRegistryError, pause
    from quant_platform.services.governance_release.watch_registry import resume as resume_fn

    try:
        st = (resume_fn if resume else pause)(strategy, is_trading_day=is_trading_day, path=reg_path)
    except WatchRegistryError as exc:
        # A missing / terminal berth is a caller mistake, not a server fault → 400.
        raise HTTPException(status_code=400, detail={"message": str(exc), "strategy": strategy}) from None
    return ok(_status_dict(st), meta={"data_source": DataSource.WATCH_REGISTRY})


@router.post("/{strategy}/pause", response_model=Envelope)
def watch_pause(
    strategy: str,
    reg_path: Path = Depends(get_watch_registry_path),
    is_trading_day: Callable[[date], bool] = Depends(get_watch_trading_day_fn),
) -> Envelope:
    """App-level pause: after-close will skip this berth (benign, no Discord) while it
    keeps its enrollment / expiry clock. Idempotent; only an active berth may pause."""
    return _toggle(strategy, reg_path, is_trading_day, resume=False)


@router.post("/{strategy}/resume", response_model=Envelope)
def watch_resume(
    strategy: str,
    reg_path: Path = Depends(get_watch_registry_path),
    is_trading_day: Callable[[date], bool] = Depends(get_watch_trading_day_fn),
) -> Envelope:
    """Resume a paused berth back to active. Idempotent; only a paused berth may resume."""
    return _toggle(strategy, reg_path, is_trading_day, resume=True)
