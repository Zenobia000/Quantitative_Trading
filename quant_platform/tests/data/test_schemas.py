"""Pydantic schema validation tests for data/schemas.py.

Schemas are the system boundary contract: ETL → parquet → DB → strategy.
Catches breaking schema changes early.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest
from pydantic import ValidationError

from quant_platform.services.data_platform.schemas import (
    BrokerChipRow,
    DailyBarRow,
    ETLBundle,
    InstitutionalRow,
)


# --------------------------------------------------------------------------- #
# DailyBarRow
# --------------------------------------------------------------------------- #


def test_daily_bar_row_minimum_valid():
    row = DailyBarRow(
        stock_id="2330",
        trade_date=date(2024, 1, 2),
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.5,
        volume=1000,
    )
    assert row.stock_id == "2330"
    assert row.adj_factor == 1.0  # default


def test_daily_bar_row_rejects_empty_stock_id():
    with pytest.raises(ValidationError):
        DailyBarRow(
            stock_id="",
            trade_date=date(2024, 1, 2),
            open=100.0, high=101.0, low=99.0, close=100.5, volume=0,
        )


def test_daily_bar_row_rejects_negative_price():
    with pytest.raises(ValidationError):
        DailyBarRow(
            stock_id="2330",
            trade_date=date(2024, 1, 2),
            open=-1.0, high=101.0, low=99.0, close=100.5, volume=0,
        )


def test_daily_bar_row_rejects_zero_price():
    with pytest.raises(ValidationError):
        DailyBarRow(
            stock_id="2330",
            trade_date=date(2024, 1, 2),
            open=0.0, high=101.0, low=99.0, close=100.5, volume=0,
        )


def test_daily_bar_row_rejects_negative_volume():
    with pytest.raises(ValidationError):
        DailyBarRow(
            stock_id="2330",
            trade_date=date(2024, 1, 2),
            open=100.0, high=101.0, low=99.0, close=100.5, volume=-100,
        )


def test_daily_bar_row_rejects_overlong_stock_id():
    with pytest.raises(ValidationError):
        DailyBarRow(
            stock_id="A" * 11,  # max_length=10
            trade_date=date(2024, 1, 2),
            open=100.0, high=101.0, low=99.0, close=100.5, volume=0,
        )


def test_daily_bar_row_custom_adj_factor():
    row = DailyBarRow(
        stock_id="2330",
        trade_date=date(2024, 1, 2),
        open=100.0, high=101.0, low=99.0, close=100.5, volume=1000,
        adj_factor=0.95,
    )
    assert row.adj_factor == 0.95


def test_daily_bar_row_rejects_zero_adj_factor():
    with pytest.raises(ValidationError):
        DailyBarRow(
            stock_id="2330",
            trade_date=date(2024, 1, 2),
            open=100.0, high=101.0, low=99.0, close=100.5, volume=0,
            adj_factor=0.0,
        )


# --------------------------------------------------------------------------- #
# InstitutionalRow
# --------------------------------------------------------------------------- #


def test_institutional_row_defaults_to_zero_flows():
    row = InstitutionalRow(stock_id="2330", trade_date=date(2024, 1, 2))
    assert row.foreign_buy == 0
    assert row.trust_buy == 0
    assert row.dealer_buy == 0


def test_institutional_row_accepts_negative_flows():
    """Institutional net flow can be negative (net sell day)."""
    row = InstitutionalRow(
        stock_id="2330",
        trade_date=date(2024, 1, 2),
        foreign_buy=-1000,
        trust_buy=-500,
        dealer_buy=-200,
    )
    assert row.foreign_buy == -1000


# --------------------------------------------------------------------------- #
# BrokerChipRow
# --------------------------------------------------------------------------- #


def test_broker_chip_row_defaults():
    row = BrokerChipRow(stock_id="2330", trade_date=date(2024, 1, 2))
    assert row.day_trade_volume == 0
    assert row.margin_offset_volume == 0


def test_broker_chip_row_rejects_negative_day_trade_volume():
    with pytest.raises(ValidationError):
        BrokerChipRow(
            stock_id="2330",
            trade_date=date(2024, 1, 2),
            day_trade_volume=-1,
        )


# --------------------------------------------------------------------------- #
# ETLBundle.merged()
# --------------------------------------------------------------------------- #


def _mk_etl_bundle(n: int = 3) -> ETLBundle:
    dates = pd.date_range("2024-01-02", periods=n, freq="B").date
    daily = pd.DataFrame(
        {
            "stock_id": ["2330"] * n,
            "trade_date": dates,
            "open": [100.0 + i for i in range(n)],
            "high": [101.0 + i for i in range(n)],
            "low": [99.0 + i for i in range(n)],
            "close": [100.5 + i for i in range(n)],
            "volume": [1000 * (i + 1) for i in range(n)],
            "adj_factor": [1.0] * n,
        }
    )
    inst = pd.DataFrame(
        {
            "stock_id": ["2330"] * n,
            "trade_date": dates,
            "foreign_buy": [100 * (i + 1) for i in range(n)],
            "trust_buy": [50 + i * 10 for i in range(n)],
            "dealer_buy": [0] * n,
        }
    )
    chips = pd.DataFrame(
        {
            "stock_id": ["2330"] * n,
            "trade_date": dates,
            "top_broker_buy": [0] * n,
            "key_broker_buy": [0] * n,
            "gov_broker_buy": [0] * n,
            "geo_broker_buy": [0] * n,
            "day_trade_volume": [500 + i * 100 for i in range(n)],
            "margin_offset_volume": [0] * n,
        }
    )
    return ETLBundle(
        stock_id="2330",
        start_date=dates[0],
        end_date=dates[-1],
        daily_bars=daily,
        institutional=inst,
        broker_chips=chips,
    )


def test_etl_bundle_merged_has_all_columns():
    bundle = _mk_etl_bundle(n=3)
    merged = bundle.merged()
    assert "foreign_buy" in merged.columns
    assert "day_trade_volume" in merged.columns
    assert len(merged) == 3


def test_etl_bundle_merged_sorts_by_trade_date():
    bundle = _mk_etl_bundle(n=5)
    merged = bundle.merged()
    assert list(merged["trade_date"]) == sorted(merged["trade_date"])


def test_etl_bundle_merged_fills_nan_flow_cols_with_zero():
    """When institutional missing some dates, merged() fills with 0."""
    dates = pd.date_range("2024-01-02", periods=3, freq="B").date
    daily = pd.DataFrame(
        {
            "stock_id": ["2330"] * 3,
            "trade_date": dates,
            "open": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
            "close": [100.5, 101.5, 102.5],
            "volume": [1000, 2000, 3000],
            "adj_factor": [1.0, 1.0, 1.0],
        }
    )
    # Institutional only covers first 2 days
    inst = pd.DataFrame(
        {
            "stock_id": ["2330"] * 2,
            "trade_date": dates[:2],
            "foreign_buy": [100, 200],
            "trust_buy": [10, 20],
            "dealer_buy": [0, 5],
        }
    )
    chips = pd.DataFrame(
        {
            "stock_id": ["2330"] * 3,
            "trade_date": dates,
            "top_broker_buy": [0] * 3,
            "key_broker_buy": [0] * 3,
            "gov_broker_buy": [0] * 3,
            "geo_broker_buy": [0] * 3,
            "day_trade_volume": [500, 600, 700],
            "margin_offset_volume": [0] * 3,
        }
    )
    bundle = ETLBundle(
        stock_id="2330",
        start_date=dates[0],
        end_date=dates[-1],
        daily_bars=daily,
        institutional=inst,
        broker_chips=chips,
    )
    merged = bundle.merged()
    # 3rd day institutional fields filled with 0
    assert merged.iloc[2]["foreign_buy"] == 0
    assert merged.iloc[2]["trust_buy"] == 0


def test_etl_bundle_arbitrary_types_allowed():
    """DataFrame is not a pydantic type — arbitrary_types_allowed flag."""
    bundle = _mk_etl_bundle(n=1)
    assert isinstance(bundle.daily_bars, pd.DataFrame)
