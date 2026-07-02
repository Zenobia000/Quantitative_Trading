"""Transaction costs must actually land in panel-strategy returns (審查缺陷 #18 深層).

Bug being pinned: segments overlap on the rebalance day and the lump cost is
charged on the NEW segment's first row — which ``groupby(level=0).first()``
then discards in favour of the old segment's cost-free row. Net effect: lump
costs are systematically swallowed (and the K3 slippage stress becomes a
silent no-op: ``slippage_sharpe == sharpe`` bit-for-bit).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest_platform.strategies.inst_flow.strategy import (
    InstFlowConfig,
    backtest_inst_flow,
)
from backtest_platform.strategies.momentum.strategy import (
    MomentumConfig,
    backtest_momentum,
)
from backtest_platform.strategies.reversal.strategy import (
    ReversalConfig,
    backtest_reversal,
)

_DATES = pd.bdate_range("2020-01-01", "2021-06-30")


def _alternating_flow_panels() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Two symbols whose net-buy leadership flips every ~quarter → forced turnover."""
    rng = np.arange(len(_DATES))
    close = pd.DataFrame(
        {"A": 100.0 * (1.001 ** rng), "B": 100.0 * (1.0012 ** rng)}, index=_DATES
    )
    quarter = (rng // 63) % 2  # flips 0/1 roughly per quarter
    flow = pd.DataFrame(
        {"A": np.where(quarter == 0, 1e9, -1e9), "B": np.where(quarter == 1, 1e9, -1e9)},
        index=_DATES,
    )
    volume = pd.DataFrame(1e7, index=_DATES, columns=["A", "B"])
    return close, flow, volume


def _alternating_momentum_prices() -> pd.DataFrame:
    """Two symbols whose trailing momentum leadership flips ~monthly."""
    rng = np.arange(len(_DATES))
    phase = (rng // 42) % 2
    ra = np.where(phase == 0, 0.004, -0.002)
    rb = np.where(phase == 1, 0.004, -0.002)
    return pd.DataFrame(
        {"A": 100.0 * np.cumprod(1 + ra), "B": 100.0 * np.cumprod(1 + rb)}, index=_DATES
    )


def _alternating_reversal_prices() -> pd.DataFrame:
    """Two symbols whose weekly loser/winner leadership flips every week.

    Anti-phase weekly oscillation → the biggest loser flips every rebalance, forcing
    ~100% turnover each week (the reversal turnover killer that must be fully charged).
    """
    rng = np.arange(len(_DATES))
    week = rng // 5
    ra = np.where(week % 2 == 0, 0.010, -0.008)
    rb = np.where(week % 2 == 1, 0.010, -0.008)
    return pd.DataFrame(
        {"A": 100.0 * np.cumprod(1 + ra), "B": 100.0 * np.cumprod(1 + rb)}, index=_DATES
    )


def test_inst_flow_lump_cost_reduces_return_by_full_turnover() -> None:
    close, flow, volume = _alternating_flow_panels()
    base = InstFlowConfig(
        rebalance="quarterly", lookback_days=20, flow_source="foreign",
        top_fraction=0.5, cost_round_rate=0.0, signal_lag_days=1,
    )
    costly = base.model_copy(update={"cost_round_rate": 0.01})
    r0 = backtest_inst_flow(close, flow, volume, base, _DATES[30], _DATES[-1])
    r1 = backtest_inst_flow(close, flow, volume, costly, _DATES[30], _DATES[-1])

    turnover_total = r0.avg_turnover * r0.n_rebalances
    assert turnover_total > 1.0, "fixture must force real turnover across rebalances"
    expected_drag = 0.01 * turnover_total
    actual_drag = float(r0.daily_returns.sum() - r1.daily_returns.sum())
    # Every rebalance's lump cost must land, not just the first entry's.
    assert actual_drag == pytest.approx(expected_drag, rel=0.35)
    assert actual_drag > 0.01  # strictly more than a single entry's cost


def test_momentum_lump_cost_reduces_return_by_full_turnover() -> None:
    prices = _alternating_momentum_prices()
    base = MomentumConfig(
        rebalance="monthly", lookback_days=40, skip_days=1,
        top_fraction=0.5, cost_round_rate=0.0, abs_momentum=False,
    )
    costly = base.model_copy(update={"cost_round_rate": 0.01})
    r0 = backtest_momentum(prices, base, _DATES[60], _DATES[-1])
    r1 = backtest_momentum(prices, costly, _DATES[60], _DATES[-1])

    turnover_total = r0.avg_turnover * r0.n_rebalances
    assert turnover_total > 1.0, "fixture must force real turnover across rebalances"
    expected_drag = 0.01 * turnover_total
    actual_drag = float(r0.daily_returns.sum() - r1.daily_returns.sum())
    assert actual_drag == pytest.approx(expected_drag, rel=0.35)
    assert actual_drag > 0.01


def test_reversal_lump_cost_reduces_return_by_full_turnover() -> None:
    prices = _alternating_reversal_prices()
    base = ReversalConfig(
        rebalance="weekly", lookback_days=5, skip_days=1,
        top_fraction=0.5, cost_round_rate=0.0,
    )
    costly = base.model_copy(update={"cost_round_rate": 0.01})
    r0 = backtest_reversal(prices, base, _DATES[10], _DATES[-1])
    r1 = backtest_reversal(prices, costly, _DATES[10], _DATES[-1])

    turnover_total = r0.avg_turnover * r0.n_rebalances
    assert turnover_total > 1.0, "fixture must force real turnover across rebalances"
    expected_drag = 0.01 * turnover_total
    actual_drag = float(r0.daily_returns.sum() - r1.daily_returns.sum())
    # Every weekly rebalance's lump cost must land, not just the first entry's.
    assert actual_drag == pytest.approx(expected_drag, rel=0.35)
    assert actual_drag > 0.01  # strictly more than a single entry's cost


def test_reversal_no_duplicate_dates_and_cost_survives_stitch() -> None:
    prices = _alternating_reversal_prices()
    cfg = ReversalConfig(
        rebalance="weekly", lookback_days=5, skip_days=1,
        top_fraction=0.5, cost_round_rate=0.02,
    )
    res = backtest_reversal(prices, cfg, _DATES[10], _DATES[-1])
    assert not res.daily_returns.index.duplicated().any()
    stressed = backtest_reversal(prices, cfg.with_extra_slippage(0.01), _DATES[10], _DATES[-1])
    # K3 stress must not be a silent no-op when there is weekly turnover.
    assert float(stressed.daily_returns.sum()) < float(res.daily_returns.sum())


def test_inst_flow_no_duplicate_dates_and_cost_survives_stitch() -> None:
    close, flow, volume = _alternating_flow_panels()
    cfg = InstFlowConfig(
        rebalance="quarterly", lookback_days=20, flow_source="foreign",
        top_fraction=0.5, cost_round_rate=0.02, signal_lag_days=1,
    )
    res = backtest_inst_flow(close, flow, volume, cfg, _DATES[30], _DATES[-1])
    assert not res.daily_returns.index.duplicated().any()
    stressed = backtest_inst_flow(
        close, flow, volume, cfg.with_extra_slippage(0.01), _DATES[30], _DATES[-1]
    )
    # K3 stress must not be a silent no-op when there is turnover.
    assert float(stressed.daily_returns.sum()) < float(res.daily_returns.sum())
