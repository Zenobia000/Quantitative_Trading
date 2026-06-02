"""Unit tests for `algorithms/four_layer_resonance.py` zipline algorithm.

Heavy zipline integration (run_algorithm + bundle ingest) lives in
validation/ harness. Here we mock zipline.api side-effects (order_target_percent,
record, schedule_function, symbol) and exercise the algorithm's pure logic:

- initialize(): reads UNIVERSE_FINMIND env, preloads frames, schedules eval
- evaluate_and_trade(): walks symbols, calls evaluate_window_with_state,
  dispatches to _execute_action
- _portfolio_state(): reads zipline portfolio
- _build_evaluate_bar(): converts prepared row → EvaluateBar dataclass
- evaluate_window_with_state(): score + signal-prep + evaluate the bar
- _execute_action(): action-name → zipline order

All zipline.api calls are mocked so this runs without zipline runtime.
"""
from __future__ import annotations

import sys
import types
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from backtest_platform.config.strategy_config import StrategyConfig
from backtest_platform.engines.zipline_adapter.algorithms import four_layer_resonance as fr


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _make_merged_frame(n_bars: int = 100) -> pd.DataFrame:
    """Build a merged frame compatible with preload_merged_frames output.

    DatetimeIndex on trade_date + all REQUIRED_COLUMNS for compute_scores.
    """
    rng = np.random.default_rng(42)
    start = pd.Timestamp("2024-01-02")
    idx = pd.bdate_range(start=start, periods=n_bars)

    base = np.linspace(100, 130, n_bars)
    noise = rng.normal(0, 0.5, n_bars)
    close = base + noise
    open_ = close - rng.normal(0.1, 0.3, n_bars)
    high = np.maximum(close, open_) + rng.uniform(0.1, 0.6, n_bars)
    low = np.minimum(close, open_) - rng.uniform(0.1, 0.6, n_bars)

    df = pd.DataFrame(
        {
            "stock_id": ["TEST"] * n_bars,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": rng.integers(5000, 15000, n_bars),
            "foreign_buy": rng.integers(100, 1000, n_bars),
            "trust_buy": rng.integers(50, 500, n_bars),
            "dealer_buy": rng.integers(-100, 200, n_bars),
            "top_broker_buy": rng.integers(100, 800, n_bars),
            "key_broker_buy": rng.integers(50, 400, n_bars),
            "gov_broker_buy": rng.integers(0, 200, n_bars),
            "geo_broker_buy": rng.integers(0, 100, n_bars),
            "day_trade_volume": rng.integers(100, 1500, n_bars),
            "margin_offset_volume": rng.integers(0, 300, n_bars),
        },
        index=idx,
    )
    df.index.name = "trade_date"
    return df


class _FakePosition:
    def __init__(self, amount: int = 0, cost_basis: float = 0.0, last_sale_price: float = 0.0):
        self.amount = amount
        self.cost_basis = cost_basis
        self.last_sale_price = last_sale_price


class _FakePortfolio:
    def __init__(self, positions: dict | None = None, portfolio_value: float = 1_000_000):
        self.positions = positions or {}
        self.portfolio_value = portfolio_value


class _FakeContext:
    """Mimics zipline.TradingAlgorithm context object passed to handlers."""

    def __init__(
        self,
        config: StrategyConfig | None = None,
        merged_frames: dict | None = None,
        portfolio: _FakePortfolio | None = None,
        symbol_strs: list | None = None,
    ):
        self.config = config or StrategyConfig()
        self.merged_frames = merged_frames or {}
        self.portfolio = portfolio or _FakePortfolio()
        self.symbol_strs = symbol_strs or []
        self.assets = [object() for _ in self.symbol_strs]  # opaque asset stand-ins
        self._dt = pd.Timestamp("2024-06-01")

    def get_datetime(self):
        return self._dt


# --------------------------------------------------------------------------- #
# _portfolio_state
# --------------------------------------------------------------------------- #


def test_portfolio_state_no_position_returns_zero():
    ctx = _FakeContext()
    asset = object()
    in_pos, cost = fr._portfolio_state(ctx, asset)
    assert in_pos == 0
    assert cost == 0.0


def test_portfolio_state_amount_zero_returns_zero():
    asset = object()
    portfolio = _FakePortfolio(positions={asset: _FakePosition(amount=0, cost_basis=120.0)})
    ctx = _FakeContext(portfolio=portfolio)
    in_pos, cost = fr._portfolio_state(ctx, asset)
    assert in_pos == 0
    assert cost == 0.0


