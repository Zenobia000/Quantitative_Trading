"""Re-export shim (W4.1b) — moved to ``research.adapters.validation_store``."""
from __future__ import annotations

from backtest_platform.research.adapters.validation_store import (
    DEFAULT_VALIDATION_PATH,
    current,
    history,
    record,
)

__all__ = [
    "DEFAULT_VALIDATION_PATH",
    "current",
    "history",
    "record",
]
