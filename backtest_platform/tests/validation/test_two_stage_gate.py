"""two_stage_gate — ADR-025 truth gate (binary hard-fail) + sizing gate (continuous).

The single binary ADR-016 gate conflated "is this edge real?" with "deploy it?".
ADR-025 splits them: the TruthGate is anti-self-deception (survivorship-clean +
overfit controls, hard-fail); the SizingGate maps a *passed* strategy to a
*continuous* position size (a 0.9-Sharpe sleeve is a small allocation, not a
rejection). These tests pin the ADR's two crux decisions:

  1. A pre-registered single config is judged on OOS>0 frac + DSR, NOT landscape
     PBO (which measures config-SELECTION overfit) — this is what separates
     inst_flow's WFA OOS 1.30 from its landscape PBO 43%.
  2. Passing the truth gate yields a *size*, not a yes/no — absolute CAGR is
     carried as reference only and never drives the allocation.
"""
from __future__ import annotations

import pytest

from backtest_platform.validation.two_stage_gate import (
    DSR_MIN,
    PBO_MAX,
    WFA_OOS_POSITIVE_MIN,
    SizingConfig,
    SizingInput,
    TruthGateInput,
    TruthVerdict,
    compute_position_size,
    evaluate_truth_gate,
    evaluate_two_stage,
    fleet_correlation,
)

# --------------------------------------------------------------------------- #
# Truth gate — survivorship is a hard precondition for every path
# --------------------------------------------------------------------------- #


def test_survivorship_dirty_is_rejected_regardless_of_strong_stats() -> None:
    # Even a stunning pre-registered OOS record is REJECTED if the universe is
    # survivor-only — this is the death both momentum and inst_flow shared.
    inp = TruthGateInput(
        survivorship_clean=False,
        pre_registered=True,
        wfa_oos_positive_frac=0.95,
        dsr=0.99,
        slippage_sharpe=1.2,
    )
    r = evaluate_truth_gate(inp)
    assert r.verdict is TruthVerdict.REJECTED
    assert any("survivorship" in reason.lower() for reason in r.reasons)


# --------------------------------------------------------------------------- #
# Truth gate — pre-registered single config: OOS frac + DSR, NOT landscape PBO
# --------------------------------------------------------------------------- #


def test_pre_registered_passes_on_oos_and_dsr_even_with_high_landscape_pbo() -> None:
    # The inst_flow crux: fixed (a priori) config, survivorship-clean WFA median
    # OOS 1.30, OOS>0 in most folds. Landscape PBO 0.43 is HIGH but irrelevant to
    # a config that was never selected from a sweep → REAL.
    inp = TruthGateInput(
        survivorship_clean=True,
        pre_registered=True,
        pbo=0.43,  # high, but must be ignored for a pre-registered config
        wfa_oos_positive_frac=0.92,
        dsr=0.97,
        slippage_sharpe=1.0,
    )
    r = evaluate_truth_gate(inp)
    assert r.verdict is TruthVerdict.REAL
    assert r.is_real is True


def test_pre_registered_rejected_when_oos_breadth_too_thin() -> None:
    inp = TruthGateInput(
        survivorship_clean=True,
        pre_registered=True,
        wfa_oos_positive_frac=0.50,  # < 0.60
        dsr=0.97,
        slippage_sharpe=1.0,
    )
    r = evaluate_truth_gate(inp)
    assert r.verdict is TruthVerdict.REJECTED


def test_pre_registered_rejected_when_dsr_below_floor() -> None:
    inp = TruthGateInput(
        survivorship_clean=True,
        pre_registered=True,
        wfa_oos_positive_frac=0.80,
        dsr=0.50,  # < DSR_MIN
        slippage_sharpe=1.0,
    )
    r = evaluate_truth_gate(inp)
    assert r.verdict is TruthVerdict.REJECTED


def test_pre_registered_incomplete_when_oos_metric_missing() -> None:
    inp = TruthGateInput(
        survivorship_clean=True,
        pre_registered=True,
        dsr=0.97,
        slippage_sharpe=1.0,
        # wfa_oos_positive_frac missing
    )
    r = evaluate_truth_gate(inp)
    assert r.verdict is TruthVerdict.INCOMPLETE
    assert r.is_real is False