def test_portfolio_state_open_position_returns_cost_basis():
    asset = object()
    portfolio = _FakePortfolio(
        positions={asset: _FakePosition(amount=1000, cost_basis=125.5)}
    )
    ctx = _FakeContext(portfolio=portfolio)
    in_pos, cost = fr._portfolio_state(ctx, asset)
    assert in_pos == 1
    assert cost == pytest.approx(125.5)


# --------------------------------------------------------------------------- #
# _current_weight
# --------------------------------------------------------------------------- #


def test_current_weight_no_position_returns_zero():
    ctx = _FakeContext()
    assert fr._current_weight(ctx, object()) == 0.0


def test_current_weight_zero_amount_returns_zero():
    asset = object()
    portfolio = _FakePortfolio(positions={asset: _FakePosition(amount=0)})
    ctx = _FakeContext(portfolio=portfolio)
    assert fr._current_weight(ctx, asset) == 0.0


def test_current_weight_zero_portfolio_value_returns_zero():
    asset = object()
    portfolio = _FakePortfolio(
        positions={asset: _FakePosition(amount=100, last_sale_price=130.0)},
        portfolio_value=0.0,
    )
    ctx = _FakeContext(portfolio=portfolio)
    assert fr._current_weight(ctx, asset) == 0.0


def test_current_weight_normal_case():
    asset = object()
    portfolio = _FakePortfolio(
        positions={asset: _FakePosition(amount=100, last_sale_price=200.0)},
        portfolio_value=1_000_000,
    )
    ctx = _FakeContext(portfolio=portfolio)
    # 100 * 200 / 1_000_000 = 0.02
    assert fr._current_weight(ctx, asset) == pytest.approx(0.02)


# --------------------------------------------------------------------------- #
# _build_evaluate_bar
# --------------------------------------------------------------------------- #


def _prepared_row(**overrides) -> pd.Series:
    base = {
        "close": 110.0,
        "high": 112.0,
        "open": 108.0,
        "box_lower": 100.0,
        "risk_swing_low": 95.0,
        "volume": 1000.0,
        "avg_volume_5": 950.0,
        "upper_shadow": 0.5,
        "candle_body_size": 1.2,
        "structure_score": 8,
        "direction_score": 7,
        "chip_score": 6,
        "momentum_score": 5,
        "total_score": 26,
        "state_flameout": 0,
        "state_strong_buy": 1,
        "state_hold": 0,
        "state_warning": 0,
        "volatility_rate": 0.03,
    }
    base.update(overrides)
    return pd.Series(base)


def test_build_evaluate_bar_uses_prepared_columns():
    last = _prepared_row()
    prev = _prepared_row(total_score=24, momentum_score=4, high=111.0)
    eb = fr._build_evaluate_bar(last, prev, in_position=1, entry_cost_price=105.0)
    assert eb.in_position == 1
    assert eb.entry_cost_price == 105.0
    assert eb.close == 110.0
    assert eb.body_high == 110.0  # max(close, open)
    assert eb.body_low == 108.0   # min(close, open)
    assert eb.prev_total_score == 24
    assert eb.prev_high == 111.0


def test_build_evaluate_bar_handles_nan_float_with_zero_default():
    """Float NaN columns funnel through _f helper → 0.0."""
    last = _prepared_row(box_lower=np.nan, risk_swing_low=np.nan)
    prev = _prepared_row()
    eb = fr._build_evaluate_bar(last, prev, in_position=0, entry_cost_price=0.0)
    assert eb.box_lower == 0.0
    assert eb.risk_swing_low == 0.0


def test_build_evaluate_bar_missing_optional_column_defaults_to_zero():
    """Series.get() returns None for absent keys; _f converts to 0.0."""
    last = _prepared_row()
    last = last.drop(["box_lower", "risk_swing_low"])
    prev = _prepared_row()
    eb = fr._build_evaluate_bar(last, prev, in_position=0, entry_cost_price=0.0)
    assert eb.box_lower == 0.0
    assert eb.risk_swing_low == 0.0


# --------------------------------------------------------------------------- #
# evaluate_window_with_state
# --------------------------------------------------------------------------- #


