"""Re-export shim (W4.1a) — moved to ``research.domain.compare``."""
from __future__ import annotations

from backtest_platform.research.domain.compare import (
    DEFAULT_METRIC_KEYS,
    LOWER_IS_BETTER,
    CompareReport,
    RunComparison,
    compare_runs,
    rank_by,
)

__all__ = [
    "DEFAULT_METRIC_KEYS",
    "LOWER_IS_BETTER",
    "CompareReport",
    "RunComparison",
    "compare_runs",
    "rank_by",
]