def test_pre_registered_incomplete_when_dsr_missing() -> None:
    inp = TruthGateInput(
        survivorship_clean=True,
        pre_registered=True,
        wfa_oos_positive_frac=0.92,
        slippage_sharpe=1.0,
        # dsr missing
    )
    r = evaluate_truth_gate(inp)
    assert r.verdict is TruthVerdict.INCOMPLETE
    assert any("dsr" in reason.lower() for reason in r.reasons)


# --------------------------------------------------------------------------- #
# Truth gate — selected config: landscape PBO IS the relevant overfit control
# --------------------------------------------------------------------------- #


def test_selected_config_rejected_on_high_pbo() -> None:
    # momentum / multi-factor / long-short death: config chosen from a sweep with
    # landscape PBO 0.43-0.77 → selection overfit → REJECTED.
    inp = TruthGateInput(
        survivorship_clean=True,
        pre_registered=False,
        pbo=0.43,
        slippage_sharpe=1.0,
    )
    r = evaluate_truth_gate(inp)
    assert r.verdict is TruthVerdict.REJECTED
    assert any("pbo" in reason.lower() for reason in r.reasons)


def test_selected_config_passes_on_low_pbo() -> None:
    inp = TruthGateInput(
        survivorship_clean=True,
        pre_registered=False,
        pbo=0.11,
        slippage_sharpe=1.0,
    )
    r = evaluate_truth_gate(inp)
    assert r.verdict is TruthVerdict.REAL


def test_selected_config_incomplete_when_pbo_missing() -> None:
    inp = TruthGateInput(
        survivorship_clean=True,
        pre_registered=False,
        slippage_sharpe=1.0,
        # pbo missing
    )
    r = evaluate_truth_gate(inp)
    assert r.verdict is TruthVerdict.INCOMPLETE


# --------------------------------------------------------------------------- #
# Truth gate — K3 slippage robustness applies to every path
# --------------------------------------------------------------------------- #


def test_slippage_collapse_rejected() -> None:
    inp = TruthGateInput(
        survivorship_clean=True,
        pre_registered=True,
        wfa_oos_positive_frac=0.92,
        dsr=0.97,
        slippage_sharpe=-0.5,  # OOS crashes under 0.3% per-leg slippage
    )
    r = evaluate_truth_gate(inp)
    assert r.verdict is TruthVerdict.REJECTED
    assert any("slippage" in reason.lower() for reason in r.reasons)


def test_slippage_missing_is_incomplete() -> None:
    inp = TruthGateInput(
        survivorship_clean=True,
        pre_registered=True,
        wfa_oos_positive_frac=0.92,
        dsr=0.97,
        # slippage_sharpe missing
    )
    r = evaluate_truth_gate(inp)
    assert r.verdict is TruthVerdict.INCOMPLETE


def test_thresholds_are_data_constants() -> None:
    # Tuning a threshold must be a visible, recordable change — not a buried edit.
    assert PBO_MAX == 0.30
    assert WFA_OOS_POSITIVE_MIN == 0.60
    assert DSR_MIN == 0.95


# --------------------------------------------------------------------------- #
# Sizing gate — continuous allocation, CAGR is reference only
# --------------------------------------------------------------------------- #


def test_nonpositive_sharpe_gets_zero_size() -> None:
    assert compute_position_size(SizingInput(oos_sharpe=0.0)) == 0.0
    assert compute_position_size(SizingInput(oos_sharpe=-0.5)) == 0.0


def test_subthreshold_sharpe_still_gets_a_real_allocation() -> None:
    # The whole point of ADR-025: 0.9 Sharpe is a SMALL position, not a rejection.
    size = compute_position_size(
        SizingInput(oos_sharpe=0.9, correlation_to_fleet=0.0, capacity_fraction=1.0)
    )
    assert size == pytest.approx(0.25 * 0.9)  # max_weight * conviction
    assert size > 0.0


def test_conviction_caps_at_reference_sharpe() -> None:
    # Sharpe 1.5 with reference 1.0 → conviction capped at 1.0 → full max_weight.
    size = compute_position_size(
        SizingInput(oos_sharpe=1.5, correlation_to_fleet=0.0, capacity_fraction=1.0)
    )
    assert size == pytest.approx(0.25)


def test_correlation_haircut_shrinks_size() -> None:
    base = compute_position_size(
        SizingInput(oos_sharpe=1.0, correlation_to_fleet=0.0, capacity_fraction=1.0)
    )
    correlated = compute_position_size(
        SizingInput(oos_sharpe=1.0, correlation_to_fleet=0.8, capacity_fraction=1.0)
    )
    assert correlated == pytest.approx(base * 0.2)
    assert correlated < base


