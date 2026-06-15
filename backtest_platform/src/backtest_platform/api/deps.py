"""API dependencies — injectable runs path + run executor.

Hiding the IO-bound collaborators (the runs ledger path) and the heavy one (the
real IS executor, which pulls in the engine/zipline stack) behind FastAPI
dependencies keeps routers thin and, crucially, lets tests override them with a
temp ledger and a stub executor via ``app.dependency_overrides`` — no global
state, no real backtests in unit tests.

The executor is imported lazily inside ``get_run_executor`` so merely importing
the API (e.g. to serve ``/health``) does not drag in zipline/vectorbt.
"""
from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from backtest_platform.research.run_config import RunConfig
from backtest_platform.research.runs_store import DEFAULT_RUNS_PATH

#: A run executor takes a validated ``RunConfig`` and returns a ledger record dict.
RunExecutor = Callable[[RunConfig], dict[str, Any]]

#: Env var overriding where the runs ledger lives (defaults to ``reports/runs.jsonl``).
RUNS_PATH_ENV = "BACKTEST_RUNS_PATH"


def get_runs_path() -> Path:
    """Resolve the runs-ledger path (``$BACKTEST_RUNS_PATH`` or the default)."""
    return Path(os.environ.get(RUNS_PATH_ENV, str(DEFAULT_RUNS_PATH)))


def get_run_executor() -> RunExecutor:
    """Return the real IS executor (``run_and_judge_persist``), imported lazily.

    Tests override this dependency with a stub so triggering a run never touches
    parquet/zipline; production resolves the genuine research-loop executor. The
    persisting variant also writes the per-run equity/drawdown/trades sidecar
    (``run_series_store``) so ``GET /runs/{id}/equity`` · ``/trades`` have data
    without a second sim pass.
    """
    from backtest_platform.research.is_harness import run_and_judge_persist

    return run_and_judge_persist


def get_telemetry_reader() -> Any:
    """Return the DB-backed telemetry reader (8.H.8), imported lazily.

    Reads the daemon-produced paper/live telemetry (equity / positions) for the
    Monitor zone. Tests override this with a fake reader; monitor endpoints fall
    back to a typed-empty ``pending`` envelope when the reader fails (no DB yet),
    so the API stays up without TimescaleDB and serves real data once present.
    """
    from backtest_platform.data.db_reader import TelemetryReader

    return TelemetryReader()
