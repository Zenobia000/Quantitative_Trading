"""Paper-Watch 觀察艙 app-level pause / resume (ADR-033 GUI enforcement补).

The觀察艙 timer本体 stays in systemd — the GUI only ``sees and manages``. An
operator who wants to停 collecting live OOS for a berth without exiting it (the
one-shot re-entry bar makes an ``exit`` costly) needs an *app-level* pause: the
after-close scheduler skips a paused berth (exit 0, no Discord noise) while the
berth keeps its enrollment / expiry clock.

Pause / resume are new event types folded the same event-sourced way as
enroll / expire / exit: the log is the audit, state is folded, never mutated.
These tests pin the fold transitions, the guards (only an active berth pauses;
only a paused berth resumes; both idempotent), and that ``all_watches`` surfaces
paused / expired berths the GUI must render (``active_watches`` stays active-only).
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from backtest_platform.research.watch_registry import (
    OBSERVATION_DAYS,
    WatchRegistryError,
    active_watches,
    all_watches,
    enroll,
    expire_due,
    pause,
    resume,
    status,
)


def _weekday(d: date) -> bool:
    return d.weekday() < 5


# --------------------------------------------------------------------------- #
# fold transitions — pause: active→paused, resume: paused→active              #
# --------------------------------------------------------------------------- #
def test_pause_folds_active_berth_to_paused(tmp_path):
    reg = tmp_path / "watch.jsonl"
    on = date(2026, 7, 2)
    enroll("inst_flow", 0.908, on, is_trading_day=_weekday, path=reg)
    st = pause("inst_flow", is_trading_day=_weekday, path=reg)
    assert st.state == "paused"
    # the derived clock is untouched — enrollment / expiry survive a pause
    assert st.enrolled_on == on
    assert st.expiry_date == on + timedelta(days=OBSERVATION_DAYS)


def test_resume_folds_paused_berth_back_to_active(tmp_path):
    reg = tmp_path / "watch.jsonl"
    on = date(2026, 7, 2)
    enroll("inst_flow", 0.908, on, is_trading_day=_weekday, path=reg)
    pause("inst_flow", is_trading_day=_weekday, path=reg)
    st = resume("inst_flow", is_trading_day=_weekday, path=reg)
    assert st.state == "active"


def test_pause_resume_pause_last_event_wins(tmp_path):
    reg = tmp_path / "watch.jsonl"
    on = date(2026, 7, 2)
    enroll("inst_flow", 0.908, on, is_trading_day=_weekday, path=reg)
    pause("inst_flow", is_trading_day=_weekday, path=reg)
    resume("inst_flow", is_trading_day=_weekday, path=reg)
    pause("inst_flow", is_trading_day=_weekday, path=reg)
    assert status("inst_flow", is_trading_day=_weekday, path=reg).state == "paused"


# --------------------------------------------------------------------------- #
# idempotency — a double pause / resume appends no second event               #
# --------------------------------------------------------------------------- #
def test_pause_is_idempotent(tmp_path):
    reg = tmp_path / "watch.jsonl"
    on = date(2026, 7, 2)
    enroll("inst_flow", 0.908, on, is_trading_day=_weekday, path=reg)
    pause("inst_flow", is_trading_day=_weekday, path=reg)
    st = pause("inst_flow", is_trading_day=_weekday, path=reg)  # already paused
    assert st.state == "paused"
    pause_events = [
        line for line in reg.read_text().splitlines() if '"event": "pause"' in line
    ]
    assert len(pause_events) == 1  # the second pause is a no-op, no duplicate event


def test_resume_on_active_berth_is_idempotent_noop(tmp_path):
    reg = tmp_path / "watch.jsonl"
    on = date(2026, 7, 2)
    enroll("inst_flow", 0.908, on, is_trading_day=_weekday, path=reg)
    st = resume("inst_flow", is_trading_day=_weekday, path=reg)  # never paused
    assert st.state == "active"
    assert '"event": "resume"' not in reg.read_text()


# --------------------------------------------------------------------------- #
# guards — pause only an active berth; a missing / terminal berth refuses      #
# --------------------------------------------------------------------------- #
def test_pause_unknown_strategy_raises(tmp_path):
    with pytest.raises(WatchRegistryError):
        pause("never_enrolled", is_trading_day=_weekday, path=tmp_path / "watch.jsonl")


def test_pause_expired_berth_raises(tmp_path):
    reg = tmp_path / "watch.jsonl"
    on = date(2026, 1, 1)
    enroll("inst_flow", 0.908, on, is_trading_day=_weekday, path=reg)
    # push past the 90-day window so the berth expires
    expire_due(on + timedelta(days=OBSERVATION_DAYS + 1), is_trading_day=_weekday, path=reg)
    assert status("inst_flow", is_trading_day=_weekday, path=reg).state == "expired"
    with pytest.raises(WatchRegistryError):
        pause("inst_flow", is_trading_day=_weekday, path=reg)


def test_resume_unknown_strategy_raises(tmp_path):
    with pytest.raises(WatchRegistryError):
        resume("never_enrolled", is_trading_day=_weekday, path=tmp_path / "watch.jsonl")


# --------------------------------------------------------------------------- #
# reads — active_watches excludes paused; all_watches surfaces every berth     #
# --------------------------------------------------------------------------- #
def test_paused_berth_leaves_active_watches(tmp_path):
    reg = tmp_path / "watch.jsonl"
    on = date(2026, 7, 2)
    enroll("inst_flow", 0.908, on, is_trading_day=_weekday, path=reg)
    enroll("momentum", 0.921, on, is_trading_day=_weekday, path=reg)
    pause("inst_flow", is_trading_day=_weekday, path=reg)
    active = {w.strategy for w in active_watches(as_of=on, is_trading_day=_weekday, path=reg)}
    assert active == {"momentum"}  # paused berth no longer counts as active


def test_paused_berth_frees_a_berth_for_a_new_enroll(tmp_path):
    # a paused berth must not count against the ≤ 2 cap — else pausing to make room
    # would be impossible. Pause inst_flow, then two fresh enrolls still fit.
    reg = tmp_path / "watch.jsonl"
    on = date(2026, 7, 2)
    enroll("inst_flow", 0.908, on, is_trading_day=_weekday, path=reg)
    pause("inst_flow", is_trading_day=_weekday, path=reg)
    enroll("momentum", 0.921, on, is_trading_day=_weekday, path=reg)
    enroll("reversal", 0.933, on, is_trading_day=_weekday, path=reg)
    active = {w.strategy for w in active_watches(as_of=on, is_trading_day=_weekday, path=reg)}
    assert active == {"momentum", "reversal"}


def test_all_watches_surfaces_active_and_paused(tmp_path):
    reg = tmp_path / "watch.jsonl"
    on = date(2026, 7, 2)
    enroll("inst_flow", 0.908, on, is_trading_day=_weekday, path=reg)
    enroll("momentum", 0.921, on, is_trading_day=_weekday, path=reg)
    pause("inst_flow", is_trading_day=_weekday, path=reg)
    by_state = {w.strategy: w.state for w in all_watches(as_of=on, is_trading_day=_weekday, path=reg)}
    assert by_state == {"inst_flow": "paused", "momentum": "active"}
