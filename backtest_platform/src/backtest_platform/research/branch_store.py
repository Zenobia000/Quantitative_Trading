"""Re-export shim (W4.1b) — moved to ``research.adapters.branch_store``."""
from __future__ import annotations

from backtest_platform.research.adapters.branch_store import (
    BRANCH_ORIGINS,
    DEFAULT_BRANCHES_PATH,
    EXECUTION_OVERLAY_KNOBS,
    BranchNotEvaluableError,
    BranchNotFoundError,
    IllegalDeltaError,
    ParentNotFoundError,
    apply_config_delta,
    classify_delta,
    compare_branch,
    config_keys,
    create_branch,
    evaluate_branch,
    get_branch,
    list_branches,
)

__all__ = [
    "BRANCH_ORIGINS",
    "DEFAULT_BRANCHES_PATH",
    "EXECUTION_OVERLAY_KNOBS",
    "BranchNotEvaluableError",
    "BranchNotFoundError",
    "IllegalDeltaError",
    "ParentNotFoundError",
    "apply_config_delta",
    "classify_delta",
    "compare_branch",
    "config_keys",
    "create_branch",
    "evaluate_branch",
    "get_branch",
    "list_branches",
]
