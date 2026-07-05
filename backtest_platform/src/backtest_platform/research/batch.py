"""Re-export shim (W4.1d) — moved to ``research.application.batch``."""
from __future__ import annotations

from backtest_platform.research.application.batch import (
    expand_stock_groups,
    run_batch,
)

__all__ = [
    "expand_stock_groups",
    "run_batch",
]
