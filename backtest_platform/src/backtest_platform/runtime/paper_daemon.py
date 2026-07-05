"""Re-export shim (W5.1c) — moved to ``services.strategy_runtime.paper_daemon``."""
from backtest_platform.services.strategy_runtime.paper_daemon import (
    ReplayStep,
    ReplaySummary,
    replay_schedule,
    run_paper_replay,
)

__all__ = [
    "ReplayStep",
    "ReplaySummary",
    "replay_schedule",
    "run_paper_replay",
]
