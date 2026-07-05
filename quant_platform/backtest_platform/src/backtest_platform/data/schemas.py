"""Pydantic schemas for data layer validation.

Enforced at ETL boundaries (FinMind → parquet → TimescaleDB) per
``rules/coding-style.md`` — validate at system boundaries, never trust
external sources.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
from pydantic import BaseModel, Field, NonNegativeInt


class DailyBarRow(BaseModel):
    stock_id: str = Field(min_length=1, max_length=10)
    trade_date: date
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: NonNegativeInt
    adj_factor: float = Field(default=1.0, gt=0)


class InstitutionalRow(BaseModel):
    stock_id: str
    trade_date: date
    foreign_buy: int = 0
    trust_buy: int = 0
    dealer_buy: int = 0


class BrokerChipRow(BaseModel):
    stock_id: str
    trade_date: date
    top_broker_buy: int = 0
    key_broker_buy: int = 0
    gov_broker_buy: int = 0
    geo_broker_buy: int = 0
    day_trade_volume: NonNegativeInt = 0
    margin_offset_volume: NonNegativeInt = 0


class ETLBundle(BaseModel):
    """Result of a single stock-id ETL run, ready for write-out."""

    model_config = {"arbitrary_types_allowed": True}

    stock_id: str
    start_date: date
    end_date: date
    daily_bars: pd.DataFrame
    institutional: pd.DataFrame
    broker_chips: pd.DataFrame

    def merged(self) -> pd.DataFrame:
        """Join all three frames on trade_date for scoring-ready output."""
        merged = self.daily_bars.merge(
            self.institutional, on=["stock_id", "trade_date"], how="left"
        )
        merged = merged.merge(self.broker_chips, on=["stock_id", "trade_date"], how="left")
        # Missing chip/institutional cells default to 0 — the scoring function
        # treats absent flow as "no signal" rather than NaN propagation.
        flow_cols = [
            "foreign_buy",
            "trust_buy",
            "dealer_buy",
            "top_broker_buy",
            "key_broker_buy",
            "gov_broker_buy",
            "geo_broker_buy",
            "day_trade_volume",
            "margin_offset_volume",
        ]
        for col in flow_cols:
            if col in merged.columns:
                merged[col] = merged[col].fillna(0).astype("int64")
        return merged.sort_values("trade_date").reset_index(drop=True)
