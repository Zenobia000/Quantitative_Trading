"""Re-export shim (W4.1b) — moved to ``research.adapters.finlab_universe``."""
from __future__ import annotations

from backtest_platform.research.adapters.finlab_universe import (
    cached_universe_symbols,
    select_survivorship_universe,
)

__all__ = [
    "cached_universe_symbols",
    "select_survivorship_universe",
]
