"""End-to-end re-validation: real momentum strategy → full validation stack.

Proves "跑通" — the platform runs a real strategy's returns through the complete
validation pipeline (metrics → §4.3.1 health → bootstrap/MC → DSR) end-to-end,
on synthetic prices (no parquet / no network). The live-data run uses the same
two calls (backtest_momentum → full_validation_report) over an ingested universe.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from backtest_platform.strategies.momentum.strategy import MomentumConfig, backtest_momentum
from backtest_platform.validation.full_report import full_validation_report


def _trending_panel(n_days: int = 1300, seed: int = 7) -> pd.DataFrame:
    """12 stocks over ~5y: persistent trenders (up/down) + noise, so 12-1 momentum
    has a real cross-sectional signal to capture."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2016-01-01", periods=n_days)
    drifts = [0.0010, 0.0009, 0.0008, 0.0007, 0.0006, 0.0001,
              -0.0001, -0.0004, -0.0006, -0.0008, -0.0010, -0.0012]
    cols = {}
    for i, mu in enumerate(drifts):
        shocks = rng.normal(mu, 0.012, n_days)
        cols[f"S{i:02d}"] = 100.0 * np.exp(np.cumsum(shocks))
    return pd.DataFrame(cols, index=dates)


def test_momentum_runs_through_full_validation_pipeline():
    prices = _trending_panel()
    cfg = MomentumConfig(rebalance="monthly", vol_target_annual=0.15)  # crash-control on
    result = backtest_momentum(prices, cfg, start="2017-01-01", end="2020-12-31")
    assert len(result.daily_returns) > 200  # the strategy actually traded
    assert result.n_rebalances > 10

    rep = full_validation_report(result.daily_returns, n_trials=1, n_iter=200)
    # the whole stack produced a coherent report end-to-end
    assert {"metrics", "health", "robustness", "deployable", "bars"} <= set(rep)
    assert len(rep["health"]["rows"]) == 13
    assert "sharpe" in rep["metrics"]
    assert 0.0 <= rep["robustness"]["deflated_sharpe"] <= 1.0
    assert 0.0 <= rep["robustness"]["mc_edge_pvalue"] <= 1.0
    # a clean cross-sectional trend panel → momentum captures a positive Sharpe
    assert rep["metrics"]["sharpe"] > 0.0


def test_vol_target_reduces_realized_vol():
    prices = _trending_panel()
    base = backtest_momentum(prices, MomentumConfig(), start="2017-01-01", end="2020-12-31")
    vt = backtest_momentum(
        prices, MomentumConfig(vol_target_annual=0.10, max_leverage=1.0),
        start="2017-01-01", end="2020-12-31",
    )
    # de-risk-only vol targeting must not increase realized volatility
    assert vt.daily_returns.std() <= base.daily_returns.std() + 1e-9


def test_trials_penalty_flows_through_to_deployable():
    prices = _trending_panel()
    result = backtest_momentum(prices, MomentumConfig(), start="2017-01-01", end="2020-12-31")
    # honest DSR with many searched configs deflates vs a single-trial claim
    one = full_validation_report(result.daily_returns, n_trials=1, n_iter=150)
    many = full_validation_report(result.daily_returns, n_trials=1000, n_iter=150)
    assert many["robustness"]["deflated_sharpe"] <= one["robustness"]["deflated_sharpe"]
