"""After-close timer health — does the systemd timer actually fire? (ADR-033 GUI补).

The scheduler本体 lives in systemd (OS guarantees punctuality); the GUI's job is to
make its *liveness* visible. A silent dead timer is the worst failure — paper OOS
just stops accruing with no alert. This module folds the after-close done-marker
JSONL against the TWSE calendar into a three-state verdict:

* ``never_ran``  — no marker at all (freshly enrolled, or the timer never installed)
* ``ok``         — the last successful session is the last *closed* trading day
* ``stale``      — the last success falls behind the last closed trading day
                   (a missed session → the timer probably isn't running)

The calendar is injected so ``昨天是假日 → 沒 marker`` never false-positives as stale:
``last_trading_day`` walks back over weekends / holidays to the last real session.
"""
from __future__ import annotations

import json
from datetime import date

from quant_platform.services.strategy_runtime.timer_health import (
    previous_trading_day,
    read_markers,
    timer_health,
)


def _weekday(d: date) -> bool:
    return d.weekday() < 5


def _write_markers(path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")


def _marker(strategy: str, d: date, *, ok: bool = True, at: str | None = None) -> dict:
    return {
        "key": f"{strategy}@{d.isoformat()}",
        "strategy": strategy,
        "date": d.isoformat(),
        "ok": ok,
        "detail": "REPLAY: 1/1 sessions green" if ok else "REPLAY: 0/1",
        "recorded_at": at or f"{d.isoformat()}T14:32:05+08:00",
    }


# --------------------------------------------------------------------------- #
# previous_trading_day — walk back over weekends / holidays                    #
# --------------------------------------------------------------------------- #
def test_previous_trading_day_skips_weekend():
    # Monday 2026-07-06 → the last closed session is Friday 2026-07-03
    assert previous_trading_day(date(2026, 7, 6), _weekday) == date(2026, 7, 3)


def test_previous_trading_day_skips_a_holiday_friday():
    # Friday 2026-07-03 is a holiday → last closed session before Mon is Thu 07-02
    holiday = date(2026, 7, 3)
    cal = lambda d: d.weekday() < 5 and d != holiday  # noqa: E731
    assert previous_trading_day(date(2026, 7, 6), cal) == date(2026, 7, 2)


# --------------------------------------------------------------------------- #
# timer_health — three states                                                 #
# --------------------------------------------------------------------------- #
def test_never_ran_when_no_marker(tmp_path):
    mp = tmp_path / "markers.jsonl"
    h = timer_health("inst_flow", as_of=date(2026, 7, 6), is_trading_day=_weekday, marker_path=mp)
    assert h.state == "never_ran"
    assert h.last_success_date is None
    assert h.recent == []


def test_ok_when_last_success_is_the_last_closed_trading_day(tmp_path):
    mp = tmp_path / "markers.jsonl"
    _write_markers(mp, [_marker("inst_flow", date(2026, 7, 3))])  # Friday
    h = timer_health("inst_flow", as_of=date(2026, 7, 6), is_trading_day=_weekday, marker_path=mp)
    assert h.state == "ok"
    assert h.last_success_date == date(2026, 7, 3)
    assert h.last_trading_day == date(2026, 7, 3)


def test_stale_when_last_success_lags_the_last_closed_trading_day(tmp_path):
    mp = tmp_path / "markers.jsonl"
    _write_markers(mp, [_marker("inst_flow", date(2026, 7, 2))])  # Thu, but Fri closed too
    h = timer_health("inst_flow", as_of=date(2026, 7, 6), is_trading_day=_weekday, marker_path=mp)
    assert h.state == "stale"
    assert h.last_success_date == date(2026, 7, 2)
    assert h.last_trading_day == date(2026, 7, 3)  # the session that was missed


def test_holiday_yesterday_is_not_stale(tmp_path):
    # The ADR-033 calendar case: Friday was a holiday, so NO Friday marker exists —
    # that must read as ok, not stale (the timer correctly skipped a closed exchange).
    mp = tmp_path / "markers.jsonl"
    _write_markers(mp, [_marker("inst_flow", date(2026, 7, 2))])  # Thursday
    holiday = date(2026, 7, 3)
    cal = lambda d: d.weekday() < 5 and d != holiday  # noqa: E731
    h = timer_health("inst_flow", as_of=date(2026, 7, 6), is_trading_day=cal, marker_path=mp)
    assert h.state == "ok"
    assert h.last_trading_day == date(2026, 7, 2)


def test_today_success_reads_ok_even_before_next_session(tmp_path):
    # as_of is itself a trading day and today's session already ran → ok
    mp = tmp_path / "markers.jsonl"
    _write_markers(mp, [_marker("inst_flow", date(2026, 7, 6))])  # today (Mon)
    h = timer_health("inst_flow", as_of=date(2026, 7, 6), is_trading_day=_weekday, marker_path=mp)
    assert h.state == "ok"


# --------------------------------------------------------------------------- #
# recent timeline — newest-first, capped, status derived from the marker       #
# --------------------------------------------------------------------------- #
def test_recent_timeline_is_newest_first_and_capped(tmp_path):
    mp = tmp_path / "markers.jsonl"
    days = [date(2026, 6, d) for d in range(1, 16)]  # 15 markers
    _write_markers(mp, [_marker("inst_flow", d) for d in days])
    h = timer_health("inst_flow", as_of=date(2026, 7, 6), is_trading_day=_weekday, marker_path=mp, recent_n=10)
    assert len(h.recent) == 10
    assert h.recent[0].date == date(2026, 6, 15)  # newest first
    assert all(m.status == "OK" for m in h.recent)


def test_read_markers_maps_failed_status_and_ignores_other_strategies(tmp_path):
    mp = tmp_path / "markers.jsonl"
    _write_markers(mp, [
        _marker("inst_flow", date(2026, 6, 1), ok=True),
        _marker("inst_flow", date(2026, 6, 2), ok=False),
        _marker("momentum", date(2026, 6, 2), ok=True),
    ])
    rows = read_markers("inst_flow", path=mp)
    assert [(m.date, m.status) for m in rows] == [
        (date(2026, 6, 1), "OK"),
        (date(2026, 6, 2), "FAILED"),
    ]


def test_stale_ignores_failed_markers_for_last_success(tmp_path):
    # a FAILED session on Friday must NOT count as a success — still stale vs Friday
    mp = tmp_path / "markers.jsonl"
    _write_markers(mp, [
        _marker("inst_flow", date(2026, 7, 2), ok=True),
        _marker("inst_flow", date(2026, 7, 3), ok=False),
    ])
    h = timer_health("inst_flow", as_of=date(2026, 7, 6), is_trading_day=_weekday, marker_path=mp)
    assert h.state == "stale"
    assert h.last_success_date == date(2026, 7, 2)
