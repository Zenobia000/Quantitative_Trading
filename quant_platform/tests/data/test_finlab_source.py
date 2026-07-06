"""Tests for the FinLab data source (① data-layer sub-project).

All FinLab access goes through an injected ``getter`` (a ``finlab.data.get``-like
callable), so these tests mock wide fixtures and never make a live API call.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from quant_platform.services.data_platform import finlab_source as fl
from quant_platform.packages.application.is_harness import load_merged_parquet

_INST = "institutional_investors_trading_summary"


def _wide(vals: list[list[float]], cols: list[str], idx: list[str]) -> pd.DataFrame:
    return pd.DataFrame(vals, index=pd.to_datetime(idx), columns=cols)


def _price_getter() -> fl.Getter:
    idx = ["2023-01-03", "2023-01-04"]
    cols = ["2330", "2317"]
    frames = {
        "etl:adj_open": _wide([[100, 50], [101, 51]], cols, idx),
        "etl:adj_high": _wide([[102, 52], [103, 53]], cols, idx),
        "etl:adj_low": _wide([[99, 49], [100, 50]], cols, idx),
        "etl:adj_close": _wide([[101, 51], [102, 52]], cols, idx),
        "price:成交股數": _wide([[1000, 2000], [1100, 2100]], cols, idx),
        f"{_INST}:外陸資買賣超股數(不含外資自營商)": _wide([[10, 20], [11, 21]], cols, idx),
        f"{_INST}:外資自營商買賣超股數": _wide([[1, 2], [1, 2]], cols, idx),
        f"{_INST}:投信買賣超股數": _wide([[5, 6], [5, 6]], cols, idx),
        f"{_INST}:自營商買賣超股數(自行買賣)": _wide([[3, 4], [3, 4]], cols, idx),
        f"{_INST}:自營商買賣超股數(避險)": _wide([[1, 1], [1, 1]], cols, idx),
    }
    return lambda key: frames[key]


def test_finlab_ingest_matches_finmind_schema(tmp_path):
    res = fl.ingest_universe_finlab(
        ["2330", "2317"], date(2023, 1, 1), date(2023, 1, 31),
        cache_dir=tmp_path, getter=_price_getter(),
    )
    assert set(res.ok_symbols) == {"2330", "2317"}
    assert res.failed_symbols == ()

    merged = load_merged_parquet("2330", parquet_dir=str(tmp_path))
    # schema parity with the FinMind bundle (what every consumer reads)
    assert {
        "stock_id", "trade_date", "open", "high", "low", "close", "volume", "adj_factor",
        "foreign_buy", "trust_buy", "dealer_buy",
    } <= set(merged.columns)
    assert merged["foreign_buy"].dtype == "int64"

    first = merged.sort_values("trade_date").iloc[0]
    # foreign_buy = 外陸資(10) + 外資自營商(1) = 11 ; dealer = 自行(3) + 避險(1) = 4
    assert int(first["foreign_buy"]) == 11
    assert int(first["dealer_buy"]) == 4
    assert int(first["trust_buy"]) == 5
    assert float(first["close"]) == 101.0


def test_finlab_ingest_marks_missing_symbol_failed(tmp_path):
    res = fl.ingest_universe_finlab(
        ["2330", "9999"], date(2023, 1, 1), date(2023, 1, 31),
        cache_dir=tmp_path, getter=_price_getter(),
    )
    assert res.ok_symbols == ("2330",)
    assert res.failed_symbols == ("9999",)


def test_survivorship_universe_includes_then_excludes_delisted():
    idx = pd.date_range("2020-01-01", "2021-12-31", freq="D")
    cols = ["A", "B", "DEAD"]
    mv = pd.DataFrame(3e9, index=idx, columns=cols)
    close = pd.DataFrame(50.0, index=idx, columns=cols)
    close.loc["2020-07-01":, "DEAD"] = float("nan")  # DEAD delists mid-2020
    turn = pd.DataFrame(5e7, index=idx, columns=cols)
    frames = {"etl:market_value": mv, "etl:adj_close": close, "price:成交金額": turn}

    led = fl.build_survivorship_universe(
        [date(2020, 4, 1), date(2020, 10, 1)],
        top_n=300, min_turnover=2e7, getter=lambda k: frames[k],
    )

    alive = led[(led.rebalance_date == "2020-04-01") & (led.stock_id == "DEAD")]
    dead = led[(led.rebalance_date == "2020-10-01") & (led.stock_id == "DEAD")]
    assert bool(alive["selected"].iloc[0]) is True  # present while alive
    assert dead["excluded_reason"].iloc[0] == "delisted"  # excluded after delist
    # survivors still selected at the later date
    assert bool(led[(led.rebalance_date == "2020-10-01") & (led.stock_id == "A")]["selected"].iloc[0])


def test_login_requires_token(monkeypatch):
    monkeypatch.delenv("FINLAB_API_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="FINLAB_API_TOKEN"):
        fl.login()
