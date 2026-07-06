"""Tests for validation/trials.py — trial-count → DSR deflation gate (8.G.4).

The more configurations we compare/scan, the more a high Sharpe is explained by
luck rather than edge. This module turns that selection-bias intuition into an
operable guardrail: a ``TrialsCounter`` to accumulate how many trials we ran, a
``deflated_sharpe_pass`` boolean wrapping ``validation.dsr.deflated_sharpe_ratio``
against ADR-016's ``DSR > 0.95`` bar, and a ``trials_deflated_criterion`` that
returns a gate-pluggable ``(label, passed, dsr_value, n_trials)`` structure so
"I tried N times, my Sharpe got deflated to X" is visible.

Numeric ground truth is recomputed from ``validation.dsr`` directly — no magic
constants — so the test asserts wiring + monotonicity, not a re-derivation of the
DSR closed form (already covered by test_dsr.py).
"""
from __future__ import annotations

import pytest

from quant_platform.services.research_validation.validation.dsr import deflated_sharpe_ratio
from quant_platform.services.research_validation.validation.trials import (
    TrialsCounter,
    TrialsDeflatedResult,
    deflated_sharpe_pass,
    trials_deflated_criterion,
)

# --------------------------------------------------------------------------- #
# TrialsCounter — cumulative trial accounting
# --------------------------------------------------------------------------- #


def test_counter_starts_at_zero():
    assert TrialsCounter().n_trials == 0


def test_counter_record_default_increments_by_one():
    c = TrialsCounter()
    c.record()
    c.record()
    assert c.n_trials == 2


def test_counter_record_accumulates_batches():
    c = TrialsCounter()
    c.record(5)
    c.record(3)
    assert c.n_trials == 8


def test_counter_can_start_from_nonzero():
    c = TrialsCounter(n_trials=10)
    c.record(2)
    assert c.n_trials == 12


def test_counter_record_returns_new_total():
    c = TrialsCounter()
    assert c.record(4) == 4
    assert c.record(1) == 5


def test_counter_rejects_non_positive_batch():
    c = TrialsCounter()
    with pytest.raises(ValueError):
        c.record(0)
    with pytest.raises(ValueError):
        c.record(-1)


def test_counter_rejects_negative_initial():
    with pytest.raises(ValueError):
        TrialsCounter(n_trials=-1)


# --------------------------------------------------------------------------- #
# deflated_sharpe_pass — boolean guardrail wrapping the DSR closed form
# --------------------------------------------------------------------------- #

# A strong-but-finite backtest: high SR, plenty of obs, mild non-normality.
_STRONG = dict(sr=0.18, n_obs=1500, skew=-0.2, kurtosis=4.0, sharpe_variance=0.02)


def test_pass_matches_dsr_against_threshold():
    """The boolean is exactly ``DSR > threshold`` using the canonical DSR fn."""
    dsr = deflated_sharpe_ratio(n_trials=1, **_STRONG)
    assert deflated_sharpe_pass(n_trials=1, **_STRONG) is (dsr > 0.95)


def test_pass_default_threshold_is_adr016_095():
    """Default bar is ADR-016 DSR > 0.95."""
    dsr = deflated_sharpe_ratio(n_trials=1, **_STRONG)
    assert deflated_sharpe_pass(n_trials=1, **_STRONG) is bool(dsr > 0.95)


def test_more_trials_lowers_dsr():
    """Selection bias: SR* grows with n_trials ⇒ DSR is non-increasing in trials."""
    dsr_few = deflated_sharpe_ratio(n_trials=2, **_STRONG)
    dsr_many = deflated_sharpe_ratio(n_trials=500, **_STRONG)
    assert dsr_many < dsr_few


