"""Tests for the 3-level circuit breaker state machine (24_risk_management_spec §4).

Strategy-agnostic. All inputs are injected synthetic ``RiskMetrics`` snapshots;
no DB, no network, no broker. Each test maps to a row in the spec's trigger /
recovery matrix (§4.1–§4.3) and the config defaults (§10).
"""
from __future__ import annotations

import dataclasses

import pytest

from backtest_platform.risk.circuit_breaker import (
    BreakerState,
    CircuitBreaker,
    CircuitBreakerConfig,
    RiskMetrics,
)


# --- helpers ---------------------------------------------------------------

def _metrics(**kw) -> RiskMetrics:
    """RiskMetrics with benign defaults; override only the fields under test."""
    base = dict(
        current_dd=0.0,
        daily_dd=0.0,
        consecutive_losses=0,
        shioaji_errors=0,
        reconciliation_failed=False,
        exceptions_last_hour=0,
    )
    base.update(kw)
    return RiskMetrics(**base)


@pytest.fixture
def breaker() -> CircuitBreaker:
    # dd_limit=0.15 → L1@15%, L2@22.5%, L3@30% (spec §4.2 worked examples)
    return CircuitBreaker(config=CircuitBreakerConfig())


# --- config / construction -------------------------------------------------

def test_default_config_matches_spec_section_10():
    cfg = CircuitBreakerConfig()
    assert cfg.dd_limit == pytest.approx(0.15)
    assert cfg.l1_dd_multiplier == pytest.approx(1.0)
    assert cfg.l2_dd_multiplier == pytest.approx(1.5)
    assert cfg.l3_dd_multiplier == pytest.approx(2.0)
    assert cfg.l1_recovery_dd == pytest.approx(0.7)
    assert cfg.l1_recovery_days == 3
    assert cfg.l2_recovery_days == 5
    assert cfg.consecutive_loss_l1 == 5
    assert cfg.consecutive_loss_l2 == 8


def test_config_is_immutable():
    cfg = CircuitBreakerConfig()
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.dd_limit = 0.99  # type: ignore[misc]


def test_metrics_is_immutable():
    m = _metrics(current_dd=0.10)
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.current_dd = 0.50  # type: ignore[misc]


def test_invalid_config_rejected():
    with pytest.raises(ValueError):
        CircuitBreakerConfig(dd_limit=0.0)
    with pytest.raises(ValueError):
        CircuitBreakerConfig(l2_dd_multiplier=0.9)  # must exceed L1
    with pytest.raises(ValueError):
        CircuitBreakerConfig(l3_dd_multiplier=1.4)  # must exceed L2


# --- DD thresholds → level (§4.2) -----------------------------------------

def test_normal_when_no_breach(breaker):
    assert breaker.evaluate(_metrics()) is BreakerState.NORMAL


def test_dd_just_below_l1_stays_normal(breaker):
    # 14.9% < 15% limit
    assert breaker.evaluate(_metrics(current_dd=0.149)) is BreakerState.NORMAL


def test_dd_at_limit_triggers_l1(breaker):
    # exactly 15% → ratio 1.0 → L1 (boundary inclusive)
    assert breaker.evaluate(_metrics(current_dd=0.15)) is BreakerState.L1


def test_dd_uses_absolute_value(breaker):
    # DD reported as a negative number must still trigger
    assert breaker.evaluate(_metrics(current_dd=-0.16)) is BreakerState.L1


def test_dd_at_1_5x_triggers_l2(breaker):
    assert breaker.evaluate(_metrics(current_dd=0.225)) is BreakerState.L2


def test_dd_at_2x_triggers_l3_and_latches_halted(breaker):
    # L3 is "human reset only" (spec §4.2) → the machine latches into HALTED.
    assert breaker.evaluate(_metrics(current_dd=0.30)) is BreakerState.HALTED


def test_dd_above_2x_triggers_l3_and_latches_halted(breaker):
    assert breaker.evaluate(_metrics(current_dd=0.45)) is BreakerState.HALTED


