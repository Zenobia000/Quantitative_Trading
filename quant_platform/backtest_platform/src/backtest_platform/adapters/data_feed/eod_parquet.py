"""EOD parquet feed — the only concrete :class:`DataFeed` today (ADR-035).

A thin adapter over the existing parquet cache reader
(``data.parquet_cache.ParquetCache``): it delegates all
IO to that reader and just reshapes the per-symbol bundles into the DataFeed's
window/latest views. It rewires nothing — it exists so future realtime feeds land
behind a stable interface. ``supports_realtime`` is ``False``: EOD after-close batch
is the operating mode.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from pathlib import Path

import pandas as pd

from backtest_platform.data.parquet_cache import ParquetCache


class EODParquetFeed:
    """Serve daily bars + latest prices from an on-disk parquet cache."""

    #: EOD batch source — no intraday/streaming quotes.
    supports_realtime: bool = False

    def __init__(self, cache_root: Path | str, cache: ParquetCache | None = None) -> None:
        self._cache = cache or ParquetCache(Path(cache_root))

    def get_daily_bars(
        self, symbols: Sequence[str], start: date, end: date
    ) -> pd.DataFrame:
        lo, hi = pd.Timestamp(start), pd.Timestamp(end)
        frames: list[pd.DataFrame] = []
        for sid in symbols:
            bundle = self._cache.load_or_none(sid)
            if bundle is None:
                continue
            bars = bundle.daily_bars
            td = pd.to_datetime(bars["trade_date"])
            window = bars.loc[(td >= lo) & (td <= hi)]
            if not window.empty:
                frames.append(window)
        if not frames:
            return pd.DataFrame()
        return (
            pd.concat(frames, ignore_index=True)
            .sort_values(["stock_id", "trade_date"])
            .reset_index(drop=True)
        )

    def get_latest_prices(self, symbols: Sequence[str]) -> dict[str, float]:
        prices: dict[str, float] = {}
        for sid in symbols:
            bundle = self._cache.load_or_none(sid)
            if bundle is None or bundle.daily_bars.empty:
                continue
            last = bundle.daily_bars.sort_values("trade_date").iloc[-1]
            prices[sid] = float(last["close"])
        return prices
