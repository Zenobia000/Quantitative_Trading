"""Data-feed seam package (ADR-035).

Exposes the :class:`DataFeed` Protocol (the stable read interface future realtime
feeds implement) and the sole concrete :class:`EODParquetFeed` (EOD parquet reader).
Design-only seam: no live feed is wired to any existing caller yet.
"""
from quant_platform.packages.adapters.data_feed.base import DataFeed
from quant_platform.packages.adapters.data_feed.eod_parquet import EODParquetFeed

__all__ = ["DataFeed", "EODParquetFeed"]
