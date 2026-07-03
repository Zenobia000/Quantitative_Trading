"""Tests for `parquet_cache.py` — read side of M1 ETL write_parquet."""
from __future__ import annotations

import json
from datetime import date

import pandas as pd
import pytest

from backtest_platform.data.finmind_etl import write_parquet
from backtest_platform.data.parquet_cache import (
    MANIFEST_NAME,
    ParquetCache,
    cached_or_fetch,
)
from backtest_platform.data.schemas import ETLBundle


def _make_range_bundle(stock_id: str, start: date, end: date) -> ETLBundle:
    """Bundle whose three frames carry one row at ``start`` and one at ``end``.

    Enough to exercise coverage-span math and merge/dedup without materialising a
    full business-day calendar. ``start == end`` yields a single row.
    """
    dates = sorted({start, end})
    n = len(dates)
    daily = pd.DataFrame(
        {
            "stock_id": [stock_id] * n,
            "trade_date": dates,
            "open": [100.0] * n,
            "high": [102.0] * n,
            "low": [99.0] * n,
            "close": [101.0] * n,
            "volume": [10000] * n,
            "adj_factor": [1.0] * n,
        }
    )
    inst = pd.DataFrame(
        {
            "stock_id": [stock_id] * n,
            "trade_date": dates,
            "foreign_buy": [0] * n,
            "trust_buy": [0] * n,
            "dealer_buy": [0] * n,
        }
    )
    chips = pd.DataFrame(
        {
            "stock_id": [stock_id] * n,
            "trade_date": dates,
            "top_broker_buy": [0] * n,
            "key_broker_buy": [0] * n,
            "gov_broker_buy": [0] * n,
            "geo_broker_buy": [0] * n,
            "day_trade_volume": [0] * n,
            "margin_offset_volume": [0] * n,
        }
    )
    return ETLBundle(
        stock_id=stock_id,
        start_date=start,
        end_date=end,
        daily_bars=daily,
        institutional=inst,
        broker_chips=chips,
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
    """cache miss case: request range exceeds cached range → re-fetch the gap.

    Under the merge policy the returned bundle's end_date is derived from the
    merged data span, and fetch_fn is invoked once for the tail gap only.
    """
    write_parquet(_make_range_bundle("2330", date(2024, 1, 2), date(2024, 1, 3)), tmp_path)
    cache = ParquetCache(root=tmp_path)

    called: dict[str, object] = {"n": 0, "ranges": []}

    def fake_fetch(stock_id, start, end):
        called["n"] += 1
        called["ranges"].append((start, end))
        return _make_range_bundle(stock_id, start, end)

    result = cached_or_fetch(
        "2330",
        date(2024, 1, 2),
        date(2024, 6, 30),  # past cached 2024-01-03
        cache,
        fetch_fn=fake_fetch,
    )
    assert called["n"] == 1  # one tail-gap fetch
    # gap starts strictly after the cached end_date (no full refetch of history)
    (gap_start, gap_end) = called["ranges"][0]
    assert gap_start > date(2024, 1, 3)
    assert gap_end == date(2024, 6, 30)
    # merged span reflects cached head + fetched tail
    assert result.start_date == date(2024, 1, 2)
    assert result.end_date == date(2024, 6, 30)


def test_cached_or_fetch_merges_gap_preserving_history(tmp_path):
    """Regression (HIGH): a partial-coverage ingest must NOT wipe cached history.

    Scenario from the bug report: cache holds 2020-2023, an ingest for 2024
    previously overwrote all three parquet files with just the 2024 slice,
    destroying (possibly paid) historical bars. The fix fetches only the gap and
    merges, so both the old and new ranges survive on disk.
    """
    cache = ParquetCache(root=tmp_path)
    write_parquet(
        _make_range_bundle("2330", date(2020, 1, 2), date(2023, 12, 29)), tmp_path
    )

    def fake_fetch(stock_id, start, end):
        # only ever asked for the missing 2024 tail
        assert start > date(2023, 12, 29), f"unexpected refetch of history: {start}"
        return _make_range_bundle(stock_id, start, end)

    result = cached_or_fetch(
        "2330", date(2020, 1, 2), date(2024, 12, 31), cache, fetch_fn=fake_fetch
    )
    assert result.start_date == date(2020, 1, 2)
    assert result.end_date == date(2024, 12, 31)

    # persisted parquet (reloaded from disk) also spans the full range
    reloaded = ParquetCache(root=tmp_path).load("2330")
    dts = pd.to_datetime(reloaded.daily_bars["trade_date"])
    assert dts.min().date() == date(2020, 1, 2)
    assert dts.max().date() == date(2024, 12, 31)
    assert reloaded.daily_bars["trade_date"].duplicated().sum() == 0


def test_cached_or_fetch_merge_dedups_overlapping_fetch(tmp_path):
    """Overlap between cache and a fetched range is de-duplicated on trade_date."""
    cache = ParquetCache(root=tmp_path)
    write_parquet(
        _make_range_bundle("2330", date(2024, 1, 2), date(2024, 1, 4)), tmp_path
    )

    def fake_fetch(stock_id, start, end):
        # deliberately overlap the cached 2024-01-04 boundary
        return _make_range_bundle(stock_id, date(2024, 1, 4), date(2024, 1, 8))

    result = cached_or_fetch(
        "2330", date(2024, 1, 2), date(2024, 1, 8), cache, fetch_fn=fake_fetch
    )
    assert result.daily_bars["trade_date"].duplicated().sum() == 0
    assert result.start_date == date(2024, 1, 2)
    assert result.end_date == date(2024, 1, 8)


def test_cached_or_fetch_writes_manifest(tmp_path):
    """ingest emits manifest.json with coverage / stock_count / hash / timestamp."""
    cache = ParquetCache(root=tmp_path)

    cached_or_fetch(
        "2330",
        date(2024, 1, 2),
        date(2024, 3, 29),
        cache,
        fetch_fn=lambda s, a, b: _make_range_bundle(s, a, b),
    )

    manifest_path = tmp_path / MANIFEST_NAME
    assert manifest_path.exists(), "manifest.json not written to cache root"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert data["stock_count"] == 1
    assert set(data["stocks"]) == {"2330"}
    assert data["stocks"]["2330"]["start"] == "2024-01-02"
    assert data["stocks"]["2330"]["end"] == "2024-03-29"
    assert data["stocks"]["2330"]["rows"] == 2
    assert isinstance(data["stocks"]["2330"]["data_hash"], str)
    assert data["stocks"]["2330"]["data_hash"]
    assert data["coverage"] == {"start": "2024-01-02", "end": "2024-03-29"}
    assert isinstance(data["data_hash"], str) and data["data_hash"]
    # ISO-8601 timestamp that round-trips
    from datetime import datetime

    datetime.fromisoformat(data["generated_at"])


def test_manifest_accumulates_across_stocks(tmp_path):
    """Sequential ingests (finmind_bundle loops symbols) build a union manifest."""
    cache = ParquetCache(root=tmp_path)
    fetch = lambda s, a, b: _make_range_bundle(s, a, b)  # noqa: E731

    cached_or_fetch("2330", date(2024, 1, 2), date(2024, 6, 28), cache, fetch_fn=fetch)
    cached_or_fetch("2317", date(2023, 1, 2), date(2024, 12, 31), cache, fetch_fn=fetch)

    data = json.loads((tmp_path / MANIFEST_NAME).read_text(encoding="utf-8"))
    assert data["stock_count"] == 2
    assert set(data["stocks"]) == {"2330", "2317"}
    # coverage is the union across stocks
    assert data["coverage"]["start"] == "2023-01-02"
    assert data["coverage"]["end"] == "2024-12-31"
