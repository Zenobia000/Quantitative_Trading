"""Parameter sweep + heatmap data (8.G.5a).

Anti-cherry-pick discipline: the sweep returns the FULL grid (every config's
portfolio metrics), never a single 'best'. Tests use an injected synthetic
rising-trend loader (NOT cache-gated; the real-parquet path is the manual
integration step).
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

import backtest_platform.research.runners  # noqa: F401 — registers built-in strategies
from backtest_platform.research.sweep import expand_grid, run_sweep, to_heatmap
from backtest_platform.strategies.four_layer_resonance.config import StrategyConfig
from backtest_platform.strategies.protocol import get_strategy

#: Base four-layer config for the sweep — replaces the removed DEFAULT_CONFIG_V3 /
#: get_preset("v3") (ADR-028); the registry self-describes its config_model.
DEFAULT_CONFIG_V3 = get_strategy("four_layer").config_model()


def _synthetic_loader(sid: str) -> pd.DataFrame:
    """Rising-trend frame with positive institutional/chip flow → produces entries."""
    n = 260
    dates = pd.date_range("2019-05-01", periods=n, freq="D")
    close = np.linspace(50, 135, n) + np.sin(np.arange(n) / 4.0) * 1.5
    return pd.DataFrame({
        "trade_date": dates, "stock_id": sid,
        "open": close - 0.3, "high": close * 1.03, "low": close * 0.97,
        "close": close, "volume": 5000,
        "foreign_buy": 120, "trust_buy": 60, "dealer_buy": 10,
        "top_broker_buy": 90, "key_broker_buy": 50, "gov_broker_buy": 5, "geo_broker_buy": 5,
        "day_trade_volume": 500, "margin_offset_volume": 100,
    })


# --------------------------------------------------------------------------- #
# expand_grid                                                                  #
# --------------------------------------------------------------------------- #

def test_expand_grid_count_is_product_of_dimensions() -> None:
    grid = {
        "entry_min_layers": [3, 4],
        "entry_confirm_days": [1, 2, 3],
        "entry_cooldown_bars": [0, 5],
    }
    configs = expand_grid(DEFAULT_CONFIG_V3, grid)
    assert len(configs) == 2 * 3 * 2  # cartesian product == 12


def test_expand_grid_applies_each_combination_via_model_copy() -> None:
    grid = {"entry_min_layers": [3, 4], "entry_confirm_days": [1, 2]}
    configs = expand_grid(DEFAULT_CONFIG_V3, grid)
    # Each produced config is a distinct frozen StrategyConfig with the swept values.
    seen = {(c.entry_min_layers, c.entry_confirm_days) for c in configs}
    assert seen == {(3, 1), (3, 2), (4, 1), (4, 2)}
    assert all(isinstance(c, StrategyConfig) for c in configs)
    # base untouched (immutability) + non-swept params preserved from base.
    assert all(c.entry_cooldown_bars == DEFAULT_CONFIG_V3.entry_cooldown_bars for c in configs)


def test_expand_grid_single_value_is_passthrough() -> None:
    configs = expand_grid(DEFAULT_CONFIG_V3, {"entry_min_layers": [3]})
    assert len(configs) == 1
    assert configs[0].entry_min_layers == 3


def test_expand_grid_empty_grid_returns_base_once() -> None:
    configs = expand_grid(DEFAULT_CONFIG_V3, {})
    assert len(configs) == 1
    assert configs[0] == DEFAULT_CONFIG_V3


def test_expand_grid_rejects_unknown_param() -> None:
    with pytest.raises((ValueError, KeyError, Exception)):
        expand_grid(DEFAULT_CONFIG_V3, {"not_a_real_param": [1, 2]})


# --------------------------------------------------------------------------- #
# run_sweep                                                                    #
# --------------------------------------------------------------------------- #

def test_run_sweep_returns_one_row_per_config_with_metric_keys() -> None:
    grid = {"entry_min_layers": [3, 4], "entry_confirm_days": [1, 2]}
    configs = expand_grid(DEFAULT_CONFIG_V3, grid)
    results = run_sweep(
        stocks=["AAA", "BBB"],
        start=date(2019, 11, 1),
        end=date(2020, 1, 14),
        configs=configs,
        loader=_synthetic_loader,
    )
    assert len(results) == len(configs)  # full grid, no cherry-pick
    for row in results:
        # portfolio metrics from is_harness._metrics + bars.
        for k in ("cagr", "sharpe", "slippage_sharpe", "maxdd", "win",
                  "avg_hold", "struct1_pct", "churn_pct", "trades", "closed", "bars"):
            assert k in row, f"missing metric {k}"
        # swept param values attached to the row.
        assert "entry_min_layers" in row
        assert "entry_confirm_days" in row
        assert row["entry_min_layers"] in (3, 4)
        assert row["entry_confirm_days"] in (1, 2)


def test_run_sweep_attaches_correct_param_values_per_row() -> None:
    grid = {"entry_min_layers": [3, 4], "entry_confirm_days": [1, 2]}
    configs = expand_grid(DEFAULT_CONFIG_V3, grid)
    results = run_sweep(
        stocks=["AAA"],
        start=date(2019, 11, 1),
        end=date(2020, 1, 14),
        configs=configs,
        loader=_synthetic_loader,
    )
    combos = {(r["entry_min_layers"], r["entry_confirm_days"]) for r in results}
    assert combos == {(3, 1), (3, 2), (4, 1), (4, 2)}


def test_run_sweep_does_not_use_runconfig_preset() -> None:
    # A config that is NOT in PRESETS must still sweep — proves we eat
    # StrategyConfig directly, not RunConfig.preset / get_preset.
    custom = DEFAULT_CONFIG_V3.model_copy(update={"strong_buy_threshold": 4})
    results = run_sweep(
        stocks=["AAA"],
        start=date(2019, 11, 1),
        end=date(2020, 1, 14),
        configs=[custom],
        loader=_synthetic_loader,
    )
    assert len(results) == 1
    assert "sharpe" in results[0]


def test_run_sweep_empty_window_yields_zero_trades() -> None:
    results = run_sweep(
        stocks=["AAA"],
        start=date(2010, 1, 1),
        end=date(2010, 6, 1),
        configs=[DEFAULT_CONFIG_V3],
        loader=_synthetic_loader,
    )
    assert len(results) == 1
    assert results[0]["trades"] == 0


# --------------------------------------------------------------------------- #
# to_heatmap                                                                   #
# --------------------------------------------------------------------------- #

def test_to_heatmap_shape_and_axes() -> None:
    results = [
        {"entry_min_layers": 3, "entry_confirm_days": 1, "sharpe": 0.1},
        {"entry_min_layers": 3, "entry_confirm_days": 2, "sharpe": 0.2},
        {"entry_min_layers": 4, "entry_confirm_days": 1, "sharpe": 0.3},
        {"entry_min_layers": 4, "entry_confirm_days": 2, "sharpe": 0.4},
    ]
    x_vals, y_vals, grid = to_heatmap(
        results, x_param="entry_confirm_days", y_param="entry_min_layers", metric="sharpe"
    )
    assert x_vals == [1, 2]
    assert y_vals == [3, 4]
    assert grid.shape == (2, 2)  # (len(y_vals), len(x_vals))
    # grid[y_index][x_index]
    assert grid[0][0] == pytest.approx(0.1)  # y=3, x=1
    assert grid[0][1] == pytest.approx(0.2)  # y=3, x=2
    assert grid[1][0] == pytest.approx(0.3)  # y=4, x=1
    assert grid[1][1] == pytest.approx(0.4)  # y=4, x=2


def test_to_heatmap_missing_cell_is_nan() -> None:
    results = [
        {"x": 1, "y": 10, "m": 0.5},
        {"x": 2, "y": 20, "m": 0.7},
    ]
    x_vals, y_vals, grid = to_heatmap(results, x_param="x", y_param="y", metric="m")
    assert x_vals == [1, 2]
    assert y_vals == [10, 20]
    assert grid.shape == (2, 2)
    assert grid[0][0] == pytest.approx(0.5)
    assert grid[1][1] == pytest.approx(0.7)
    assert np.isnan(grid[0][1])  # (y=10, x=2) absent
    assert np.isnan(grid[1][0])  # (y=20, x=1) absent


def test_to_heatmap_axes_sorted() -> None:
    results = [
        {"x": 3, "y": 2, "m": 1.0},
        {"x": 1, "y": 2, "m": 2.0},
        {"x": 2, "y": 1, "m": 3.0},
    ]
    x_vals, y_vals, grid = to_heatmap(results, x_param="x", y_param="y", metric="m")
    assert x_vals == [1, 2, 3]  # sorted ascending
    assert y_vals == [1, 2]
    assert grid.shape == (2, 3)


def test_to_heatmap_returns_numpy_array() -> None:
    results = [{"x": 1, "y": 1, "m": 0.0}]
    _, _, grid = to_heatmap(results, x_param="x", y_param="y", metric="m")
    assert isinstance(grid, np.ndarray)
