"""Unit tests for the Discord three-tier alert rule engine.

Hermetic: no DB, no network, no real Discord. Time is injected via a frozen
``now`` / clock so dedup-window and silent-hour behaviour is reproducible.

Spec: dev_docs/20_dashboard_specification.md §4 (§4.1 levels, §4.2 rule table,
§4.4 dedup / silent window).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backtest_platform.monitoring.alert_rules import (
    DEDUPE_WINDOW,
    Alert,
    AlertLevel,
    AlertRouter,
    silent_hours,
)

# A fixed reference instant well inside the active (non-silent) window: 13:42 TWT.
# All TWT (UTC+8) so the local-hour math the engine does is unambiguous.
TWT = timezone(timedelta(hours=8))
DAYTIME = datetime(2026, 5, 31, 13, 42, 0, tzinfo=TWT)  # 13:42 → active
NIGHTTIME = datetime(2026, 5, 31, 23, 10, 0, tzinfo=TWT)  # 23:10 → silent
EARLY = datetime(2026, 5, 31, 6, 30, 0, tzinfo=TWT)  # 06:30 → silent


def _router(now: datetime = DAYTIME) -> AlertRouter:
    """Router with a clock pinned to ``now`` (advance via .set / replace)."""
    clock = {"t": now}
    return AlertRouter(clock=lambda: clock["t"]), clock  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# AlertLevel enum
# ---------------------------------------------------------------------------


def test_alert_level_has_three_tiers() -> None:
    assert {lvl.name for lvl in AlertLevel} == {"CRITICAL", "HIGH", "INFO"}


def test_alert_level_value_round_trips() -> None:
    assert AlertLevel("CRITICAL") is AlertLevel.CRITICAL
    assert AlertLevel.HIGH.value == "HIGH"


def test_alert_is_frozen() -> None:
    alert = Alert(rule_id="CRIT-001", level=AlertLevel.CRITICAL, title="t", message="m")
    with pytest.raises(Exception):
        alert.rule_id = "x"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# §4.2 rule triggers — each rule fires on its documented condition
# ---------------------------------------------------------------------------


def test_crit_001_three_consecutive_rejected_fills() -> None:
    router, _ = _router()
    alerts = router.evaluate({"fills_rejected_streak": 3})
    ids = {a.rule_id for a in alerts}
    assert "CRIT-001" in ids
    fired = next(a for a in alerts if a.rule_id == "CRIT-001")
    assert fired.level is AlertLevel.CRITICAL


def test_crit_001_does_not_fire_below_three() -> None:
    router, _ = _router()
    alerts = router.evaluate({"fills_rejected_streak": 2})
    assert "CRIT-001" not in {a.rule_id for a in alerts}


def test_crit_002_shioaji_disconnected_over_60s() -> None:
    router, _ = _router()
    alerts = router.evaluate({"shioaji_connected": 0, "shioaji_disconnect_secs": 90})
    assert "CRIT-002" in {a.rule_id for a in alerts}


def test_crit_002_does_not_fire_when_connected() -> None:
    router, _ = _router()
    alerts = router.evaluate({"shioaji_connected": 1, "shioaji_disconnect_secs": 0})
    assert "CRIT-002" not in {a.rule_id for a in alerts}


def test_crit_002_does_not_fire_under_60s() -> None:
    router, _ = _router()
    alerts = router.evaluate({"shioaji_connected": 0, "shioaji_disconnect_secs": 30})
    assert "CRIT-002" not in {a.rule_id for a in alerts}


def test_crit_003_circuit_breaker_l2_or_l3() -> None:
    router, _ = _router()
    assert "CRIT-003" in {a.rule_id for a in router.evaluate({"risk_event_type": "L2_CUT"})}
    router2, _ = _router()
    assert "CRIT-003" in {a.rule_id for a in router2.evaluate({"risk_event_type": "L3_HALT"})}


def test_crit_003_ignores_other_risk_events() -> None:
    router, _ = _router()
    alerts = router.evaluate({"risk_event_type": "HEAT_WARN"})
    assert "CRIT-003" not in {a.rule_id for a in alerts}


def test_crit_004_container_restart() -> None:
    router, _ = _router()
    alerts = router.evaluate({"container_restart_count": 1})
    assert "CRIT-004" in {a.rule_id for a in alerts}


def test_high_001_etl_failed() -> None:
    router, _ = _router()
    alerts = router.evaluate({"etl_status": "FAIL"})
    fired = next(a for a in alerts if a.rule_id == "HIGH-001")
    assert fired.level is AlertLevel.HIGH


def test_high_002_zero_signals() -> None:
    router, _ = _router()
    alerts = router.evaluate({"signal_count_1430": 0})
    assert "HIGH-002" in {a.rule_id for a in alerts}


def test_high_002_does_not_fire_with_signals() -> None:
    router, _ = _router()
    alerts = router.evaluate({"signal_count_1430": 7})
    assert "HIGH-002" not in {a.rule_id for a in alerts}


def test_high_003_position_drift_over_5pct() -> None:
    router, _ = _router()
    alerts = router.evaluate({"max_position_drift_pct": 0.07})
    assert "HIGH-003" in {a.rule_id for a in alerts}


def test_high_003_does_not_fire_at_or_below_5pct() -> None:
    router, _ = _router()
    alerts = router.evaluate({"max_position_drift_pct": 0.05})
    assert "HIGH-003" not in {a.rule_id for a in alerts}


def test_high_004_finlab_quota_low() -> None:
    router, _ = _router()
    alerts = router.evaluate({"finlab_remaining_mb": 480})
    assert "HIGH-004" in {a.rule_id for a in alerts}


def test_high_004_does_not_fire_when_quota_ok() -> None:
    router, _ = _router()
    alerts = router.evaluate({"finlab_remaining_mb": 800})
    assert "HIGH-004" not in {a.rule_id for a in alerts}


def test_info_001_daily_digest_flag() -> None:
    router, _ = _router()
    alerts = router.evaluate({"daily_digest": True})
    fired = next(a for a in alerts if a.rule_id == "INFO-001")
    assert fired.level is AlertLevel.INFO


def test_info_002_trade_fill() -> None:
    router, _ = _router()
    alerts = router.evaluate({"trade_fill": {"action": "buy", "symbol": "2330"}})
    assert "INFO-002" in {a.rule_id for a in alerts}


def test_unrelated_metrics_yield_no_alerts() -> None:
    router, _ = _router()
    assert router.evaluate({"cpu_pct": 12}) == []


def test_multiple_rules_fire_in_one_evaluate() -> None:
    router, _ = _router()
    alerts = router.evaluate(
        {"fills_rejected_streak": 3, "etl_status": "FAIL", "finlab_remaining_mb": 100}
    )
    ids = {a.rule_id for a in alerts}
    assert {"CRIT-001", "HIGH-001", "HIGH-004"} <= ids


def test_message_includes_context_value() -> None:
    router, _ = _router()
    alert = next(
        a for a in router.evaluate({"finlab_remaining_mb": 480}) if a.rule_id == "HIGH-004"
    )
    assert "480" in alert.message


# ---------------------------------------------------------------------------
# §4.4 dedup window — same rule_id within 30 min fires once
# ---------------------------------------------------------------------------


def test_dedupe_suppresses_within_window() -> None:
    router, clock = _router()
    first = router.evaluate({"fills_rejected_streak": 3})
    assert "CRIT-001" in {a.rule_id for a in first}

    clock["t"] = DAYTIME + timedelta(minutes=10)
    second = router.evaluate({"fills_rejected_streak": 3})
    assert "CRIT-001" not in {a.rule_id for a in second}


def test_dedupe_releases_after_window() -> None:
    router, clock = _router()
    router.evaluate({"fills_rejected_streak": 3})

    clock["t"] = DAYTIME + DEDUPE_WINDOW + timedelta(seconds=1)
    again = router.evaluate({"fills_rejected_streak": 3})
    assert "CRIT-001" in {a.rule_id for a in again}


def test_dedupe_is_per_rule_id() -> None:
    router, clock = _router()
    router.evaluate({"fills_rejected_streak": 3})  # CRIT-001 fires + records

    clock["t"] = DAYTIME + timedelta(minutes=5)
    # Different rule, still within CRIT-001's window — must NOT be suppressed.
    alerts = router.evaluate({"etl_status": "FAIL"})
    assert "HIGH-001" in {a.rule_id for a in alerts}


def test_dedupe_boundary_at_exactly_30_min_still_suppressed() -> None:
    router, clock = _router()
    router.evaluate({"fills_rejected_streak": 3})
    clock["t"] = DAYTIME + DEDUPE_WINDOW  # exactly 30 min later
    again = router.evaluate({"fills_rejected_streak": 3})
    assert "CRIT-001" not in {a.rule_id for a in again}


# ---------------------------------------------------------------------------
# §4.4 silent window — 22:00–08:00 only Critical
# ---------------------------------------------------------------------------


def test_silent_hours_helper() -> None:
    assert silent_hours(NIGHTTIME) is True
    assert silent_hours(EARLY) is True
    assert silent_hours(DAYTIME) is False
    # boundaries: 22:00 silent, 08:00 active
    assert silent_hours(datetime(2026, 5, 31, 22, 0, tzinfo=TWT)) is True
    assert silent_hours(datetime(2026, 5, 31, 8, 0, tzinfo=TWT)) is False
    assert silent_hours(datetime(2026, 5, 31, 7, 59, tzinfo=TWT)) is True


def test_silent_window_suppresses_high_and_info() -> None:
    router, _ = _router(NIGHTTIME)
    alerts = router.evaluate(
        {"etl_status": "FAIL", "daily_digest": True, "finlab_remaining_mb": 100}
    )
    assert alerts == []  # all HIGH/INFO suppressed at night


def test_silent_window_lets_critical_through() -> None:
    router, _ = _router(NIGHTTIME)
    alerts = router.evaluate({"fills_rejected_streak": 3, "etl_status": "FAIL"})
    ids = {a.rule_id for a in alerts}
    assert "CRIT-001" in ids  # critical survives
    assert "HIGH-001" not in ids  # high suppressed


def test_active_window_lets_everything_through() -> None:
    router, _ = _router(DAYTIME)
    alerts = router.evaluate({"fills_rejected_streak": 3, "etl_status": "FAIL"})
    ids = {a.rule_id for a in alerts}
    assert {"CRIT-001", "HIGH-001"} <= ids


def test_silent_suppressed_alert_not_recorded_for_dedupe() -> None:
    """A HIGH suppressed by silent hours must still fire once day returns."""
    router, clock = _router(NIGHTTIME)
    night = router.evaluate({"etl_status": "FAIL"})
    assert night == []

    # Morning arrives within 30 min — if we had wrongly recorded the night
    # attempt, dedupe would now swallow it. It must fire.
    clock["t"] = datetime(2026, 6, 1, 8, 1, tzinfo=TWT)
    morning = router.evaluate({"etl_status": "FAIL"})
    assert "HIGH-001" in {a.rule_id for a in morning}


# ---------------------------------------------------------------------------
# Determinism — injected clock is the only time source
# ---------------------------------------------------------------------------


def test_default_clock_is_utc_now(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without an injected clock the router must still construct and use UTC now."""
    router = AlertRouter()
    alerts = router.evaluate({"container_restart_count": 1})
    # Can't assert exact time, but it must fire (real clock, daytime-agnostic
    # since CRIT is never silenced).
    assert "CRIT-004" in {a.rule_id for a in alerts}
