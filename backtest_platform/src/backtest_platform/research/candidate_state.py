"""Re-export shim (W4.1a) — moved to ``research.domain.candidate_state``."""
from __future__ import annotations

from backtest_platform.research.domain.candidate_state import (
    ACTIONS,
    DECISION_ACTIONS,
    KEEP_LABELS,
    STATES,
    IllegalTransitionError,
    next_state,
    reason_required,
)

__all__ = [
    "ACTIONS",
    "DECISION_ACTIONS",
    "KEEP_LABELS",
    "STATES",
    "IllegalTransitionError",
    "next_state",
    "reason_required",
]