def test_negative_correlation_is_not_penalised() -> None:
    # A diversifying (negative-corr) sleeve should not be shrunk below zero-corr.
    neg = compute_position_size(
        SizingInput(oos_sharpe=1.0, correlation_to_fleet=-0.5, capacity_fraction=1.0)
    )
    zero = compute_position_size(
        SizingInput(oos_sharpe=1.0, correlation_to_fleet=0.0, capacity_fraction=1.0)
    )
    assert neg == pytest.approx(zero)


def test_capacity_scales_size_down() -> None:
    half = compute_position_size(
        SizingInput(oos_sharpe=1.0, correlation_to_fleet=0.0, capacity_fraction=0.5)
    )
    assert half == pytest.approx(0.25 * 0.5)


def test_cagr_does_not_affect_size() -> None:
    # Absolute CAGR is reference only — a market-neutral sleeve with low CAGR but
    # solid Sharpe is sized on Sharpe, not punished for CAGR.
    lo = compute_position_size(SizingInput(oos_sharpe=1.0, cagr=0.05))
    hi = compute_position_size(SizingInput(oos_sharpe=1.0, cagr=0.30))
    assert lo == hi


def test_sizing_config_is_tunable() -> None:
    size = compute_position_size(
        SizingInput(oos_sharpe=1.0),
        SizingConfig(max_weight=0.50, reference_sharpe=2.0),
    )
    # conviction = 1.0/2.0 = 0.5; size = 0.50 * 0.5 = 0.25
    assert size == pytest.approx(0.25)


# --------------------------------------------------------------------------- #
# Two-stage orchestration — truth gate is the precondition for any size
# --------------------------------------------------------------------------- #


def test_truth_fail_forces_zero_size_even_with_great_sharpe() -> None:
    decision = evaluate_two_stage(
        TruthGateInput(
            survivorship_clean=False,  # hard-fail
            pre_registered=True,
            wfa_oos_positive_frac=0.95,
            dsr=0.99,
            slippage_sharpe=1.5,
        ),
        SizingInput(oos_sharpe=2.0),
    )
    assert decision.truth.is_real is False
    assert decision.size == 0.0


def test_truth_real_yields_sized_allocation() -> None:
    decision = evaluate_two_stage(
        TruthGateInput(
            survivorship_clean=True,
            pre_registered=True,
            pbo=0.43,
            wfa_oos_positive_frac=0.92,
            dsr=0.97,
            slippage_sharpe=1.0,
        ),
        SizingInput(oos_sharpe=0.9, correlation_to_fleet=0.0, capacity_fraction=1.0),
    )
    assert decision.truth.is_real is True
    assert decision.size == pytest.approx(0.25 * 0.9)


# --------------------------------------------------------------------------- #
# fleet_correlation — computes SizingInput.correlation_to_fleet from returns (8.G.10)
# --------------------------------------------------------------------------- #
def _series(values, start="2020-01-01"):
    import pandas as pd

    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="B"))


def test_fleet_correlation_empty_fleet_is_zero():
    assert fleet_correlation(_series([0.01, -0.02, 0.03]), []) == 0.0


def test_fleet_correlation_identical_series_is_one():
    s = _series([0.01, -0.02, 0.03, 0.005, -0.01])
    assert fleet_correlation(s, [s]) == pytest.approx(1.0)


def test_fleet_correlation_anti_correlated_is_negative_one():
    s = _series([0.01, -0.02, 0.03, 0.005, -0.01])
    assert fleet_correlation(s, [-s]) == pytest.approx(-1.0)


def test_fleet_correlation_averages_over_members_and_aligns_dates():
    s = _series([0.01, -0.02, 0.03, 0.005, -0.01])
    # one identical (corr 1), one anti (corr -1) → mean 0
    assert fleet_correlation(s, [s, -s]) == pytest.approx(0.0)


def test_fleet_correlation_skips_degenerate_constant_member():
    import pandas as pd

    s = _series([0.01, -0.02, 0.03, 0.005, -0.01])
    constant = pd.Series(0.0, index=s.index)  # zero variance → NaN corr, skipped
    assert fleet_correlation(s, [s, constant]) == pytest.approx(1.0)
