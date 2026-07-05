"""Re-export shim (W4.1b) — moved to ``research.adapters.run_series_store``."""
from __future__ import annotations

from backtest_platform.research.adapters.run_series_store import (
    DEFAULT_SERIES_DIR,
    read_series,
    series_path,
    write_series,
)

__all__ = [
    "DEFAULT_SERIES_DIR",
    "read_series",
    "series_path",
    "write_series",
]
