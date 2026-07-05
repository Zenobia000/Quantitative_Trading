"""Re-export shim (W4.1d) — moved to ``research.application.is_harness``."""
from __future__ import annotations

from backtest_platform.research.application import is_harness as _is_harness
from backtest_platform.research.application.is_harness import (
    PARQUET_DIR,
    TRADING_DAYS,
    equity_drawdown,
    load_merged_parquet,
    run_and_judge,
    run_and_judge_persist,
    run_and_judge_with_returns,
    run_is,
    run_is_returns,
    run_is_trades,
)

# Back-compat private helpers (ADR-027): ``research.application.sweep`` imports
# these four-layer sim helpers from here by their private names. Alias via
# assignment (not ``import ... as``) so the linter cannot strip them as unused.
_SLIP_STRESS = _is_harness._SLIP_STRESS
_daily_returns = _is_harness._daily_returns
_metrics = _is_harness._metrics
_signaled_window = _is_harness._signaled_window
_trades = _is_harness._trades

__all__ = [
    "PARQUET_DIR",
    "TRADING_DAYS",
    "equity_drawdown",
    "load_merged_parquet",
    "run_and_judge",
    "run_and_judge_persist",
    "run_and_judge_with_returns",
    "run_is",
    "run_is_returns",
    "run_is_trades",
]
