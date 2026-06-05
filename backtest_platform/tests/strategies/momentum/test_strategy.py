"""momentum.strategy — config + backtest over synthetic prices with known winners."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest_platform.strategies.momentum.strategy import (
    MomentumConfig,
    _vol_target,
    backtest_momentum,
)


def _panel() -> pd.DataFrame:
    """5 stocks, 500 business days: UP1/UP2 trend up, DN1/DN2 down, FLAT flat.
    Momentum should select the up-trenders."""
    dates = pd.bdate_range("2018-01-01", periods=500)
    n = np.arange(500)
    return pd.DataFrame(
        {
            "UP1": 100 * (1.0020) ** n,
            "UP2": 100 * (1.0018) ** n,
            "DN1": 100 * (0.9990) ** n,
            "DN2": 100 * (0.9988) ** n,
            "FLAT": 100.0 + 0 * n,
        },
        index=dates,
    )


# --- config --------------------------------------------------------------

def test_config_frozen_and_extra_slippage():
    cfg = MomentumConfig()
    with pytest.raises(Exception):
        cfg.lookback_days = 100  # frozen
    slipped = cfg.with_extra_slippage(0.003)
    assert slipped.cost_round_rate == pytest.approx(cfg.cost_round_rate + 0.006)
    assert cfg.cost_round_rate != slipped.cost_round_rate  # original unchanged


def test_config_rejects_unknown_field():
    with pytest.raises(Exception):
        MomentumConfig(bogus=1)


# --- backtest ------------------------------------------------------------

def test_momentum_selects_winners_and_is_positive():
    cfg = MomentumConfig(top_fraction=0.4)  # k = int(5*0.4) = 2 → the two up-trenders
    res = backtest_momentum(_panel(), cfg, "2019-06-01", "2019-12-31")
    assert res.n_rebalances > 0
    assert res.avg_holdings == pytest.approx(2.0)
    # holding the up-trenders over the window → positive cumulative return
    assert (1 + res.daily_returns).prod() - 1 > 0


def test_higher_cost_lowers_return():
    panel = _panel()
    lo = backtest_momentum(panel, MomentumConfig(top_fraction=0.4), "2019-06-01", "2019-12-31")
    hi = backtest_momentum(
        panel, MomentumConfig(top_fraction=0.4, cost_round_rate=0.05), "2019-06-01", "2019-12-31"
    )
    assert (1 + hi.daily_returns).prod() < (1 + lo.daily_returns).prod()


def test_empty_window_returns_empty():
    res = backtest_momentum(_panel(), MomentumConfig(), "2010-01-01", "2010-06-30")
    assert res.daily_returns.empty
    assert res.n_rebalances == 0


def test_vol_target_de_risks_high_vol_without_levering():
    rng = np.random.default_rng(0)
    r = pd.Series(rng.normal(0.0, 0.03, 300))  # ~3%/day ≈ 47% annual, well above target
    scaled = _vol_target(r, target_annual=0.15, lookback=20, max_lev=1.0)
    # after warmup, realized vol is cut toward target
    assert scaled.iloc[40:].std() < r.iloc[40:].std()
    # max_lev=1.0 → only de-risk, never amplify a daily move
    assert (scaled.abs() <= r.abs() + 1e-12).all()


def test_vol_target_off_by_default():
    cfg = MomentumConfig()
    assert cfg.vol_target_annual is None  # vanilla unless explicitly enabled


def test_cost_mode_spread_matches_lump_total_drag():
    panel = _panel()
    _wealth = lambda r: (1 + r.daily_returns).prod()
    free = _wealth(backtest_momentum(panel, MomentumConfig(top_fraction=0.4, cost_round_rate=0.0), "2019-06-01", "2019-12-31"))
    lump = _wealth(backtest_momentum(panel, MomentumConfig(top_fraction=0.4, cost_round_rate=0.02, cost_mode="lump"), "2019-06-01", "2019-12-31"))
    spread = _wealth(backtest_momentum(panel, MomentumConfig(top_fraction=0.4, cost_round_rate=0.02, cost_mode="spread"), "2019-06-01", "2019-12-31"))
    assert lump < free and spread < free          # both cost the strategy
    assert abs(lump - spread) < 0.02 * free       # same total cost → ~same final wealth


def test_cost_mode_rejects_bad_value():
    with pytest.raises(Exception):
        MomentumConfig(cost_mode="bogus")


def test_quarterly_rebalances_less_than_monthly():
    panel = _panel()
    m = backtest_momentum(panel, MomentumConfig(top_fraction=0.4, rebalance="monthly"), "2019-01-01", "2019-12-31")
    q = backtest_momentum(panel, MomentumConfig(top_fraction=0.4, rebalance="quarterly"), "2019-01-01", "2019-12-31")
    assert q.n_rebalances < m.n_rebalances  # fewer rebalances = less turnover/cost
    assert q.n_rebalances <= 5               # ~4 quarters in a year


def test_rebalance_rejects_bad_value():
    with pytest.raises(Exception):
        MomentumConfig(rebalance="weekly")


def test_winsorizes_data_error_spike():
    panel = _panel()
    # inject a 5x price spike (un-adjusted-split style) then revert
    panel.iloc[300, panel.columns.get_loc("UP1")] *= 5
    res = backtest_momentum(panel, MomentumConfig(top_fraction=0.4), "2019-06-01", "2019-12-31")
    # no inf / absurd return survived winsorization
    assert np.isfinite(res.daily_returns).all()
    assert res.daily_returns.abs().max() <= 0.5