def test_more_trials_flips_pass_to_fail():
    """The headline guardrail: enough trials deflate a passing SR into a fail.

    We bracket a threshold so a small trial count passes and a large one fails;
    this is the 'compare more → closer to false-significance' guard made operable.
    """
    passing = deflated_sharpe_pass(n_trials=1, threshold=0.95, **_STRONG)
    failing = deflated_sharpe_pass(n_trials=100_000, threshold=0.95, **_STRONG)
    assert passing is True
    assert failing is False


def test_pass_is_strict_greater_not_geq():
    """Boundary: DSR exactly equal to threshold must NOT pass (strict >)."""
    dsr = deflated_sharpe_ratio(n_trials=3, **_STRONG)
    # threshold set to the exact DSR value ⇒ strict > fails.
    assert deflated_sharpe_pass(n_trials=3, threshold=dsr, **_STRONG) is False
    # a hair below ⇒ passes.
    assert deflated_sharpe_pass(n_trials=3, threshold=dsr - 1e-9, **_STRONG) is True


def test_n_trials_one_means_no_deflation():
    """n_trials==1 ⇒ SR*=0 ⇒ DSR == raw PSR (no selection penalty)."""
    from quant_platform.services.research_validation.validation.dsr import psr

    dsr = deflated_sharpe_ratio(n_trials=1, **_STRONG)
    raw = psr(
        _STRONG["sr"],
        n_obs=_STRONG["n_obs"],
        skew=_STRONG["skew"],
        kurtosis=_STRONG["kurtosis"],
    )
    assert dsr == pytest.approx(raw)


# --------------------------------------------------------------------------- #
# trials_deflated_criterion — gate-pluggable result structure
# --------------------------------------------------------------------------- #


def test_criterion_returns_structure_with_four_fields():
    res = trials_deflated_criterion(n_trials=1, **_STRONG)
    assert isinstance(res, TrialsDeflatedResult)
    assert hasattr(res, "label")
    assert hasattr(res, "passed")
    assert hasattr(res, "dsr_value")
    assert hasattr(res, "n_trials")


def test_criterion_unpacks_as_tuple():
    """Spec: a (label, passed, dsr_value, n_trials) structure addable to a gate."""
    label, passed, dsr_value, n_trials = trials_deflated_criterion(
        n_trials=7, **_STRONG
    )
    assert isinstance(label, str)
    assert isinstance(passed, bool)
    assert isinstance(dsr_value, float)
    assert n_trials == 7


def test_criterion_dsr_value_matches_closed_form():
    res = trials_deflated_criterion(n_trials=12, **_STRONG)
    assert res.dsr_value == pytest.approx(
        deflated_sharpe_ratio(n_trials=12, **_STRONG)
    )


def test_criterion_passed_agrees_with_boolean_helper():
    res = trials_deflated_criterion(n_trials=42, threshold=0.95, **_STRONG)
    assert res.passed is deflated_sharpe_pass(
        n_trials=42, threshold=0.95, **_STRONG
    )


def test_criterion_label_surfaces_trials_and_threshold():
    """Label must make 'tried N, deflated to X' visible for the gate summary."""
    res = trials_deflated_criterion(n_trials=250, threshold=0.95, **_STRONG)
    assert "250" in res.label
    assert "DSR" in res.label


def test_criterion_accepts_a_counter_as_trial_source():
    """Ergonomics: a TrialsCounter can drive the criterion directly."""
    counter = TrialsCounter()
    counter.record(9)
    res = trials_deflated_criterion(n_trials=counter.n_trials, **_STRONG)
    assert res.n_trials == 9


def test_criterion_more_trials_flips_passed_field():
    few = trials_deflated_criterion(n_trials=1, threshold=0.95, **_STRONG)
    many = trials_deflated_criterion(n_trials=100_000, threshold=0.95, **_STRONG)
    assert few.passed is True
    assert many.passed is False
    assert many.dsr_value < few.dsr_value


def test_result_is_frozen():
    res = trials_deflated_criterion(n_trials=1, **_STRONG)
    with pytest.raises(Exception):
        res.passed = False  # type: ignore[misc]
