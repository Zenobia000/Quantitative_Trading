"""Re-export shim (W4.1d) — moved to ``research.application.sweep``."""
from __future__ import annotations

from backtest_platform.research.application.sweep import (
    expand_grid,
    run_sweep,
    to_heatmap,
)

__all__ = [
    "expand_grid",
    "run_sweep",
    "to_heatmap",
]
