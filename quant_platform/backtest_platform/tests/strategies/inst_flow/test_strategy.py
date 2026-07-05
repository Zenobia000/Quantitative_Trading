"""inst_flow.strategy — institutional-flow factor over synthetic panels."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest_platform.strategies.inst_flow.strategy import (
    InstFlowConfig,
    backtest_inst_flow,
    flow_intensity,
)


def _panels(n: int = 500):
    """5 stocks. UP1/UP2 rise AND get heavy foreign net-buy; DN1/DN2 fall + are
    sold; FLAT flat. A flow factor that works selects the bought (rising) names."""
    dates = pd.bdate_range("2018-01-01", periods=n)
    k = np.arange(n)
    close = pd.DataFrame({
        "UP1": 100 * 1.0015 ** k, "UP2": 100 * 1.0012 ** k,
        "DN1": 100 * 0.9990 ** k, "DN2": 100 * 0.9988 ** k,
        "FLAT": 100.0 + 0 * k,
    }, index=dates)
    volume = pd.DataFrame(1000, index=dates, columns=close.columns)
    flow = pd.DataFrame({
        "UP1": 300, "UP2": 200, "DN1": -300, "DN2": -200, "FLAT": 0,
    }, index=dates)
    return close, flow, volume


# --- config --------------------------------------------------------------

def test_config_frozen_and_sources():
    cfg = InstFlowConfig()
    with pytest.raises(Exception):
        cfg.lookback_days = 10  # frozen
    assert cfg.flow_cols == ("foreign_buy",)
    assert InstFlowConfig(flow_source="foreign_trust").flow_cols == ("foreign_buy", "trust_buy")
    assert InstFlowConfig(flow_source="all").flow_cols == ("foreign_buy", "trust_buy", "dealer_buy")


def test_config_rejects_unknown():
    with pytest.raises(Exception):
        InstFlowConfig(bogus=1)


# --- signal --------------------------------------------------------------

def test_flow_intensity_is_netbuy_over_volume():
    close, flow, volume = _panels(60)
    inten = flow_intensity(flow, volume, lookback=20)
    # UP1: 300/1000 = 0.30 per day → trailing sum ratio 0.30; DN1: -0.30
    assert inten["UP1"].dropna().iloc[-1] == pytest.approx(0.30, abs=1e-9)
    assert inten["DN1"].dropna().iloc[-1] == pytest.approx(-0.30, abs=1e-9)
    assert inten["UP1"].iloc[:19].isna().all()  # warmup before lookback fills


# --- backtest ------------------------------------------------------------

def test_factor_selects_bought_names_positive_return():
    close, flow, volume = _panels()
    res = backtest_inst_flow(
        close, flow, volume, InstFlowConfig(top_fraction=0.4, lookback_days=20),
        "2019-01-01", "2019-12-31",
    )
    assert len(res.daily_returns) > 100
    # following net buying into rising names → positive cumulative return
    assert (1 + res.daily_returns).prod() > 1.0


def test_long_only_positive_holds_cash_when_all_sold():
    close, flow, volume = _panels(300)
    # flip every flow negative → no name has positive net buying → cash (flat)
    flow = -flow.abs() - 1
    res = backtest_inst_flow(
        close, flow, volume, InstFlowConfig(long_only_positive=True, lookback_days=20),
        "2018-07-01", "2018-12-31",
    )
    assert (res.daily_returns == 0).all()  # all cash, no losses


def test_vol_target_reduces_vol():
    close, flow, volume = _panels()
    base = backtest_inst_flow(close, flow, volume, InstFlowConfig(), "2019-01-01", "2019-12-31")
    vt = backtest_inst_flow(
        close, flow, volume, InstFlowConfig(vol_target_annual=0.08, max_leverage=1.0),
        "2019-01-01", "2019-12-31",
    )
    assert vt.daily_returns.std() <= base.daily_returns.std() + 1e-9


def test_empty_window_returns_empty():
    close, flow, volume = _panels()
    res = backtest_inst_flow(close, flow, volume, InstFlowConfig(), "2010-01-01", "2010-06-01")
    assert res.daily_returns.empty
