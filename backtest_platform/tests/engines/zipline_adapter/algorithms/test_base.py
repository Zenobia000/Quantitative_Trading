"""Tests for `algorithms/base.py` — preload + history window helpers.

Skips end-to-end zipline integration (slow, requires bundle ingest);
covered separately by `test_four_layer_resonance_smoke.py`.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from backtest_platform.data.finmind_etl import write_parquet
from backtest_platform.data.schemas import ETLBundle
from backtest_platform.engines.zipline_adapter.algorithms.base import (
    as_of_to_date,
    get_history_window,
    preload_merged_frames,
)


def _make_bundle(stock_id: str, n_days: int = 5) -> ETLBundle:
    dates = pd.date_range("2024-01-02", periods=n_days, freq="B").date
    daily = pd.DataFrame(
        {
            "stock_id": [stock_id] * n_days,
            "trade_date": dates,
            "open": [100.0 + i for i in range(n_days)],
            "high": [101.0 + i for i in range(n_days)],
            "low": [99.0 + i for i in range(n_days)],
            "close": [100.5 + i for i in range(n_days)],
            "volume": [10_000 * (i + 1) for i in range(n_days)],
            "adj_factor": [1.0] * n_days,
        }
    )
    inst = pd.DataFrame(
        {
            "stock_id": [stock_id] * n_days,
            "trade_date": dates,
            "foreign_buy": [i * 100 for i in range(n_days)],
            "trust_buy": [i * 50 for i in range(n_days)],
            "dealer_buy": [0] * n_days,
        }
    )
    chips = pd.DataFrame(
        {
            "stock_id": [stock_id] * n_days,
            "trade_date": dates,
            "top_broker_buy": [0] * n_days,
            "key_broker_buy": [0] * n_days,
            "gov_broker_buy": [0] * n_days,
            "geo_broker_buy": [0] * n_days,
            "day_trade_volume": [500 * (i + 1) for i in range(n_days)],
            "margin_offset_volume": [0] * n_days,
        }
    )
    return ETLBundle(
        stock_id=stock_id,
        start_date=dates[0],
        end_date=dates[-1],
        daily_bars=daily,
        institutional=inst,
        broker_chips=chips,
    )


def test_preload_returns_dict_keyed_by_symbol(tmp_path):
    for sym in ("2330", "2454"):
        write_parquet(_make_bundle(sym), tmp_path)

    frames = preload_merged_frames(["2330", "2454"], cache_dir=tmp_path)
    assert set(frames.keys()) == {"2330", "2454"}
    assert len(frames["2330"]) == 5


def test_preload_raises_when_cache_missing(tmp_path):
    """User must run zipline ingest first."""
    with pytest.raises(FileNotFoundError, match="parquet cache miss"):
        preload_merged_frames(["NONEXISTENT"], cache_dir=tmp_path)


def test_preload_index_is_datetime(tmp_path):
    """Algorithm uses `frame.loc[<=as_of]` — index must be tz-naive DatetimeIndex."""
    write_parquet(_make_bundle("2330"), tmp_path)
    frames = preload_merged_frames(["2330"], cache_dir=tmp_path)
    assert isinstance(frames["2330"].index, pd.DatetimeIndex)
    assert frames["2330"].index.tz is None


def test_preload_merged_has_required_columns(tmp_path):
    """compute_scores expects 14 REQUIRED_COLUMNS; ensure preload yields them."""
    from backtest_platform.strategies.four_layer_resonance.scoring import (
        REQUIRED_COLUMNS,
    )

    write_parquet(_make_bundle("2330"), tmp_path)
    frames = preload_merged_frames(["2330"], cache_dir=tmp_path)
    missing = set(REQUIRED_COLUMNS) - set(frames["2330"].columns)
    assert not missing, f"merged frame missing: {missing}"


def test_get_history_window_returns_bar_count_rows(tmp_path):
    write_parquet(_make_bundle("2330", n_days=10), tmp_path)
    frame = preload_merged_frames(["2330"], cache_dir=tmp_path)["2330"]

    # Ask for last 3 bars as of day 6
    as_of = frame.index[5]
    window = get_history_window(frame, as_of, bar_count=3)
    assert len(window) == 3
    assert window.index[-1] == as_of


def test_get_history_window_excludes_future_bars(tmp_path):
    """Critical: no lookahead bias. Even if more rows exist, window cuts at as_of."""
    write_parquet(_make_bundle("2330", n_days=10), tmp_path)
    frame = preload_merged_frames(["2330"], cache_dir=tmp_path)["2330"]

    as_of = frame.index[3]  # day 4
    window = get_history_window(frame, as_of, bar_count=100)
    assert len(window) == 4  # only days 1-4
    assert (window.index <= as_of).all()


def test_get_history_window_handles_tz_aware_as_of(tmp_path):
    """zipline timestamps are tz-aware UTC; our frame is naive. Test handles both."""
    write_parquet(_make_bundle("2330", n_days=5), tmp_path)
    frame = preload_merged_frames(["2330"], cache_dir=tmp_path)["2330"]

    tz_aware = pd.Timestamp(frame.index[2]).tz_localize("UTC")
    window = get_history_window(frame, tz_aware, bar_count=2)
    assert len(window) == 2


def test_as_of_to_date_strips_timezone():
    """zipline timestamps need conversion for M1 functions (which use date)."""
    tz_aware = pd.Timestamp("2024-03-15 14:30:00", tz="UTC")
    assert as_of_to_date(tz_aware) == date(2024, 3, 15)


def test_as_of_to_date_naive_timestamp():
    naive = pd.Timestamp("2024-03-15")
    assert as_of_to_date(naive) == date(2024, 3, 15)
