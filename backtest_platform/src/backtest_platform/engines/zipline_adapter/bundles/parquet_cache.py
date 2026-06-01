"""Parquet cache reader for FinMind ETL bundles (M1 既有 write_parquet 的反向).

The bundle ingester reads from parquet first, only hitting FinMind API when
cache miss. This is the main mitigation for FinMind 600 req/hr rate limit
(plan v3.0 R2): 100 stocks × 7 years would need 2100 API calls if naive;
with parquet cache + day-incremental, drops to ~7 calls/day.

Layout (matches `data/finmind_etl.py:write_parquet`):
    data/parquet/
        daily_bars__<stock_id>.parquet
        institutional__<stock_id>.parquet
        broker_chips__<stock_id>.parquet
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from backtest_platform.data.schemas import ETLBundle


@dataclass(slots=True, frozen=True)
class ParquetCache:
    """Read-side companion to `data/finmind_etl.write_parquet`."""

    root: Path

    def exists(self, stock_id: str) -> bool:
        """All three tables must be present to consider cache valid."""
        return all(
            (self.root / f"{table}__{stock_id}.parquet").exists()
            for table in ("daily_bars", "institutional", "broker_chips")
        )

    def load(self, stock_id: str) -> ETLBundle:
        """Read three parquet files into an ETLBundle.

        Caller must check `exists()` first; missing files raise FileNotFoundError.
        Date range is inferred from the daily_bars frame, not the filename.
        """
        daily = pd.read_parquet(self.root / f"daily_bars__{stock_id}.parquet")
        inst = pd.read_parquet(self.root / f"institutional__{stock_id}.parquet")
        chips = pd.read_parquet(self.root / f"broker_chips__{stock_id}.parquet")

        if daily.empty:
            raise ValueError(f"daily_bars__{stock_id}.parquet is empty")

        start = pd.to_datetime(daily["trade_date"].min()).date()
        end = pd.to_datetime(daily["trade_date"].max()).date()
        return ETLBundle(
            stock_id=stock_id,
            start_date=start,
            end_date=end,
            daily_bars=daily,
            institutional=inst,
            broker_chips=chips,
        )

    def load_or_none(self, stock_id: str) -> ETLBundle | None:
        """Convenience: return None on cache miss instead of raising."""
        return self.load(stock_id) if self.exists(stock_id) else None


def cached_or_fetch(
    stock_id: str,
    start: date,
    end: date,
    cache: ParquetCache,
    fetch_fn=None,  # callable matching `fetch_bundle` signature; default = M1 ETL
) -> ETLBundle:
    """Return cached bundle if covers requested range, else fetch + persist.

    Range check is inclusive on both ends; a cache hit requires
    `cached.start_date <= start <= end <= cached.end_date`.
    """
    cached = cache.load_or_none(stock_id)
    if cached and cached.start_date <= start and end <= cached.end_date:
        return cached

    if fetch_fn is None:
        from backtest_platform.data.finmind_etl import fetch_bundle as fetch_fn

    bundle = fetch_fn(stock_id, start, end)

    from backtest_platform.data.finmind_etl import write_parquet

    write_parquet(bundle, cache.root)
    return bundle
