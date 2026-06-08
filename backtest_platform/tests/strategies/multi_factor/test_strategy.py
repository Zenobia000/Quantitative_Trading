"""multi_factor.strategy — composite over synthetic panels."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest_platform.strategies.multi_factor.strategy import (
    MultiFactorConfig,
    backtest_multi_factor,
    composite_scores,
)


def _panels(n: int = 500):
    """5 stocks: GOOD = up-trend + bought + low-vol; BAD = down + sold + high-vol."""
    dates = pd.bdate_range("2018-01-01", periods=n)
    k = np.arange(n)
    rng = np.random.default_rng(0)
    close = pd.DataFrame({
        "G1": 100 * 1.0015 ** k, "G2": 100 * 1.0012 ** k,
        "B1": 100 * 0.9990 ** k * (1 + 0.03 * rng.standard_normal(n)),  # high vol
        "B2": 100 * 0.9988 ** k * (1 + 0.03 * rng.standard_normal(n)),
        "M": 100.0 + 0 * k,
    }, index=dates).clip(lower=1.0)
    volume = pd.DataFrame(1000, index=dates, columns=close.columns)
    flow = pd.DataFrame({"G1": 300, "G2": 200, "B1": -300, "B2": -200, "M": 0}, index=dates)
    return close, flow, volume


def test_config_frozen_and_factor_validation():
    cfg = MultiFactorConfig()
    with pytest.raises(Exception):
        cfg.top_fraction = 0.5  # frozen
    assert cfg.factors == ("momentum", "inst_flow", "low_vol")
    with pytest.raises(Exception):
        MultiFactorConfig(factors=("bogus",))
    assert MultiFactorConfig(factors=("momentum",)).factors == ("momentum",)


def test_composite_is_mean_of_factor_zscores():
    close, flow, volume = _panels(300)
    sc = composite_scores(close, flow, volume, MultiFactorConfig(flow_lookback=20, vol_lookback_signal=20))
    last = sc.dropna(how="all").iloc[-1]
    # GOOD names (up + bought + low-vol) should out-rank BAD names
    assert last["G1"] > last["B1"]
    assert last["G2"] > last["B2"]


def test_backtest_selects_good_names_positive():
    close, flow, volume = _panels()
    res = backtest_multi_factor(
        close, flow, volume,
        MultiFactorConfig(top_fraction=0.4, flow_lookback=20, vol_lookback_signal=20, mom_lookback=120),
        "2018-09-01", "2019-12-31",
    )
    assert len(res.daily_returns) > 100
    assert (1 + res.daily_returns).prod() > 1.0


def test_single_factor_subset_runs():
    close, flow, volume = _panels()
    res = backtest_multi_factor(
        close, flow, volume,
        MultiFactorConfig(factors=("momentum",), mom_lookback=120),
        "2018-09-01", "2019-12-31",
    )
    assert len(res.daily_returns) > 50


def test_empty_window_returns_empty():
    close, flow, volume = _panels()
    res = backtest_multi_factor(close, flow, volume, MultiFactorConfig(), "2010-01-01", "2010-06-01")
    assert res.daily_returns.empty


# --- long-short overlay --------------------------------------------------

def test_long_short_off_is_long_only():
    close, flow, volume = _panels()
    base = backtest_multi_factor(close, flow, volume, MultiFactorConfig(mom_lookback=120), "2018-09-01", "2019-12-31")
    off = backtest_multi_factor(close, flow, volume, MultiFactorConfig(mom_lookback=120, long_short=False), "2018-09-01", "2019-12-31")
    assert base.daily_returns.equals(off.daily_returns)


def test_long_short_captures_both_sides():
    close, flow, volume = _panels()
    cfg = MultiFactorConfig(mom_lookback=120, flow_lookback=20, vol_lookback_signal=20,
                            long_short=True, top_fraction=0.4, short_fraction=0.4, borrow_rate_annual=0.0)
    ls = backtest_multi_factor(close, flow, volume, cfg, "2018-09-01", "2019-12-31")
    assert len(ls.daily_returns) > 100
    # long winners − short losers → positive spread (both sides contribute)
    assert (1 + ls.daily_returns).prod() > 1.0


def test_long_short_borrow_cost_drags():
    close, flow, volume = _panels()
    common = dict(mom_lookback=120, flow_lookback=20, vol_lookback_signal=20,
                  long_short=True, top_fraction=0.4, short_fraction=0.4)
    free = backtest_multi_factor(close, flow, volume, MultiFactorConfig(**common, borrow_rate_annual=0.0), "2018-09-01", "2019-12-31")
    borrow = backtest_multi_factor(close, flow, volume, MultiFactorConfig(**common, borrow_rate_annual=0.05), "2018-09-01", "2019-12-31")
    assert borrow.daily_returns.mean() < free.daily_returns.mean()  # borrow cost reduces return
