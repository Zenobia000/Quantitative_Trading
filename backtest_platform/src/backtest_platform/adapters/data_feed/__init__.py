"""Data-feed seam package (ADR-035).

Exposes the :class:`DataFeed` Protocol (the stable read interface future realtime
feeds implement) and the sole concrete :class:`EODParquetFeed` (EOD parquet reader).
Design-only seam: no live feed is wired to any existing caller yet.
"""
from backtest_platform.adapters.data_feed.base import DataFeed
from backtest_platform.adapters.data_feed.eod_parquet import EODParquetFeed

__all__ = ["DataFeed", "EODParquetFeed"]
