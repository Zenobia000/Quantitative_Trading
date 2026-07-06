"""API test fixtures — isolated app per test with a temp ledger + stub executor.

``create_app`` builds a fresh FastAPI instance per test, and we override the two
injected dependencies (``get_runs_path`` → a ``tmp_path`` JSONL file,
``get_run_executor`` → an in-memory stub) so no test touches the real ledger,
parquet cache, or zipline engine. Everything stays hermetic and fast.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from quant_platform.apps.api.app import create_app
from quant_platform.apps.api.deps import get_data_root, get_run_executor, get_runs_path

#: Two minimal ledger records — a v2 baseline and a v3.1b variant, both FAIL,
#: with opposite-sign nothing (same sign) so compare's sign-consistency is True.
SAMPLE_RUNS = [
    {
        "run_id": "aaa111",
        "strategy": "four_layer",
        "hypothesis": "baseline reproduce",
        "gate_status": "FAIL",
        "metrics": {"cagr": 0.05, "sharpe": 0.40, "struct1_pct": 0.50, "churn_pct": 0.30},
        "is_start": "2015-01-01",
        "is_end": "2020-12-31",
    },
    {
        "run_id": "bbb222",
        "strategy": "momentum",
        "hypothesis": "dirB strict structure",
        "gate_status": "FAIL",
        "metrics": {"cagr": 0.12, "sharpe": 0.90, "struct1_pct": 0.00, "churn_pct": 0.10},
        "is_start": "2015-01-01",
        "is_end": "2020-12-31",
    },
]


@pytest.fixture
def runs_path(tmp_path) -> Path:
    """Path to a per-test runs ledger (file may or may not exist yet)."""
    return tmp_path / "runs.jsonl"


@pytest.fixture
def data_root(tmp_path) -> Path:
    """Per-test parquet-cache scan root for ``GET /system/bundles`` (may be empty).

    Kept separate from the real ``data/`` dir so bundle tests write synthetic
    manifests here and every other API test simply sees a typed-empty bundle list.
    """
    root = tmp_path / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def sample_runs() -> list[dict]:
    """A fresh copy of the canonical two-run ledger fixture."""
    return [dict(r) for r in SAMPLE_RUNS]


@pytest.fixture
def write_runs(runs_path):
    """Callable that writes records to the ledger and returns its path."""

    def _write(records: list[dict]) -> Path:
        with runs_path.open("w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return runs_path

    return _write


@pytest.fixture
def stub_executor():
    """In-memory run executor — records its calls, returns a canned ledger record."""

    def _execute(cfg) -> dict:
        _execute.calls.append(cfg)
        return {
            "run_id": cfg.run_id,
            "strategy": cfg.strategy,
            "hypothesis": cfg.hypothesis,
            "gate_status": "INCOMPLETE",
            "gate_summary": "stub run",
            "metrics": {
                "trades": 3,
                "cagr": 0.10,
                "sharpe": 0.50,
                "struct1_pct": 0.10,
                "churn_pct": 0.10,
                "avg_hold": 7.0,
            },
            "is_start": cfg.is_start.isoformat(),
            "is_end": cfg.is_end.isoformat(),
            "stocks": list(cfg.stocks),
        }

    _execute.calls = []
    return _execute


@pytest.fixture
def client(runs_path, stub_executor, data_root) -> TestClient:
    """TestClient over a fresh app with temp-ledger + stub-executor + temp data-root."""
    app = create_app()
    app.dependency_overrides[get_runs_path] = lambda: runs_path
    app.dependency_overrides[get_run_executor] = lambda: stub_executor
    app.dependency_overrides[get_data_root] = lambda: data_root
    with TestClient(app) as test_client:
        yield test_client