# --- non-DD triggers (§4.3) -----------------------------------------------

def test_consecutive_losses_5_triggers_l1(breaker):
    assert breaker.evaluate(_metrics(consecutive_losses=5)) is BreakerState.L1


def test_consecutive_losses_8_triggers_l2(breaker):
    assert breaker.evaluate(_metrics(consecutive_losses=8)) is BreakerState.L2


def test_daily_dd_over_10pct_triggers_l2(breaker):
    # single-day DD > 10% is an L2 trigger even when cumulative DD is mild
    assert breaker.evaluate(_metrics(daily_dd=0.11, current_dd=0.05)) is BreakerState.L2


def test_shioaji_errors_5_triggers_l3(breaker):
    assert breaker.evaluate(_metrics(shioaji_errors=5)) is BreakerState.HALTED


def test_reconciliation_failure_triggers_l3(breaker):
    assert breaker.evaluate(_metrics(reconciliation_failed=True)) is BreakerState.HALTED


def test_exceptions_10_per_hour_triggers_l3(breaker):
    assert breaker.evaluate(_metrics(exceptions_last_hour=10)) is BreakerState.HALTED


def test_worst_trigger_wins_when_multiple_fire(breaker):
    # mild DD (L1) but reconciliation failed (L3) → L3 (HALTED) must win
    m = _metrics(current_dd=0.16, reconciliation_failed=True)
    assert breaker.evaluate(m) is BreakerState.HALTED


# --- state machine: escalation is immediate, monotonic up -----------------

def test_evaluate_persists_current_state(breaker):
    assert breaker.state is BreakerState.NORMAL
    breaker.evaluate(_metrics(current_dd=0.15))
    assert breaker.state is BreakerState.L1


def test_escalation_normal_to_l1_to_l2_to_l3(breaker):
    assert breaker.evaluate(_metrics(current_dd=0.15)) is BreakerState.L1
    assert breaker.evaluate(_metrics(current_dd=0.23)) is BreakerState.L2
    assert breaker.evaluate(_metrics(current_dd=0.31)) is BreakerState.HALTED


def test_l3_trigger_records_transition_as_halted(breaker):
    # The classification level is L3 but the persisted/terminal state is HALTED;
    # the audit log records the latched HALTED target.
    breaker.evaluate(_metrics(current_dd=0.31))
    assert breaker.state is BreakerState.HALTED
    assert breaker.transitions[-1].to_state is BreakerState.HALTED
    assert "L3" in (breaker.transitions[-1].reason or "")


def test_l3_latches_to_halted_and_cannot_auto_recover(breaker):
    breaker.evaluate(_metrics(current_dd=0.31))  # -> L3
    # once halted, a clean metric snapshot must NOT silently recover
    result = breaker.evaluate(_metrics(current_dd=0.0))
    assert result is BreakerState.HALTED
    assert breaker.state is BreakerState.HALTED


# --- recovery requires conditions sustained over N days (§4.1/§4.2) --------

def test_l1_does_not_recover_before_threshold(breaker):
    breaker.evaluate(_metrics(current_dd=0.15))  # -> L1
    # DD now below 0.7x limit (=10.5%) but only 1 day → no recovery yet
    assert breaker.evaluate(_metrics(current_dd=0.10)) is BreakerState.L1


def test_l1_recovers_after_3_clean_days(breaker):
    breaker.evaluate(_metrics(current_dd=0.15))  # -> L1
    clean = _metrics(current_dd=0.10)  # < 0.7 * 0.15 = 0.105
    assert breaker.evaluate(clean) is BreakerState.L1  # day 1
    assert breaker.evaluate(clean) is BreakerState.L1  # day 2
    assert breaker.evaluate(clean) is BreakerState.NORMAL  # day 3