def test_evaluate_window_with_state_returns_none_when_window_too_short():
    df = _make_merged_frame(n_bars=1)
    df_with_date = df.reset_index().rename(columns={"index": "trade_date"})
    df_with_date = df_with_date.set_index("trade_date")
    config = StrategyConfig()
    result = fr.evaluate_window_with_state(
        df_with_date, config, in_position=0, entry_cost_price=0.0
    )
    assert result == "none"


def test_evaluate_window_with_state_returns_signal_string_when_full_window():
    df = _make_merged_frame(n_bars=100)
    config = StrategyConfig()
    result = fr.evaluate_window_with_state(
        df, config, in_position=0, entry_cost_price=0.0
    )
    # Action enum domain
    assert result in (
        "stoploss",
        "exit",
        "takeprofit",
        "reduce",
        "add",
        "buy",
        "hold",
        "none",
    )


# --------------------------------------------------------------------------- #
# _execute_action — pass through to zipline order_target_percent
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("exit_action", ["stoploss", "exit", "takeprofit"])
def test_execute_action_exit_orders_target_zero(exit_action):
    asset = object()
    ctx = _FakeContext()
    with patch.object(fr, "order_target_percent") as mock_otp:
        fr._execute_action(ctx, asset, exit_action)
    mock_otp.assert_called_once_with(asset, 0)


def test_execute_action_buy_orders_buy_target_pct():
    asset = object()
    ctx = _FakeContext()
    with patch.object(fr, "order_target_percent") as mock_otp:
        fr._execute_action(ctx, asset, "buy")
    mock_otp.assert_called_once_with(asset, fr._BUY_TARGET_PCT)


def test_execute_action_add_increments_weight():
    asset = object()
    portfolio = _FakePortfolio(
        positions={asset: _FakePosition(amount=100, last_sale_price=200.0)},
        portfolio_value=1_000_000,
    )
    ctx = _FakeContext(portfolio=portfolio)
    with patch.object(fr, "order_target_percent") as mock_otp:
        fr._execute_action(ctx, asset, "add")
    # current weight 0.02 + 0.02 = 0.04
    args, _ = mock_otp.call_args
    assert args[0] is asset
    assert args[1] == pytest.approx(0.04)


def test_execute_action_reduce_decrements_weight():
    asset = object()
    portfolio = _FakePortfolio(
        positions={asset: _FakePosition(amount=200, last_sale_price=200.0)},
        portfolio_value=1_000_000,
    )
    ctx = _FakeContext(portfolio=portfolio)
    with patch.object(fr, "order_target_percent") as mock_otp:
        fr._execute_action(ctx, asset, "reduce")
    # current weight = 0.04 - 0.02 = 0.02
    args, _ = mock_otp.call_args
    assert args[1] == pytest.approx(0.02)


def test_execute_action_reduce_clamps_at_zero():
    """Reducing below zero must not emit negative target."""
    asset = object()
    ctx = _FakeContext()  # no position → current weight = 0
    with patch.object(fr, "order_target_percent") as mock_otp:
        fr._execute_action(ctx, asset, "reduce")
    args, _ = mock_otp.call_args
    assert args[1] == pytest.approx(0.0)


@pytest.mark.parametrize("noop_action", ["hold", "none"])
def test_execute_action_hold_emits_no_order(noop_action):
    ctx = _FakeContext()
    asset = object()
    with patch.object(fr, "order_target_percent") as mock_otp:
        fr._execute_action(ctx, asset, noop_action)
    mock_otp.assert_not_called()


# --------------------------------------------------------------------------- #
# initialize() — mock zipline.api side-effects
# --------------------------------------------------------------------------- #


def test_initialize_uses_default_universe_when_env_unset(monkeypatch):
    monkeypatch.delenv("UNIVERSE_FINMIND", raising=False)
    ctx = _FakeContext()
    fake_symbol = lambda s: f"asset_{s}"  # noqa: E731

    with (
        patch.object(fr, "symbol", side_effect=fake_symbol),
        patch.object(fr, "preload_merged_frames", return_value={}),
        patch.object(fr, "apply_taiwan_stock_rules"),
        patch.object(fr, "schedule_function") as mock_sched,
    ):
        fr.initialize(ctx)

    assert ctx.symbol_strs == list(fr.DEFAULT_UNIVERSE)
    assert ctx.assets == [f"asset_{s}" for s in fr.DEFAULT_UNIVERSE]
    assert isinstance(ctx.config, StrategyConfig)
    mock_sched.assert_called_once()


