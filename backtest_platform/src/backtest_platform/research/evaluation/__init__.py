"""High-level evaluation layer (rebuild Goal 3 / ADR-039).

A thin, contract-faithful orchestration layer ABOVE the ADR-029 workflow
primitives. Public surface:

- ``EvaluationProfile`` / ``get_profile`` / ``list_profiles`` — the four built-in
  evaluation recipes (``quick_triage`` / ``fixed_hypothesis_oos`` /
  ``grid_search_selection`` / ``deployment_strict``).
- ``evaluate`` — run a strategy under a profile → a persisted ``EvaluationResult``
  + report pack.
- ``read_evaluations`` / ``get_evaluation`` — read the append-only evaluation ledger.
"""
from backtest_platform.research.evaluation.orchestrator import evaluate
from backtest_platform.research.evaluation.profiles import (
    EvaluationProfile,
    get_profile,
    list_profile_names,
    list_profiles,
)
from backtest_platform.research.evaluation.store import (
    get_evaluation,
    read_evaluations,
)

__all__ = [
    "EvaluationProfile",
    "evaluate",
    "get_evaluation",
    "get_profile",
    "list_profile_names",
    "list_profiles",
    "read_evaluations",
]
