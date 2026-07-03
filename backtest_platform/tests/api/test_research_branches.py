"""api.research_branches — branch experiment endpoints (Goal 9).

Seeds a real parent evaluation via the synthetic loader, then drives create / list /
get / evaluate / compare through the envelope. The evaluate dependency is overridden
with a synthetic-loader evaluator so no parquet/engine is touched.
"""
from __future__ import annotations

import functools
from datetime import date

import pytest
from fastapi.testclient import TestClient

from backtest_platform.api.app import create_app
from backtest_platform.api.deps import (
    get_branch_evaluator,
    get_branches_path,
    get_evaluations_path,
)
from backtest_platform.research import branch_store as bs
from backtest_platform.research.evaluation import evaluate
from backtest_platform.strategies.conformance import synthetic_loader

_SYMS = [f"SYN{i:04d}" for i in range(6)]


@pytest.fixture
def ctx(tmp_path):
    ev, br, packs = tmp_path / "ev.jsonl", tmp_path / "br.jsonl", tmp_path / "packs"
    parent = evaluate(
        "momentum", "quick_triage", loader=synthetic_loader(n_bars=500),
        symbols=_SYMS, is_start=date(2019, 1, 1), is_end=date(2020, 12, 31),
        evaluations_path=ev, pack_root=packs,
    )
    # Evaluator stub: real branch_store.evaluate_branch but with a synthetic loader
    # + no candidate ingest (keeps the API test engine-free and store-isolated).
    stub_eval = functools.partial(
        bs.evaluate_branch, loader=synthetic_loader(n_bars=500), pack_root=packs, ingest=False,
    )
    app = create_app()
    app.dependency_overrides[get_branches_path] = lambda: br
    app.dependency_overrides[get_evaluations_path] = lambda: ev
    app.dependency_overrides[get_branch_evaluator] = lambda: stub_eval
    return TestClient(app), parent


def _create(client, parent, delta, **body):
    return client.post(
        "/research/branches",
        json={"parent_evaluation_id": parent["evaluation_id"], "config_delta": delta, **body},
    )


def test_create_branch_201(ctx):
    client, parent = ctx
    r = _create(client, parent, [{"key": "lookback_days", "to": 90}])
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["parent_evaluation_id"] == parent["evaluation_id"]
    assert data["status"] == "draft"
    assert data["applies_to_rerun"] is True


def test_create_branch_unknown_parent_404(ctx):
    client, _ = ctx
    r = client.post(
        "/research/branches",
        json={"parent_evaluation_id": "eval_ghost", "config_delta": [{"key": "lookback_days", "to": 90}]},
    )
    assert r.status_code == 404
    assert r.json()["error"]["detail"]["resource"] == "evaluation"


def test_create_branch_illegal_key_422(ctx):
    client, parent = ctx
    r = _create(client, parent, [{"key": "not_a_field", "to": 1}])
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_branch_empty_delta_422(ctx):
    client, parent = ctx
    r = _create(client, parent, [])
    assert r.status_code == 422  # Pydantic min_length=1


def test_list_branches_filter(ctx):
    client, parent = ctx
    _create(client, parent, [{"key": "lookback_days", "to": 90}])
    r = client.get("/research/branches", params={"strategy": "momentum"})
    assert r.status_code == 200
    assert r.json()["meta"]["total"] == 1
    assert r.json()["meta"]["data_source"] == "ledger"


def test_get_branch_and_404(ctx):
    client, parent = ctx
    bid = _create(client, parent, [{"key": "lookback_days", "to": 90}]).json()["data"]["branch_id"]
    assert client.get(f"/research/branches/{bid}").status_code == 200
    r = client.get("/research/branches/branch_ghost")
    assert r.status_code == 404
    assert r.json()["error"]["detail"]["resource"] == "branch"


def test_evaluate_branch_backfills(ctx):
    client, parent = ctx
    bid = _create(client, parent, [{"key": "lookback_days", "to": 90}]).json()["data"]["branch_id"]
    r = client.post(f"/research/branches/{bid}/evaluate")
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["status"] == "evaluated"
    assert data["evaluation_id"] and data["evaluation_id"] != parent["evaluation_id"]


def test_evaluate_overlay_only_branch_409(ctx):
    client, parent = ctx
    bid = _create(
        client, parent, [{"key": "slippage_bps", "to": 10}], origin="simulation",
    ).json()["data"]["branch_id"]
    r = client.post(f"/research/branches/{bid}/evaluate")
    assert r.status_code == 409
    assert r.json()["error"]["detail"]["resource_id"] == bid


def test_evaluate_unknown_branch_404(ctx):
    client, _ = ctx
    assert client.post("/research/branches/branch_ghost/evaluate").status_code == 404


def test_compare_branch_delta_table(ctx):
    client, parent = ctx
    bid = _create(client, parent, [{"key": "lookback_days", "to": 90}]).json()["data"]["branch_id"]
    client.post(f"/research/branches/{bid}/evaluate")
    r = client.get(f"/research/branches/{bid}/compare")
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["branch_evaluated"] is True
    assert {row["metric"] for row in body["metrics"]} >= {"sharpe", "cagr", "max_drawdown"}
    assert body["decision"]["verdict"] in {"branch_better", "parent_better", "inconclusive"}


def test_compare_before_evaluate_prompts(ctx):
    client, parent = ctx
    bid = _create(client, parent, [{"key": "lookback_days", "to": 90}]).json()["data"]["branch_id"]
    body = client.get(f"/research/branches/{bid}/compare").json()["data"]
    assert body["branch_evaluated"] is False
    assert body["decision"] is None


def test_compare_unknown_branch_404(ctx):
    client, _ = ctx
    assert client.get("/research/branches/branch_ghost/compare").status_code == 404
