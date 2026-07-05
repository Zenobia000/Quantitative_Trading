"""workflow.doe — DOE grid scan via strategy dispatch (synthetic loader)."""
from __future__ import annotations

import ast
import pathlib
from datetime import date

from backtest_platform.research import runners as _runners  # noqa: F401
from backtest_platform.research.workflows.config import DOEConfig
from backtest_platform.research.workflows.doe import DOEResult, run_doe
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
    assert result.n_configs == 2  # 2 lookback x 1 rebalance


def test_run_doe_each_run_has_required_metrics():
    result = run_doe(_doe_cfg(), loader=synthetic_loader(n_bars=600))
    required = {"cagr", "sharpe", "slippage_sharpe", "maxdd", "trades", "bars"}
    for row in result.runs:
        assert required <= row.keys(), f"missing keys in {row.keys()}"


def test_run_doe_each_run_has_grid_params():
    result = run_doe(_doe_cfg(), loader=synthetic_loader(n_bars=600))
    for row in result.runs:
        assert "lookback_days" in row
        assert "rebalance" in row


def test_run_doe_does_not_import_backtest_directly():
    """Dispatch invariant: doe.py must not directly import backtest functions."""
    src = pathlib.Path(
        "src/backtest_platform/research/workflows/doe.py"
    ).read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [n.name for n in getattr(node, "names", [])]
            module = getattr(node, "module", "") or ""
            for name in names:
                assert "backtest_momentum" not in name and "backtest_inst_flow" not in name
            assert "backtest_momentum" not in module and "backtest_inst_flow" not in module
