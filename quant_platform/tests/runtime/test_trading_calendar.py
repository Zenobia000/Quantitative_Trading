"""Tests for the Taiwan trading-day helper (after-close scheduler §).

The XTAI (exchange_calendars) path is exercised only via an INJECTED calendar so
the suite never depends on the optional ``calendar`` extra; the default env falls
back to the weekday approximation, which these tests pin explicitly.
"""
from __future__ import annotations

from datetime import date

from quant_platform.services.strategy_runtime.trading_calendar import is_taiwan_trading_day


class _FakeCalendar:
    """Minimal ``exchange_calendars``-shaped stub: only ``is_session``."""

    def __init__(self, sessions: set[date]) -> None:
        self._sessions = sessions

    def is_session(self, ts) -> bool:  # ts is a pd.Timestamp
        return ts.date() in self._sessions


def test_weekday_fallback_treats_monday_to_friday_as_trading():
    # 2026-07-02 is a Thursday; fallback (no injected calendar) → trading day.
    assert is_taiwan_trading_day(date(2026, 7, 2)) is True


def test_weekday_fallback_treats_weekend_as_non_trading():
    # 2026-07-04 Saturday, 2026-07-05 Sunday.
    assert is_taiwan_trading_day(date(2026, 7, 4)) is False
    assert is_taiwan_trading_day(date(2026, 7, 5)) is False


def test_injected_calendar_is_authoritative_over_weekday_fallback():
    # A weekday the injected calendar does NOT list (e.g. a holiday) → non-trading,
    # proving the calendar overrides the naive Mon-Fri fallback.
    cal = _FakeCalendar(sessions={date(2026, 7, 1)})  # only Wed 7/1 is a session
    assert is_taiwan_trading_day(date(2026, 7, 1), calendar=cal) is True
    assert is_taiwan_trading_day(date(2026, 7, 2), calendar=cal) is False  # Thu, not listed


def test_fallback_mode_logs_approximate_warning_once(monkeypatch):
    # The approximate (weekday) path must WARN once that weekday holidays over-fire —
    # a visible data-quality signal, latched so every gate call doesn't spam it.
    import quant_platform.services.strategy_runtime.trading_calendar as tc

    monkeypatch.setattr(tc, "_calendar_mode_logged", False)
    warns: list[tuple] = []
    monkeypatch.setattr(tc.logger, "warning", lambda *a, **k: warns.append(a))
    monkeypatch.setattr(tc.logger, "info", lambda *a, **k: None)
    tc._log_calendar_mode_once(xtai_available=False)
    tc._log_calendar_mode_once(xtai_available=False)  # latched → no second line
    assert len(warns) == 1
    assert "近似日曆" in warns[0][0]


def test_exact_mode_logs_precise_info_once(monkeypatch):
    import quant_platform.services.strategy_runtime.trading_calendar as tc

    monkeypatch.setattr(tc, "_calendar_mode_logged", False)
    infos: list[tuple] = []
    monkeypatch.setattr(tc.logger, "info", lambda *a, **k: infos.append(a))
    monkeypatch.setattr(tc.logger, "warning", lambda *a, **k: None)
    tc._log_calendar_mode_once(xtai_available=True)
    tc._log_calendar_mode_once(xtai_available=True)
    assert len(infos) == 1
    assert "精確 XTAI" in infos[0][0]
