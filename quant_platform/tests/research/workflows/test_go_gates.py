"""workflow.go_gates — WFA + PBO via dispatch (synthetic loader)."""
from __future__ import annotations

from datetime import date

from quant_platform.services.research_validation import runners as _runners  # noqa: F401
from quant_platform.services.research_validation.workflows.config import GOGatesConfig
from quant_platform.services.research_validation.workflows.go_gates import GOGatesResult, run_go_gates
from quant_platform.services.research_validation.strategies.conformance import synthetic_loader
from quant_platform.services.research_validation.strategies.momentum.strategy import MomentumConfig


def _cfg():
    return GOGatesConfig(
        strategy="momentum",
        fixed_config=MomentumConfig(lookback_days=120),
        config_grid={"lookback_days": [120, 252]},
        symbols=[f"SYN{i:04d}" for i in range(5)],
        is_start=date(2015, 1, 1),
        is_end=date(2022, 12, 31),
        n_wfa_folds=3,
        pbo_n_splits=4,
    )


def test_run_go_gates_returns_result():
    result = run_go_gates(_cfg(), loader=synthetic_loader(n_bars=800))
    assert isinstance(result, GOGatesResult)
    assert result.strategy == "momentum"


def test_result_has_wfa_fraction():
    result = run_go_gates(_cfg(), loader=synthetic_loader(n_bars=800))
    assert 0.0 <= result.wfa_oos_positive_frac <= 1.0


def test_result_has_pbo_when_grid_provided():
    result = run_go_gates(_cfg(), loader=synthetic_loader(n_bars=800))
    # pbo may be None if the matrix is too small, else within [0, 1]
    assert result.pbo is None or 0.0 <= result.pbo <= 1.0


def test_result_has_verdict():
    result = run_go_gates(_cfg(), loader=synthetic_loader(n_bars=800))
    assert result.verdict in ("PASS", "FAIL", "INCOMPLETE")
