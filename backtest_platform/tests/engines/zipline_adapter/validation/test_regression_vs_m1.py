"""Regression test: zipline_adapter actions vs M1 baseline.

Per plan v3.0 §11 R7: actions sequence must agree between M1 pipeline
ground-truth and the zipline live-mode emulation (sequential evaluate_bar
walk with maintained state). Divergence indicates a wrapper bug.

Acceptance: match_pct >= 0.999 (plan v3.0 §12 Sprint 2).

Most cases require a cached parquet bundle, which is only populated when
`zipline ingest -b finmind` has been run. Tests are skipped if no cache
exists so unit-test CI stays green; integration runners with cache will
execute the real comparison.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from backtest_platform.strategies.four_layer_resonance.config import StrategyConfig
from backtest_platform.engines.zipline_adapter.algorithms.four_layer_resonance import (
    _build_evaluate_bar,
    evaluate_window_with_state,
)
from backtest_platform.engines.zipline_adapter.bundles.parquet_cache import (
    ParquetCache,
)
from backtest_platform.engines.zipline_adapter.validation.regression_vs_m1 import (
    compare_actions,
    compute_m1_actions,
    compute_zipline_actions,
)
from backtest_platform.strategies.four_layer_resonance.signals import (
    EvaluateBar,
    SignalName,
    evaluate_bar,
)


def _cache_has(symbol: str) -> bool:
    cache = ParquetCache(root=Path("data/parquet"))
    return cache.exists(symbol)


@pytest.fixture
def stock_2330() -> str:
    """Skip tests if 2330 cache missing (CI without ingest)."""
    if not _cache_has("2330"):
        pytest.skip("2330 parquet cache missing — run `zipline ingest -b finmind`")
    return "2330"


@pytest.mark.integration
def test_2330_full_year_2024_matches(stock_2330):
    """Full year 2024 regression — the acceptance check.

    Both compute paths must produce identical action sequences on the
    requested range. With proper warmup buffer (180 calendar days),
    indicators are stable on the first range bar and onwards.
    """
    result = compare_actions(stock_2330, date(2024, 1, 1), date(2024, 12, 31))
    assert result.total_bars > 0, "no bars compared — data slicing bug"
    assert result.match_pct >= 0.999, (
        f"match_pct={result.match_pct:.4%} below acceptance 99.9%; "
        f"first mismatches: {result.mismatch_details[:5]}"
    )


@pytest.mark.integration
def test_2330_short_range_matches(stock_2330):
    """Short range (3 months) — verifies warmup buffer is enough."""
    result = compare_actions(stock_2330, date(2024, 6, 1), date(2024, 8, 31))
    assert result.match_pct >= 0.999, (
        f"short-range match_pct={result.match_pct:.4%}; "
        f"mismatches: {result.mismatch_details[:5]}"
    )


@pytest.mark.integration
def test_compute_m1_emits_warmup_filtered_range(stock_2330):
    """M1 baseline must drop warmup bars from output."""
    start = date(2024, 1, 1)
    end = date(2024, 6, 30)
    df = compute_m1_actions(stock_2330, start, end)
    assert not df.empty
    assert df["trade_date"].min() >= start, "warmup bars leaked into output"
    assert df["trade_date"].max() <= end


@pytest.mark.integration
def test_compute_zipline_emits_same_range(stock_2330):
    """zipline emulation must produce same date range as M1."""
    start = date(2024, 1, 1)
    end = date(2024, 6, 30)
    m1 = compute_m1_actions(stock_2330, start, end)
    z = compute_zipline_actions(stock_2330, start, end)
    assert len(m1) == len(z), f"row count diverges: m1={len(m1)} z={len(z)}"
    # Dates must align
    pd.testing.assert_series_equal(
        m1["trade_date"].reset_index(drop=True),
        z["trade_date"].reset_index(drop=True),
        check_names=False,
    )


# ---------------------------------------------------------------------------
# Synthetic unit tests for the wrapper helper (no parquet cache needed)
# ---------------------------------------------------------------------------


def _make_eb(**overrides) -> EvaluateBar:
    """Build an EvaluateBar with safe defaults; override for specific cases."""
    base: dict = {
        "in_position": 0,
        "entry_cost_price": 0.0,
        "close": 100.0,
        "high": 101.0,
        "open": 99.0,
        "box_lower": 95.0,
        "risk_swing_low": 90.0,
        "volume": 1000.0,
        "avg_volume_5": 1000.0,
        "body_high": 100.0,
        "body_low": 99.0,
        "upper_shadow": 1.0,
        "candle_body_size": 1.0,
        "structure_score": 0,
        "direction_score": 0,
        "chip_score": 0,
        "momentum_score": 0,
        "total_score": 0,
        "prev_total_score": 0.0,
        "prev_momentum_score": 0.0,
        "prev_high": 100.0,
        "state_flameout": 0,
        "state_strong_buy": 0,
        "state_hold": 0,
        "state_warning": 0,
        "volatility_rate": 0.05,
    }
    base.update(overrides)
    return EvaluateBar(**base)


def test_evaluate_bar_hold_when_in_position_and_strong():
    """Sanity: position=1 + total_score >= 3 + momentum >= 1 → 'hold'."""
    config = StrategyConfig()
    eb = _make_eb(
        in_position=1,
        entry_cost_price=95.0,
        total_score=4,
        momentum_score=2,
    )
    action: SignalName = evaluate_bar(eb, config)
    assert action == "hold"


def test_evaluate_bar_stoploss_when_close_below_box_lower():
    """In position + close < box_lower → 'stoploss' (highest priority)."""
    config = StrategyConfig()
    eb = _make_eb(
        in_position=1,
        entry_cost_price=100.0,
        close=90.0,  # below box_lower=95
        box_lower=95.0,
    )
    assert evaluate_bar(eb, config) == "stoploss"


def test_build_evaluate_bar_extracts_columns_correctly():
    """_build_evaluate_bar must map series columns to dataclass fields."""
    last = pd.Series({
        "close": 100.0, "high": 105.0, "open": 98.0,
        "box_lower": 92.0, "risk_swing_low": 90.0,
        "volume": 1000.0, "avg_volume_5": 950.0,
        "upper_shadow": 2.0, "candle_body_size": 2.0,
        "structure_score": 2, "direction_score": 1,
        "chip_score": 1, "momentum_score": 2, "total_score": 6,
        "state_flameout": 0, "state_strong_buy": 1,
        "state_hold": 1, "state_warning": 0,
        "volatility_rate": 0.08,
    })
    prev = pd.Series({
        "total_score": 5, "momentum_score": 2, "high": 102.0,
    })
    eb = _build_evaluate_bar(last, prev, in_position=1, entry_cost_price=95.0)

    assert eb.in_position == 1
    assert eb.entry_cost_price == 95.0
    assert eb.close == 100.0
    assert eb.body_high == 100.0  # max(close=100, open=98)
    assert eb.body_low == 98.0  # min(close=100, open=98)
    assert eb.total_score == 6
    assert eb.prev_total_score == 5.0
    assert eb.prev_high == 102.0
    assert eb.state_strong_buy == 1


def test_evaluate_window_with_state_handles_short_window():
    """Window of length 0 or 1 returns 'none' (insufficient history)."""
    config = StrategyConfig()
    empty = pd.DataFrame(
        columns=["open", "high", "low", "close", "volume"],
        index=pd.DatetimeIndex([], name="trade_date"),
    )
    assert evaluate_window_with_state(empty, config, 0, 0.0) == "none"