def test_initialize_respects_universe_env(monkeypatch):
    monkeypatch.setenv("UNIVERSE_FINMIND", "2330,2454")
    ctx = _FakeContext()

    with (
        patch.object(fr, "symbol", side_effect=lambda s: s),
        patch.object(fr, "preload_merged_frames", return_value={"2330": None, "2454": None}),
        patch.object(fr, "apply_taiwan_stock_rules"),
        patch.object(fr, "schedule_function"),
    ):
        fr.initialize(ctx)

    assert ctx.symbol_strs == ["2330", "2454"]


def test_initialize_calls_taiwan_stock_rules(monkeypatch):
    monkeypatch.setenv("UNIVERSE_FINMIND", "2330")
    ctx = _FakeContext()

    with (
        patch.object(fr, "symbol", side_effect=lambda s: s),
        patch.object(fr, "preload_merged_frames", return_value={"2330": None}),
        patch.object(fr, "apply_taiwan_stock_rules") as mock_rules,
        patch.object(fr, "schedule_function"),
    ):
        fr.initialize(ctx)

    mock_rules.assert_called_once_with(ctx.config)


# --------------------------------------------------------------------------- #
# evaluate_and_trade — orchestrator
# --------------------------------------------------------------------------- #


def test_evaluate_and_trade_skips_symbols_without_frames():
    ctx = _FakeContext(
        merged_frames={},  # nothing preloaded
        symbol_strs=["2330"],
    )
    with (
        patch.object(fr, "record") as mock_record,
        patch.object(fr, "order_target_percent") as mock_otp,
    ):
        fr.evaluate_and_trade(ctx, data=None)
    # No order placed, but record() called with n_evaluated=0
    mock_otp.assert_not_called()
    mock_record.assert_called_once()
    call_kwargs = mock_record.call_args.kwargs
    assert call_kwargs.get("n_evaluated") == 0


def test_evaluate_and_trade_skips_when_window_too_short_for_warmup():
    """If history < box_period + 5, evaluate is skipped (no order)."""
    short_frame = _make_merged_frame(n_bars=10)
    ctx = _FakeContext(
        merged_frames={"2330": short_frame},
        symbol_strs=["2330"],
    )
    ctx._dt = short_frame.index[-1]

    with (
        patch.object(fr, "record") as mock_record,
        patch.object(fr, "order_target_percent") as mock_otp,
    ):
        fr.evaluate_and_trade(ctx, data=None)
    mock_otp.assert_not_called()
    mock_record.assert_called_once()


def test_evaluate_and_trade_dispatches_action_to_execute():
    """Full window → evaluate_window returns something, _execute_action runs."""
    frame = _make_merged_frame(n_bars=100)
    ctx = _FakeContext(
        merged_frames={"2330": frame},
        symbol_strs=["2330"],
    )
    ctx._dt = frame.index[-1]

    with (
        patch.object(fr, "record") as mock_record,
        patch.object(fr, "order_target_percent"),
        patch.object(fr, "evaluate_window_with_state", return_value="buy"),
    ):
        fr.evaluate_and_trade(ctx, data=None)

    mock_record.assert_called_once()
    call_kwargs = mock_record.call_args.kwargs
    assert call_kwargs.get("n_evaluated") == 1
    assert call_kwargs.get("action_buy") == 1


def test_evaluate_and_trade_continues_on_per_symbol_exception():
    """Single-symbol evaluation failure must not abort the whole loop."""
    frame = _make_merged_frame(n_bars=100)
    ctx = _FakeContext(
        merged_frames={"2330": frame, "2454": frame},
        symbol_strs=["2330", "2454"],
    )
    ctx._dt = frame.index[-1]

    side_effects = [ValueError("boom"), "buy"]
    with (
        patch.object(fr, "record") as mock_record,
        patch.object(fr, "order_target_percent"),
        patch.object(fr, "evaluate_window_with_state", side_effect=side_effects),
    ):
        fr.evaluate_and_trade(ctx, data=None)

    # Only the second symbol was evaluated successfully
    call_kwargs = mock_record.call_args.kwargs
    assert call_kwargs.get("n_evaluated") == 1


# --------------------------------------------------------------------------- #
# handle_data — no-op stub
# --------------------------------------------------------------------------- #


def test_handle_data_returns_none():
    """zipline requires module-level handle_data; ours is a no-op."""
    assert fr.handle_data(object(), object()) is None
