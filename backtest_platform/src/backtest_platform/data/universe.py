"""Universe filter — v2.md 2.2.

Pure-function design: caller assembles a metadata DataFrame for the candidate
pool (from FinMind ``taiwan_stock_info`` + price history + governance data),
passes it to :func:`apply_filters`, and gets back the surviving stock IDs.

M1 skeleton: filter logic complete; data assembly pipeline (M2) will feed
real metadata. Industry concentration and "1 financial stock" limits are
NOT applied here — those are portfolio-level rules enforced at signal time
(see v2.md 3.2.3), not universe membership.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

UNIVERSE_METADATA_COLUMNS: tuple[str, ...] = (
    "stock_id",
    "market",  # 'TWSE' (上市) or 'TPEX' (上櫃)
    "market_cap",  # NTD
    "listed_date",  # date
    "industry",
    "avg_volume_60",  # lots (張)
    "avg_amount_60",  # NTD
    "current_price",
    "is_etf",
    "is_warrant",
    "is_convertible",
    "is_attention",  # 處置股
    "is_full_delivery",  # 全額交割
    "governance_grade",  # 'A++', 'A+', 'A', 'B', 'C', 'CC', 'D' (None = unrated)
    "days_since_ex_dividend",  # int or None
    "days_until_ex_dividend",  # int or None
)


@dataclass(frozen=True, slots=True)
class UniverseConfig:
    """Thresholds for v2.md 2.2 universe filtering."""

    min_market_cap: float = 5e9
    min_listed_days: int = 365
    min_avg_volume_lots: int = 1000
    min_avg_amount: float = 3e7
    min_price: float = 10.0
    max_price: float = 500.0
    exclude_governance_grades: tuple[str, ...] = ("D",)
    ex_dividend_quiet_days: int = 30

    @classmethod
    def default(cls) -> UniverseConfig:
        return cls()


def apply_filters(
    metadata: pd.DataFrame,
    config: UniverseConfig | None = None,
    snapshot_date: date | None = None,
) -> pd.DataFrame:
    """Return the subset of ``metadata`` that passes all v2.md 2.2 filters.

    Adds a column ``excluded_reason`` to the FULL frame (caller can inspect
    rejections); returns only rows where ``excluded_reason`` is empty.
    """
    config = config or UniverseConfig.default()
    snapshot_date = snapshot_date or date.today()
    _validate_metadata(metadata)

    out = metadata.copy()
    out["excluded_reason"] = ""

    def _reject(mask: pd.Series, reason: str) -> None:
        # First reason wins so we can tell which gate actually killed the stock.
        keep_existing = out["excluded_reason"] != ""
        out.loc[mask & ~keep_existing, "excluded_reason"] = reason

    # Listing type
    _reject(out["is_etf"].astype(bool), "etf")
    _reject(out["is_warrant"].astype(bool), "warrant")
    _reject(out["is_convertible"].astype(bool), "convertible_bond")
    _reject(out["is_attention"].astype(bool), "attention_stock")
    _reject(out["is_full_delivery"].astype(bool), "full_delivery")

    # Market: only 上市 / 上櫃
    _reject(~out["market"].isin({"TWSE", "TPEX"}), "wrong_market")

    # Capital / liquidity
    _reject(out["market_cap"] < config.min_market_cap, "market_cap_too_low")
    _reject(out["avg_volume_60"] < config.min_avg_volume_lots, "volume_too_low")
    _reject(out["avg_amount_60"] < config.min_avg_amount, "amount_too_low")
    _reject(out["current_price"] < config.min_price, "price_below_floor")
    _reject(out["current_price"] > config.max_price, "price_above_cap")

    # Listed time
    listing_cutoff = snapshot_date - timedelta(days=config.min_listed_days)
    listed_dates = pd.to_datetime(out["listed_date"]).dt.date
    _reject(listed_dates > listing_cutoff, "newly_listed")

    # Governance grade
    bad_grades = set(config.exclude_governance_grades)
    _reject(out["governance_grade"].isin(bad_grades), "bad_governance")

    # Ex-dividend quiet period — recent and imminent both excluded
    quiet = config.ex_dividend_quiet_days
    recent = out["days_since_ex_dividend"].fillna(quiet + 1).astype(int) < quiet
    upcoming = out["days_until_ex_dividend"].fillna(quiet + 1).astype(int) < quiet
    _reject(recent | upcoming, "ex_dividend_quiet")

    return out


def survivors(filtered: pd.DataFrame) -> pd.DataFrame:
    """Return rows that passed all filters (excluded_reason == '')."""
    return filtered[filtered["excluded_reason"] == ""].reset_index(drop=True)


def rejection_summary(filtered: pd.DataFrame) -> pd.Series:
    """Counts by rejection reason — useful for diagnosing why the pool is small."""
    return filtered["excluded_reason"].value_counts().drop("", errors="ignore")


def _validate_metadata(df: pd.DataFrame) -> None:
    missing = [c for c in UNIVERSE_METADATA_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"universe metadata missing columns: {missing}")
