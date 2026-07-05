"""Re-export shim (W4.1d) — moved to ``research.application.loader``."""
from __future__ import annotations

from backtest_platform.research.application.loader import (
    get_doe_config,
    get_go_gates_config,
    get_paper_replay_config,
    get_truth_gate_config,
    get_universe_config,
    list_workflow_configs,
    load_research_config,
)

__all__ = [
    "get_doe_config",
    "get_go_gates_config",
    "get_paper_replay_config",
    "get_truth_gate_config",
    "get_universe_config",
    "list_workflow_configs",
    "load_research_config",
]
