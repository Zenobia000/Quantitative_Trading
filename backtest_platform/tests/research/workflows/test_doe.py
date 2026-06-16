from datetime import date
import ast, pathlib
import pytest
from backtest_platform.research import runners as _runners  # noqa: F401
from backtest_platform.research.workflows.config import DOEConfig
from backtest_platform.research.workflows.doe import run_doe, DOEResult
from backtest_platform.strategies.conformance import synthetic_loader

def _doe_cfg():
    return DOEConfig(
        strategy="momentum",
        grid={"lookback_days": [120, 252], "rebalance": ["monthly"]},
        symbols=["SYN0001", "SYN0002", "SYN0003"],
        is_start=date(2019, 1, 1),
        is_end=date(2020, 12, 31),
    )

def test_run_doe_returns_doe_result():
    result = run_doe(_doe_cfg(), loader=synthetic_loader(n_bars=600))
    assert isinstance(result, DOEResult)
    assert result.strategy == "momentum"

def test_run_doe_n_configs_matches_grid():
    result = run_doe(_doe_cfg(), loader=synthetic_loader(n_bars=600))
    assert result.n_configs == 2

def test_run_doe_each_run_has_required_metrics():
    result = run_doe(_doe_cfg(), loader=synthetic_loader(n_bars=600))
    required = {"cagr", "sharpe", "slippage_sharpe", "maxdd", "trades", "bars"}
    for row in result.runs:
        assert required <= row.keys(), f"missing keys: {required - row.keys()}"

def test_run_doe_each_run_has_grid_params():
    result = run_doe(_doe_cfg(), loader=synthetic_loader(n_bars=600))
    for row in result.runs:
        assert "lookback_days" in row
        assert "rebalance" in row

def test_run_doe_does_not_import_backtest_directly():
    import backtest_platform.research.workflows.doe as _doe_mod
    src = pathlib.Path(_doe_mod.__file__).read_text()
    assert "backtest_momentum" not in src
    assert "backtest_inst_flow" not in src
    assert "backtest_template" not in src
