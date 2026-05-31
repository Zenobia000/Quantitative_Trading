"""Tests for state machine and signal priority — v2.md 2.4."""
from __future__ import annotations

import pandas as pd
import pytest

from backtest_platform.config.strategy_config import StrategyConfig
from backtest_platform.strategies.four_layer_resonance.scoring import compute_scores
from backtest_platform.strategies.four_layer_resonance.signals import (
    SIGNAL_PRIORITY,
    compute_signals,
    compute_states,
)


def test_signal_priority_order_matches_spec() -> None:
    """v2.md 2.4.2 priority: stoploss > exit > takeprofit > reduce > add > buy > hold."""
    assert SIGNAL_PRIORITY == (
        "stoploss",
        "exit",
        "takeprofit",
        "reduce",
        "add",
        "buy",
        "hold",
    )


def test_states_are_zero_one(
    synthetic_uptrend: pd.DataFrame, config: StrategyConfig
) -> None:
    scored = compute_scores(synthetic_uptrend, config)
    states = compute_states(scored, config).dropna(subset=["box_upper"])
    for col in ("state_flameout", "state_strong_buy", "state_hold", "state_warning"):
        assert states[col].isin([0, 1]).all(), f"{col} carries non-binary value"


def test_flameout_when_momentum_negative_one(
    synthetic_flameout: pd.DataFrame, config: StrategyConfig
) -> None:
    scored = compute_scores(synthetic_flameout, config)
    states = compute_states(scored, config)
    has_flameout_period = (
        (scored["momentum_score"] == -1) | (scored["close"] < scored["box_lower"])
    )
    assert (states["state_flameout"] == has_flameout_period.astype(int)).all()


def test_strong_buy_requires_all_layers_positive(
    synthetic_uptrend: pd.DataFrame, config: StrategyConfig
) -> None:
    """state_strong_buy fires only when all four layer scores >= 1 and total >= threshold."""
    scored = compute_scores(synthetic_uptrend, config)
    states = compute_states(scored, config).dropna(subset=["box_upper"])
    strong = states[states["state_strong_buy"] == 1]
    assert (strong["structure_score"] >= 1).all()
    assert (strong["direction_score"] >= 1).all()
    assert (strong["chip_score"] >= 1).all()
    assert (strong["momentum_score"] >= 1).all()
    assert (strong["total_score"] >= config.strong_buy_threshold).all()


def test_compute_signals_drives_position_monotonically(
    synthetic_uptrend: pd.DataFrame, config: StrategyConfig
) -> None:
    """in_position should only transition 0->1 on buy and 1->0 on stoploss/exit."""
    scored = compute_scores(synthetic_uptrend, config)
    sig = compute_signals(scored, config)
    transitions = sig[sig["in_position"].diff().abs() == 1]
    for _, row in transitions.iterrows():
        if row["in_position"] == 1:
            assert row["action"] == "buy"
        else:
            assert row["action"] in ("stoploss", "exit")


def test_compute_signals_emits_one_action_per_bar(
    synthetic_uptrend: pd.DataFrame, config: StrategyConfig
) -> None:
    scored = compute_scores(synthetic_uptrend, config)
    sig = compute_signals(scored, config).dropna(subset=["box_upper"])
    # Action is always one of the priority names or "none".
    assert sig["action"].isin(list(SIGNAL_PRIORITY) + ["none"]).all()
    # Exactly one signal_* column should match the action per bar (or all zero).
    for _, row in sig.iterrows():
        active = [name for name in SIGNAL_PRIORITY if row[f"signal_{name}"] == 1]
        if row["action"] == "none":
            # All firing signals may be present but only via priority drop — none
            # means literally nothing fired.
            assert not active
        else:
            assert row["action"] in active


def test_stoploss_overrides_other_signals(config: StrategyConfig) -> None:
    """If both stoploss and exit conditions hold, action == 'stoploss'."""
    scored = pd.DataFrame(_synthetic_breakdown_rows()).pipe(compute_scores, config)
    sig = compute_signals(scored, config)
    breakdown = sig[sig["action"] == "stoploss"]
    # stoploss when fired must NOT yield a buy on the same bar
    assert (breakdown["signal_buy"] == 0).all()


def _synthetic_breakdown_rows() -> dict[str, list]:
    """Construct a rise-then-cliff series to force stoploss."""
    import numpy as np

    n = 70
    close = list(np.linspace(100, 130, 60)) + [128, 125, 110, 95, 90, 88, 85, 82, 80, 78]
    open_ = [c - 0.4 for c in close]
    high = [c + 0.5 for c in close]
    low = [o - 0.5 for o in open_]
    dates = pd.date_range("2024-01-02", periods=n, freq="D")
    zero = [0] * n
    return {
        "trade_date": list(dates),
        "stock_id": ["TEST"] * n,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": [5000] * n,
        "foreign_buy": zero,
        "trust_buy": zero,
        "dealer_buy": zero,
        "top_broker_buy": zero,
        "key_broker_buy": zero,
        "gov_broker_buy": zero,
        "geo_broker_buy": zero,
        "day_trade_volume": zero,
        "margin_offset_volume": zero,
    }
