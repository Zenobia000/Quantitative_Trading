"""DataFeed seam (ADR-035) — the stable interface future realtime lands behind.

This is a *seam*, deliberately small: a structural :class:`DataFeed` Protocol that
declares only what a consumer needs to read price bars, plus a ``supports_realtime``
capability flag so a caller can branch (batch after-close vs streaming) without
importing a concrete feed. No live feed is implemented here — the only concrete
implementation today is the EOD parquet reader (``eod_parquet.EODParquetFeed``).
When XQ signals / Q broker quotes are integrated (criteria in ADR-035), they slot in
as new implementers of THIS protocol; no existing caller has to change.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class DataFeed(Protocol):
    """Read-side contract for daily bars + latest prices (a market-data source).

    ``supports_realtime`` is a capability flag, not a promise of freshness: the EOD
    parquet feed sets it ``False`` (after-close batch is the current operating mode);
    a future streaming feed would set it ``True``.
    """

    #: Whether this feed can serve intraday / streaming quotes (vs EOD batch only).
    supports_realtime: bool

    def get_daily_bars(
        self, symbols: Sequence[str], start: date, end: date
    ) -> pd.DataFrame:
        """Daily OHLCV bars for ``symbols`` over the inclusive ``[start, end]`` window.

        Returns a long-format frame (one row per symbol-day); symbols with no data in
        range are simply absent. Empty (no matches) → an empty frame, never an error.
        """
        ...

    def get_latest_prices(self, symbols: Sequence[str]) -> dict[str, float]:
        """Most-recent close per symbol (``{symbol: close}``); missing symbols omitted."""
        ...
