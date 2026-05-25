"""Tests for compute_scores — score columns must respect v2.md 2.3 score ranges."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest_platform.config.strategy_config import StrategyConfig
from backtest_platform.strategy.scoring import REQUIRED_COLUMNS, compute_scores


def test_missing_columns_raises(synthetic_uptrend: pd.DataFrame, config: StrategyConfig) -> None:
    df = synthetic_uptrend.drop(columns=["foreign_buy"])
    with pytest.raises(ValueError, match="missing required columns"):
        compute_scores(df, config)


def test_required_columns_constant_matches_schema(synthetic_uptrend: pd.DataFrame) -> None:
    """Catch drift: every REQUIRED_COLUMNS entry should appear in fixture."""
    missing = [c for c in REQUIRED_COLUMNS if c not in synthetic_uptrend.columns]
    assert missing == []


def test_scores_within_documented_ranges(
    synthetic_uptrend: pd.DataFrame, config: StrategyConfig
) -> None:
    out = compute_scores(synthetic_uptrend, config).dropna(subset=["box_upper"])
    assert out["structure_score"].between(0, 2).all()
    assert out["direction_score"].between(-1, 2).all()
    assert out["chip_score"].between(-1, 2).all()
    assert out["momentum_score"].between(-1, 2).all()
    assert out["total_score"].between(-3, 8).all()


def test_structure_breakout_scores_two(config: StrategyConfig) -> None:
    """Close above box_upper must score 2 on structure."""
    df = _flat_then_breakout(config.box_period)
    out = compute_scores(df, config)
    breakout_row = out.iloc[-1]
    assert breakout_row["structure_score"] == 2
    assert breakout_row["close"] > breakout_row["box_upper"]


def test_l2_direction_both_positive_scores_two(
    synthetic_uptrend: pd.DataFrame, config: StrategyConfig
) -> None:
    """When both foreign and trust are positive, direction_score == 2."""
    out = compute_scores(synthetic_uptrend, config)
    both_pos = out[(out["foreign_buy"] > 0) & (out["trust_buy"] > 0)]
    assert (both_pos["direction_score"] == 2).all()


def test_l3_chip_ratio_above_threshold_scores_two(config: StrategyConfig) -> None:
    """Force chip_ratio >= 0.10 by oversizing chip_total relative to net_volume."""
    df = _flat_then_breakout(config.box_period)
    df["foreign_buy"] = 10000  # huge inflow vs ~5000 volume
    df["trust_buy"] = 0
    df["dealer_buy"] = 0
    df["top_broker_buy"] = 0
    df["key_broker_buy"] = 0
    df["gov_broker_buy"] = 0
    df["geo_broker_buy"] = 0
    out = compute_scores(df, config)
    last = out.iloc[-1]
    assert last["chip_ratio"] >= config.chip_strong_threshold
    assert last["chip_score"] == 2


def test_l3_chip_zero_net_volume_carries_previous(config: StrategyConfig) -> None:
    """net_volume == 0 should not produce inf — must ffill prior value."""
    df = _flat_then_breakout(config.box_period)
    df.loc[df.index[-1], "day_trade_volume"] = df.loc[df.index[-1], "volume"]
    df.loc[df.index[-1], "margin_offset_volume"] = 0
    out = compute_scores(df, config)
    assert np.isfinite(out["chip_ratio"]).all()


def test_total_equals_sum_of_layers(
    synthetic_uptrend: pd.DataFrame, config: StrategyConfig
) -> None:
    out = compute_scores(synthetic_uptrend, config).dropna(subset=["box_upper"])
    layered_sum = (
        out["structure_score"]
        + out["direction_score"]
        + out["chip_score"]
        + out["momentum_score"]
    )
    assert (out["total_score"] == layered_sum).all()


def _flat_then_breakout(box_period: int) -> pd.DataFrame:
    """Build a flat series of length box_period followed by an explosive day.

    All chip / institutional columns set to neutral defaults so tests can
    override per-case to focus on a single layer.
    """
    n = box_period + 5
    rng = np.random.default_rng(0)
    close = np.full(n, 100.0)
    close[-1] = 130.0  # breakout
    open_ = close - 0.5
    high = close + 0.5
    low = open_ - 0.5
    high[-1] = 131.0
    return pd.DataFrame(
        {
            "trade_date": pd.date_range("2024-01-02", periods=n, freq="D"),
            "stock_id": "TEST",
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": rng.integers(4000, 6000, n),
            "foreign_buy": np.zeros(n, dtype=int),
            "trust_buy": np.zeros(n, dtype=int),
            "dealer_buy": np.zeros(n, dtype=int),
            "top_broker_buy": np.zeros(n, dtype=int),
            "key_broker_buy": np.zeros(n, dtype=int),
            "gov_broker_buy": np.zeros(n, dtype=int),
            "geo_broker_buy": np.zeros(n, dtype=int),
            "day_trade_volume": np.zeros(n, dtype=int),
            "margin_offset_volume": np.zeros(n, dtype=int),
        }
    )