def test_l1_recovery_streak_resets_on_relapse(breaker):
    breaker.evaluate(_metrics(current_dd=0.15))  # -> L1
    clean = _metrics(current_dd=0.10)
    breaker.evaluate(clean)  # day 1
    breaker.evaluate(_metrics(current_dd=0.14))  # relapse: DD back up, streak resets
    assert breaker.state is BreakerState.L1
    # need a fresh 3-day clean streak again
    breaker.evaluate(clean)
    breaker.evaluate(clean)
    assert breaker.evaluate(clean) is BreakerState.NORMAL


def test_l2_de_escalates_to_l1_after_5_clean_days(breaker):
    breaker.evaluate(_metrics(current_dd=0.23))  # -> L2
    # DD < 1.0x limit (15%) sustained 5 days → step down to L1 (not straight to NORMAL)
    partial = _metrics(current_dd=0.14)
    for _ in range(4):
        assert breaker.evaluate(partial) is BreakerState.L2
    assert breaker.evaluate(partial) is BreakerState.L1


def test_l2_re_escalates_immediately_on_new_l3_breach(breaker):
    breaker.evaluate(_metrics(current_dd=0.23))  # -> L2
    # recovery is gradual but escalation is immediate; L3 latches to HALTED
    assert breaker.evaluate(_metrics(current_dd=0.31)) is BreakerState.HALTED


# --- manual reset (§4.2 L3 = human reset only) ----------------------------

def test_manual_reset_clears_halted(breaker):
    breaker.evaluate(_metrics(current_dd=0.31))  # -> L3 -> HALTED
    breaker.reset()
    assert breaker.state is BreakerState.NORMAL


def test_reset_records_transition(breaker):
    breaker.evaluate(_metrics(current_dd=0.31))
    n_before = len(breaker.transitions)
    breaker.reset(reason="post-incident review")
    assert len(breaker.transitions) == n_before + 1
    last = breaker.transitions[-1]
    assert last.to_state is BreakerState.NORMAL
    assert last.manual is True
    assert "review" in (last.reason or "")


# --- query helpers for the order layer (EX-012 hook) ----------------------

def test_should_halt_only_when_halted(breaker):
    assert breaker.should_halt() is False
    breaker.evaluate(_metrics(current_dd=0.31))
    assert breaker.should_halt() is True


def test_should_reduce_at_l2_and_above(breaker):
    assert breaker.should_reduce() is False
    breaker.evaluate(_metrics(current_dd=0.23))  # L2
    assert breaker.should_reduce() is True
    breaker.evaluate(_metrics(current_dd=0.31))  # HALTED
    assert breaker.should_reduce() is True


def test_should_block_new_entries_at_l1_and_above(breaker):
    # buy/add blocked at any non-NORMAL state (spec §5.1: add/buy intercepted at L1/L2/L3)
    assert breaker.should_block_new_entries() is False
    breaker.evaluate(_metrics(current_dd=0.15))  # L1
    assert breaker.should_block_new_entries() is True


def test_allows_protective_signals_always(breaker):
    # stoploss/exit/reduce must never be blocked, even when halted (§5.1)
    breaker.evaluate(_metrics(current_dd=0.31))
    assert breaker.allows_protective_exit() is True


# --- transition log -------------------------------------------------------

def test_transitions_record_from_to_and_trigger(breaker):
    breaker.evaluate(_metrics(current_dd=0.15, consecutive_losses=5))
    t = breaker.transitions[-1]
    assert t.from_state is BreakerState.NORMAL
    assert t.to_state is BreakerState.L1
    assert t.reason  # human-readable trigger description
    assert t.metrics_snapshot.current_dd == pytest.approx(0.15)


def test_no_transition_logged_when_state_unchanged(breaker):
    breaker.evaluate(_metrics())  # stays NORMAL
    assert breaker.transitions == []


def test_reset_on_non_halted_is_idempotent(breaker):
    # resetting an already-NORMAL breaker is a no-op (no spurious transition)
    breaker.reset()
    assert breaker.state is BreakerState.NORMAL
    assert breaker.transitions == []
