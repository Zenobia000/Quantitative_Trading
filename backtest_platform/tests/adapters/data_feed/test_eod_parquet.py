"""Tests for ``adapters.data_feed`` — the EOD parquet feed behind the DataFeed seam.

Builds a real parquet cache with the M1 ``write_parquet`` writer (synthetic bars,
no network) and reads it back through :class:`EODParquetFeed`, so dtype round-trips
are exercised exactly as production would hit them.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from backtest_platform.adapters.data_feed import DataFeed, EODParquetFeed
from backtest_platform.data.finmind_etl import write_parquet
from backtest_platform.data.schemas import ETLBundle


def _bundle(stock_id: str, rows: list[tuple[date, float]]) -> ETLBundle:
    dates = [d for d, _ in rows]
    closes = [c for _, c in rows]
    n = len(rows)
    daily = pd.DataFrame(
        {
            "stock_id": [stock_id] * n,
            "trade_date": dates,
            "open": closes,
            "high": [c + 1 for c in closes],
            "low": [c - 1 for c in closes],
            "close": closes,
            "volume": [10_000] * n,
            "adj_factor": [1.0] * n,
        }
    )
    inst = pd.DataFrame(
        {"stock_id": [stock_id] * n, "trade_date": dates, "foreign_buy": [0] * n, "trust_buy": [0] * n, "dealer_buy": [0] * n}
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
        start_date=dates[0],
        end_date=dates[-1],
        daily_bars=daily,
        institutional=inst,
        broker_chips=chips,
    )


def _seed(root, stock_id, rows):
    write_parquet(_bundle(stock_id, rows), root)


def test_feed_satisfies_protocol_and_flags(tmp_path):
    feed = EODParquetFeed(tmp_path)
    assert isinstance(feed, DataFeed)  # runtime_checkable structural conformance
    assert feed.supports_realtime is False


def test_get_daily_bars_filters_window_and_symbols(tmp_path):
    _seed(tmp_path, "2330", [(date(2024, 1, 2), 100.0), (date(2024, 1, 3), 101.0), (date(2024, 1, 4), 102.0)])
    _seed(tmp_path, "2317", [(date(2024, 1, 2), 50.0), (date(2024, 1, 3), 51.0)])
    feed = EODParquetFeed(tmp_path)

    df = feed.get_daily_bars(["2330", "2317"], date(2024, 1, 3), date(2024, 1, 4))
    assert set(df["stock_id"]) == {"2330", "2317"}
    # 2330 has two rows in window, 2317 has one (its 1/4 does not exist)
    assert list(df[df["stock_id"] == "2330"]["close"]) == [101.0, 102.0]
    assert list(df[df["stock_id"] == "2317"]["close"]) == [51.0]


def test_get_daily_bars_missing_symbol_skipped(tmp_path):
    _seed(tmp_path, "2330", [(date(2024, 1, 2), 100.0)])
    feed = EODParquetFeed(tmp_path)
    df = feed.get_daily_bars(["2330", "9999"], date(2024, 1, 1), date(2024, 1, 31))
    assert set(df["stock_id"]) == {"2330"}


def test_get_daily_bars_empty_when_nothing_matches(tmp_path):
    feed = EODParquetFeed(tmp_path)
    df = feed.get_daily_bars(["2330"], date(2024, 1, 1), date(2024, 1, 31))
    assert df.empty


def test_get_latest_prices_returns_last_close(tmp_path):
    _seed(tmp_path, "2330", [(date(2024, 1, 2), 100.0), (date(2024, 1, 5), 105.0), (date(2024, 1, 3), 101.0)])
    feed = EODParquetFeed(tmp_path)
    prices = feed.get_latest_prices(["2330", "9999"])
    # latest by trade_date is 1/5 even though rows are unordered on disk
    assert prices == {"2330": 105.0}
