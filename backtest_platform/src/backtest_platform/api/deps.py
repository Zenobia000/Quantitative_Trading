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
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backtest_platform.config.settings import get_settings
from backtest_platform.research.run_config import RunConfig
from backtest_platform.research.runs_store import DEFAULT_RUNS_PATH

#: A run executor takes a validated ``RunConfig`` and returns a ledger record dict.
RunExecutor = Callable[[RunConfig], dict[str, Any]]

#: Env var overriding where the runs ledger lives (defaults to ``reports/runs.jsonl``).
#: Read via ``config.settings.Settings.backtest_runs_path`` (ADR-027 Stage 2).
RUNS_PATH_ENV = "BACKTEST_RUNS_PATH"

#: Env vars overriding the觀察艙 registry / after-close marker stores (ADR-033).
#: The GUI's ``/monitor/watch`` reads both; overridable so an operator can point the
#: dashboard at a non-default ``reports/`` and tests at a tmp pair.
WATCH_REGISTRY_PATH_ENV = "WATCH_REGISTRY_PATH"
AFTER_CLOSE_MARKER_PATH_ENV = "AFTER_CLOSE_MARKER_PATH"

#: Env var overriding the per-run validation-event log (8.H.7). The Run-Report
#: verdict block reads its latest folded state; overridable so tests point at a tmp
#: JSONL and an operator at a non-default ``reports/``.
VALIDATION_EVENTS_PATH_ENV = "VALIDATION_EVENTS_PATH"

#: Env var overriding the rebuild Goal 3 evaluation ledger store. The
#: research-evaluation router reads it; overridable so tests point at a tmp
#: ``reports/`` and an operator at a non-default location.
EVALUATIONS_PATH_ENV = "EVALUATIONS_PATH"

_TWT = timezone(timedelta(hours=8))  # Taiwan is fixed UTC+8 (no DST)


def get_runs_path() -> Path:
    """Resolve the runs-ledger path (``$BACKTEST_RUNS_PATH`` or the default)."""
    configured = get_settings().backtest_runs_path
    return configured if configured is not None else DEFAULT_RUNS_PATH


def get_data_root() -> Path:
    """Root dir holding the parquet bundle caches (``data/`` by default).

    Injected so tests point ``GET /system/bundles`` at a ``tmp_path`` of synthetic
    manifests via ``app.dependency_overrides`` — no real parquet cache touched. The
    scan root itself (``bundle_registry.DEFAULT_DATA_ROOT``) is a cwd-relative path,
    the same convention every other ``data/parquet`` reference uses.
    """
    from backtest_platform.data.bundle_registry import DEFAULT_DATA_ROOT

    return DEFAULT_DATA_ROOT


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


# --------------------------------------------------------------------------- #
# 觀察艙 (Paper-Watch) reads — path / clock / calendar seams for /monitor/watch #
# --------------------------------------------------------------------------- #
def get_watch_registry_path() -> Path:
    """Resolve the觀察艙 event-log path (``$WATCH_REGISTRY_PATH`` or the default)."""
    from backtest_platform.research.watch_registry import DEFAULT_WATCH_PATH

    raw = os.environ.get(WATCH_REGISTRY_PATH_ENV)
    return Path(raw) if raw else DEFAULT_WATCH_PATH


def get_after_close_marker_path() -> Path:
    """Resolve the after-close done-marker path (``$AFTER_CLOSE_MARKER_PATH`` or default)."""
    from backtest_platform.orchestration.after_close import DEFAULT_MARKER_PATH

    raw = os.environ.get(AFTER_CLOSE_MARKER_PATH_ENV)
    return Path(raw) if raw else DEFAULT_MARKER_PATH


def get_validation_events_path() -> Path:
    """Resolve the validation-event log path (``$VALIDATION_EVENTS_PATH`` or default).

    The Run-Report verdict block folds this run's latest ``{validation_status, stage}``
    from it; injectable so tests point at a tmp JSONL without touching ``reports/``.
    """
    from backtest_platform.research.validation_store import DEFAULT_VALIDATION_PATH

    raw = os.environ.get(VALIDATION_EVENTS_PATH_ENV)
    return Path(raw) if raw else DEFAULT_VALIDATION_PATH


def get_evaluations_path() -> Path:
    """Resolve the evaluation ledger path (``$EVALUATIONS_PATH`` or the default)."""
    from backtest_platform.research.evaluation.store import DEFAULT_EVALUATIONS_PATH

    raw = os.environ.get(EVALUATIONS_PATH_ENV)
    return Path(raw) if raw else DEFAULT_EVALUATIONS_PATH


def get_watch_today() -> date:
    """Today's date in Asia/Taipei — the ``as_of`` the觀察艙 overview folds against.

    A dependency (not an inline ``date.today()``) so tests pin a fixed ``as_of`` and
    the timer-health / observed-day math stays deterministic without freezing time.
    """
    return datetime.now(_TWT).date()


def get_watch_trading_day_fn() -> Callable[[date], bool]:
    """The TWSE trading-day predicate used for observed-day + timer-stale math.

    Injectable so tests drive a plain weekday lambda (no calendar extra); production
    resolves the real ``is_taiwan_trading_day`` (XTAI if installed, weekday fallback).
    """
    from backtest_platform.runtime.trading_calendar import is_taiwan_trading_day

    return is_taiwan_trading_day
