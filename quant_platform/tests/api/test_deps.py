"""``api.deps`` — the real (non-overridden) dependency resolvers.

The ``client`` fixture overrides these, so cover the production code paths here
directly: env-driven ledger path resolution + lazy executor import.
"""
from __future__ import annotations

from quant_platform.apps.api.deps import (
    RUNS_PATH_ENV,
    get_run_executor,
    get_runs_path,
)
from quant_platform.packages.adapters.runs_store import DEFAULT_RUNS_PATH


def test_get_runs_path_defaults_to_ledger(monkeypatch):
    monkeypatch.delenv(RUNS_PATH_ENV, raising=False)
    assert get_runs_path() == DEFAULT_RUNS_PATH


def test_get_runs_path_honours_env(monkeypatch, tmp_path):
    target = tmp_path / "custom_runs.jsonl"
    monkeypatch.setenv(RUNS_PATH_ENV, str(target))
    assert get_runs_path() == target


def test_get_run_executor_returns_real_runner():
    from quant_platform.packages.application.is_harness import run_and_judge_persist

    assert get_run_executor() is run_and_judge_persist
