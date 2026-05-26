"""Tests for FinMind ETL with a stub loader (no network)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from backtest_platform.data.finmind_etl import fetch_bundle, write_parquet
from backtest_platform.data.schemas import ETLBundle


class StubLoader:
    """Mimics FinMind DataLoader for offline tests."""

    def taiwan_stock_daily(self, stock_id: str, start_date: str, end_date: str) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "date": ["2024-01-02", "2024-01-03"],
                "stock_id": [stock_id, stock_id],
                "open": [100.0, 101.0],
                "max": [102.0, 103.0],
                "min": [99.5, 100.5],
                "close": [101.5, 102.5],
                "Trading_Volume": [5000, 6000],
            }
        )

    def taiwan_stock_institutional_investors(
        self, stock_id: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "date": ["2024-01-02", "2024-01-02", "2024-01-03"],
                "stock_id": [stock_id] * 3,
                "name": ["Foreign_Investor", "Investment_Trust", "Foreign_Investor"],
                "buy": [1000, 500, 800],
                "sell": [600, 200, 1000],
            }
        )

    def taiwan_stock_day_trading(
        self, stock_id: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        # Real FinMind schema: date, stock_id, BuyAfterSale, Volume, BuyAmount, SellAmount
        return pd.DataFrame(
            {
                "stock_id": [stock_id, stock_id],
                "date": ["2024-01-02", "2024-01-03"],
                "BuyAfterSale": ["", ""],
                "Volume": [200, 250],
                "BuyAmount": [20000, 25000],
                "SellAmount": [20100, 25050],
            }
        )

    def taiwan_stock_dividend(
        self, stock_id: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        # No dividends in test range
        return pd.DataFrame()


def test_fetch_bundle_with_stub_loader_returns_valid_bundle() -> None:
    bundle = fetch_bundle(
        stock_id="2330",
        start=date(2024, 1, 1),
        end=date(2024, 1, 31),
        loader=StubLoader(),
        rate_limit_seconds=0,
    )
    assert isinstance(bundle, ETLBundle)
    assert bundle.stock_id == "2330"
    assert len(bundle.daily_bars) == 2
    assert len(bundle.institutional) == 2
    assert len(bundle.broker_chips) == 2


def test_institutional_pivot_computes_net_correctly() -> None:
    bundle = fetch_bundle(
        stock_id="2330",
        start=date(2024, 1, 1),
        end=date(2024, 1, 31),
        loader=StubLoader(),
        rate_limit_seconds=0,
    )
    inst = bundle.institutional.set_index("trade_date")
    # 2024-01-02: foreign 1000-600=400, trust 500-200=300
    assert inst.loc[date(2024, 1, 2), "foreign_buy"] == 400
    assert inst.loc[date(2024, 1, 2), "trust_buy"] == 300
    # 2024-01-03: foreign 800-1000=-200, trust absent → 0
    assert inst.loc[date(2024, 1, 3), "foreign_buy"] == -200
    assert inst.loc[date(2024, 1, 3), "trust_buy"] == 0


def test_merged_bundle_has_all_required_columns() -> None:
    """merged() output must satisfy compute_scores REQUIRED_COLUMNS."""
    from backtest_platform.strategy.scoring import REQUIRED_COLUMNS

    bundle = fetch_bundle(
        stock_id="2330",
        start=date(2024, 1, 1),
        end=date(2024, 1, 31),
        loader=StubLoader(),
        rate_limit_seconds=0,
    )
    merged = bundle.merged()
    missing = [c for c in REQUIRED_COLUMNS if c not in merged.columns]
    assert missing == [], f"merged bundle missing: {missing}"


def test_write_parquet_creates_three_files(tmp_path: Path) -> None:
    bundle = fetch_bundle(
        stock_id="2330",
        start=date(2024, 1, 1),
        end=date(2024, 1, 31),
        loader=StubLoader(),
        rate_limit_seconds=0,
    )
    paths = write_parquet(bundle, tmp_path / "out")
    assert paths["daily_bars"].exists()
    assert paths["institutional"].exists()
    assert paths["broker_chips"].exists()
    roundtrip = pd.read_parquet(paths["daily_bars"])
    assert len(roundtrip) == 2
