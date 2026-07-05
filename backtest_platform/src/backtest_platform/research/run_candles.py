"""Re-export shim (W4.1a) — moved to ``research.domain.run_candles``."""
from __future__ import annotations

from backtest_platform.research.domain.run_candles import (
    PARQUET_DIR,
    bars_to_candles,
    build_candles,
    derive_markers,
    load_daily_bars,
    sig_to_markers,
)

__all__ = [
    "PARQUET_DIR",
    "bars_to_candles",
    "build_candles",
    "derive_markers",
    "load_daily_bars",
    "sig_to_markers",
]
