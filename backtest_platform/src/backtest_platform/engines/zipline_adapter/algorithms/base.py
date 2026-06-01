"""Shared utilities for zipline algorithms (ADR-013, plan v3.0 §4.2).

The core problem: zipline's `data.history()` only returns OHLCV from the
bundle, but M1 `compute_scores`/`compute_signals` require 14 columns
including institutional flows + broker chips + day-trading volume.

Solution: preload merged ETLBundles from parquet cache at `initialize()` time,
index by (symbol, date) into in-memory dict-of-DataFrames. Per-bar lookup is
O(1) dict + O(rolling_window) DataFrame slice.

This is faster than per-bar parquet reads and avoids cluttering the zipline
bundle schema with non-OHLCV columns (bundle storage is bcolz-optimized
for daily bars only).
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
from loguru import logger

from backtest_platform.engines.zipline_adapter.bundles.parquet_cache import (
    ParquetCache,
)


def preload_merged_frames(
    symbols: list[str],
    cache_dir: Path | None = None,
) -> dict[str, pd.DataFrame]:
    """Load M1 ETLBundle.merged() frames for all symbols upfront.

    Returns dict[symbol → DataFrame] where each frame is indexed by
    trade_date (DatetimeIndex) and has REQUIRED_COLUMNS for scoring.

    Raises FileNotFoundError if any symbol's cache is missing — caller
    should ensure `zipline ingest -b finmind` ran first.
    """
    cache_dir = cache_dir or Path("data/parquet")
    cache = ParquetCache(root=cache_dir)
    out: dict[str, pd.DataFrame] = {}

    for sym in symbols:
        if not cache.exists(sym):
            raise FileNotFoundError(
                f"parquet cache miss for {sym}; run `zipline ingest -b finmind` "
                f"with UNIVERSE_FINMIND including {sym}"
            )
        bundle = cache.load(sym)
        merged = bundle.merged()
        merged["trade_date"] = pd.to_datetime(merged["trade_date"])
        merged = merged.set_index("trade_date").sort_index()
        out[sym] = merged
        logger.debug("preloaded {} ({} rows)", sym, len(merged))

    return out


def get_history_window(
    merged_frame: pd.DataFrame,
    as_of: pd.Timestamp,
    bar_count: int,
) -> pd.DataFrame:
    """Return the `bar_count` rows ending at `as_of` (inclusive).

    Used by algorithms to feed `compute_scores` the rolling window it needs.
    `as_of` should be the current trading day (zipline `data.current_dt`).
    """
    # Normalize timezone (zipline gives tz-aware, our frame is naive)
    as_of_naive = as_of.tz_localize(None) if as_of.tz else as_of
    # Find all rows <= as_of, take last `bar_count`
    window = merged_frame.loc[merged_frame.index <= as_of_naive].tail(bar_count)
    return window


def as_of_to_date(as_of: pd.Timestamp) -> date:
    """Convert zipline timestamp to python date (M1 functions expect date)."""
    return (as_of.tz_localize(None) if as_of.tz else as_of).date()
