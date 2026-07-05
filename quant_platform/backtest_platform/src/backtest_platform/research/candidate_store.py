"""Re-export shim (W4.1b) — moved to ``research.adapters.candidate_store``."""
from __future__ import annotations

from backtest_platform.research.adapters.candidate_store import (
    DEFAULT_CANDIDATES_PATH,
    DEFAULT_DECISIONS_PATH,
    BlockedSelectionError,
    CandidateNotFoundError,
    EnqueuePort,
    MissingReasonError,
    candidate_id_for,
    get_candidate,
    ingest_evaluation,
    list_candidates,
    record_decision,
    select_live_oos,
)

__all__ = [
    "DEFAULT_CANDIDATES_PATH",
    "DEFAULT_DECISIONS_PATH",
    "BlockedSelectionError",
    "CandidateNotFoundError",
    "EnqueuePort",
    "MissingReasonError",
    "candidate_id_for",
    "get_candidate",
    "ingest_evaluation",
    "list_candidates",
    "record_decision",
    "select_live_oos",
]
