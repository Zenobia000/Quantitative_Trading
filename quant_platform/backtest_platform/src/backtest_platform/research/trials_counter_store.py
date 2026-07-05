"""Re-export shim (W4.1b) — moved to ``research.adapters.trials_counter_store``."""
from __future__ import annotations

from backtest_platform.research.adapters.trials_counter_store import (
    DEFAULT_TRIALS_PATH,
    cumulative,
    increment,
    param_space_key,
)

__all__ = [
    "DEFAULT_TRIALS_PATH",
    "cumulative",
    "increment",
    "param_space_key",
]
