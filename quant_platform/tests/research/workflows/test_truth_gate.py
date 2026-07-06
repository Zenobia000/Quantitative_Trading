"""workflow.truth_gate — ADR-025 two-stage gate via dispatch (synthetic loader)."""
from __future__ import annotations

from datetime import date

from quant_platform.services.research_validation import runners as _runners  # noqa: F401
from quant_platform.services.research_validation.workflows.config import TruthGateConfig
from quant_platform.services.research_validation.workflows.truth_gate import TruthGateResult, run_truth_gate
from quant_platform.services.research_validation.strategies.conformance import synthetic_loader
from quant_platform.services.research_validation.strategies.momentum.strategy import MomentumConfig


def _cfg():
    return TruthGateConfig(
        strategy="momentum",
        fixed_config=MomentumConfig(lookback_days=120),
        symbols=[f"SYN{i:04d}" for i in range(6)],
        is_start=date(2015, 1, 1),
        oos_start=date(2020, 1, 1),
        is_end=date(2022, 12, 31),
        n_trials=8,
        slippage_stress=0.003,
        n_wfa_folds=3,
    )


def test_run_truth_gate_returns_result():
    result = run_truth_gate(_cfg(), loader=synthetic_loader(n_bars=800))
    assert isinstance(result, TruthGateResult)
    assert result.strategy == "momentum"


def test_result_has_verdict():
    result = run_truth_gate(_cfg(), loader=synthetic_loader(n_bars=800))
    assert result.verdict in ("REAL", "REJECTED", "INCOMPLETE")


def test_result_has_dsr():
    result = run_truth_gate(_cfg(), loader=synthetic_loader(n_bars=800))
    assert isinstance(result.dsr, float)


def test_result_has_slippage_sharpe():
    result = run_truth_gate(_cfg(), loader=synthetic_loader(n_bars=800))
    assert isinstance(result.slippage_sharpe, float)


def test_result_has_wfa_fraction():
    result = run_truth_gate(_cfg(), loader=synthetic_loader(n_bars=800))
    assert 0.0 <= result.wfa_oos_positive_frac <= 1.0
