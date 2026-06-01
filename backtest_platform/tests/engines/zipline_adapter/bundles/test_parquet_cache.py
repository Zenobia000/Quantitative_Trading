"""Tests for `parquet_cache.py` — read side of M1 ETL write_parquet."""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from backtest_platform.data.finmind_etl import write_parquet
from backtest_platform.data.schemas import ETLBundle
from backtest_platform.engines.zipline_adapter.bundles.parquet_cache import (
    ParquetCache,
    cached_or_fetch,
)


def _make_bundle(stock_id: str = "2330") -> ETLBundle:
    """Minimal valid bundle for round-trip tests."""
    daily = pd.DataFrame(
        {
            "stock_id": [stock_id, stock_id],
            "trade_date": [date(2024, 1, 2), date(2024, 1, 3)],
            "open": [100.0, 101.0],
            "high": [102.0, 103.0],
            "low": [99.0, 100.5],
            "close": [101.0, 102.0],
            "volume": [10000, 12000],
            "adj_factor": [1.0, 1.0],
        }
    )
    inst = pd.DataFrame(
        {
            "stock_id": [stock_id, stock_id],
            "trade_date": [date(2024, 1, 2), date(2024, 1, 3)],
            "foreign_buy": [500, -200],
            "trust_buy": [100, 50],
            "dealer_buy": [0, 0],
        }
    )
    chips = pd.DataFrame(
        {
            "stock_id": [stock_id, stock_id],
            "trade_date": [date(2024, 1, 2), date(2024, 1, 3)],
            "top_broker_buy": [0, 0],
            "key_broker_buy": [0, 0],
            "gov_broker_buy": [0, 0],
            "geo_broker_buy": [0, 0],
            "day_trade_volume": [1000, 1500],
            "margin_offset_volume": [0, 0],
        }
    )
    return ETLBundle(
        stock_id=stock_id,
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 3),
        daily_bars=daily,
        institutional=inst,
        broker_chips=chips,
    )


def test_exists_returns_false_when_no_files(tmp_path):
    cache = ParquetCache(root=tmp_path)
    assert cache.exists("2330") is False


def test_exists_true_only_when_all_three_files_present(tmp_path):
    """Partial cache (e.g. only daily_bars) must NOT count as hit —
    downstream merged() would silently lose institutional/chip columns."""
    cache = ParquetCache(root=tmp_path)
    (tmp_path / "daily_bars__2330.parquet").write_bytes(b"stub")
    assert cache.exists("2330") is False  # still missing inst + chips
    (tmp_path / "institutional__2330.parquet").write_bytes(b"stub")
    assert cache.exists("2330") is False  # still missing chips
    (tmp_path / "broker_chips__2330.parquet").write_bytes(b"stub")
    assert cache.exists("2330") is True


def test_load_round_trip_preserves_bundle(tmp_path):
    """write_parquet → ParquetCache.load should return equivalent ETLBundle."""
    original = _make_bundle("2330")
    write_parquet(original, tmp_path)

    cache = ParquetCache(root=tmp_path)
    loaded = cache.load("2330")

    assert loaded.stock_id == original.stock_id
    assert loaded.start_date == original.start_date
    assert loaded.end_date == original.end_date
    pd.testing.assert_frame_equal(
        loaded.daily_bars.reset_index(drop=True),
        original.daily_bars.reset_index(drop=True),
    )


def test_load_or_none_returns_none_on_miss(tmp_path):
    cache = ParquetCache(root=tmp_path)
    assert cache.load_or_none("2330") is None


def test_cached_or_fetch_uses_cache_when_range_covered(tmp_path):
    """cache hit: fetch_fn must NOT be invoked."""
    original = _make_bundle("2330")
    write_parquet(original, tmp_path)
    cache = ParquetCache(root=tmp_path)

    def _should_not_be_called(*args, **kwargs):
        pytest.fail("fetch_fn was called despite valid cache")

    result = cached_or_fetch(
        "2330",
        date(2024, 1, 2),
        date(2024, 1, 3),
        cache,
        fetch_fn=_should_not_be_called,
    )
    assert result.stock_id == "2330"


def test_cached_or_fetch_calls_fetch_when_range_extends_past_cache(tmp_path):
    """cache miss case: request range exceeds cached range → re-fetch."""
    original = _make_bundle("2330")
    write_parquet(original, tmp_path)
    cache = ParquetCache(root=tmp_path)

    expanded_bundle = _make_bundle("2330")
    expanded_bundle = ETLBundle(
        stock_id="2330",
        start_date=date(2024, 1, 2),
        end_date=date(2024, 12, 31),  # extends past cached end_date
        daily_bars=expanded_bundle.daily_bars,
        institutional=expanded_bundle.institutional,
        broker_chips=expanded_bundle.broker_chips,
    )

    called: dict[str, int] = {"n": 0}

    def fake_fetch(stock_id, start, end):
        called["n"] += 1
        return expanded_bundle

    result = cached_or_fetch(
        "2330",
        date(2024, 1, 2),
        date(2024, 6, 30),  # past cached 2024-01-03
        cache,
        fetch_fn=fake_fetch,
    )
    assert called["n"] == 1
    assert result.end_date == date(2024, 12, 31)
