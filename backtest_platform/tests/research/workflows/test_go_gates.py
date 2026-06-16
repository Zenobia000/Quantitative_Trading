from datetime import date
import pytest
from backtest_platform.research import runners as _runners  # noqa: F401
from backtest_platform.research.workflows.config import GOGatesConfig
from backtest_platform.research.workflows.go_gates import run_go_gates, GOGatesResult
from backtest_platform.strategies.conformance import synthetic_loader
from backtest_platform.strategies.momentum.strategy import MomentumConfig

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
    assert result.pbo is not None
    assert 0.0 <= result.pbo <= 1.0

def test_result_has_verdict():
    result = run_go_gates(_cfg(), loader=synthetic_loader(n_bars=800))
    assert result.verdict in ("PASS", "FAIL", "INCOMPLETE")
