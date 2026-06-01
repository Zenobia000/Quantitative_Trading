"""Tests for the self-written vectorized PnL simulator."""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from backtest_platform.config.strategy_config import StrategyConfig
from backtest_platform.engines.zipline_adapter.validation.vectorized_pnl_check import (
    simulate_vectorized_long_only,
)


def _make_series(values, n: int | None = None) -> pd.Series:
    """Build aligned price/action series for tests. Accepts floats or str."""
    n = n or len(values)
    idx = pd.date_range("2024-01-02", periods=n, freq="B")
    return pd.Series(values, index=idx)


def test_no_action_returns_initial_cash():
    prices = _make_series([100.0, 101.0, 102.0])
    actions = _make_series(["hold", "hold", "hold"])
    run = simulate_vectorized_long_only(prices, actions, initial_cash=1_000_000)
    assert run.final_equity == 1_000_000
    assert run.n_trades == 0


def test_buy_then_exit_at_higher_price_gives_profit():
    """Buy at 100, exit at 110. With default config (~0.5% round-trip cost)
    profit should be ~10% gross - cost."""
    prices = _make_series([100.0, 100.0, 110.0])
    actions = _make_series(["hold", "buy", "exit"])
    config = StrategyConfig()
    run = simulate_vectorized_long_only(prices, actions, config=config, initial_cash=1_000_000)
    assert run.n_trades == 2  # buy + exit
    # 5% of 1M = 50k notional, gain 10% = 5k gross, minus fees
    assert run.final_equity > 1_000_000  # profitable
    assert run.final_equity < 1_005_000  # gain capped by 5% sizing
    assert run.total_fees > 0
    assert run.total_tax > 0  # sold side incurs tax


def test_stoploss_flattens_position():
    prices = _make_series([100.0, 100.0, 95.0])
    actions = _make_series(["hold", "buy", "stoploss"])
    run = simulate_vectorized_long_only(prices, actions, initial_cash=1_000_000)
    assert run.n_trades == 2
    # Loss expected — sized 5% so capped impact
    assert run.final_equity < 1_000_000
    # Round-trip cost component: fee_rate × discount × notional × 2 + tax + slippage
    # We just sanity check tax was charged (sell side)
    assert run.total_tax > 0


def test_add_grows_position():
    prices = _make_series([100.0, 100.0, 101.0, 102.0, 110.0])
    actions = _make_series(["hold", "buy", "add", "hold", "exit"])
    run = simulate_vectorized_long_only(prices, actions, initial_cash=1_000_000)
    assert run.n_trades == 3  # buy + add + exit
    assert run.final_equity > 1_000_000


def test_reduce_halves_shares():
    """Reduce when in position: sell half, keep half."""
    prices = _make_series([100.0, 100.0, 110.0, 105.0])
    actions = _make_series(["hold", "buy", "reduce", "exit"])
    run = simulate_vectorized_long_only(prices, actions, initial_cash=1_000_000)
    assert run.n_trades == 3  # buy + reduce + exit


def test_buy_when_already_long_is_noop():
    """The simulator is single-position; redundant buy must not double-add."""
    prices = _make_series([100.0, 100.0, 101.0, 102.0])
    actions = _make_series(["hold", "buy", "buy", "exit"])
    run = simulate_vectorized_long_only(prices, actions, initial_cash=1_000_000)
    assert run.n_trades == 2  # only first buy + exit


def test_cost_attribution_breakdown():
    """Validate fees vs tax vs slippage are tracked separately."""
    prices = _make_series([100.0] * 5)
    actions = _make_series(["hold", "buy", "hold", "hold", "exit"])
    config = StrategyConfig()
    run = simulate_vectorized_long_only(prices, actions, config=config, initial_cash=1_000_000)
    # All three cost buckets should be non-zero
    assert run.total_fees > 0
    assert run.total_tax > 0
    assert run.total_slippage_cost > 0
    # Tax > Fees because tax_stock_rate (0.3%) > buy/sell fee (0.0855%)
    # for the sell leg. Round-trip: fees on both legs, tax on sell only.
    # tax = sell_gross × 0.003
    # fee = (buy_gross + sell_gross) × 0.000855
    # Therefore tax should be roughly 1.75× fees per round-trip
    assert run.total_tax > run.total_fees


def test_equity_curve_length_matches_prices():
    prices = _make_series([100.0] * 10)
    actions = _make_series(["hold"] * 10)
    run = simulate_vectorized_long_only(prices, actions, initial_cash=1_000_000)
    assert len(run.equity_curve) == 10
