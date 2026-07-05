"""Re-export shim (W4.1b) — moved to ``research.adapters.runs_store``."""
from __future__ import annotations

from backtest_platform.research.adapters.runs_store import (
    DEFAULT_RUNS_PATH,
    append_run,
    read_runs,
)

__all__ = [
    "DEFAULT_RUNS_PATH",
    "append_run",
    "read_runs",
]
