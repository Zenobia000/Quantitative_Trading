"""api.research_evaluation — /research/profiles + /research/evaluations (Goal 3)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backtest_platform.api.app import create_app
from backtest_platform.api.deps import get_evaluations_path
from backtest_platform.research.evaluation.report_pack import write_report_pack
from backtest_platform.research.evaluation.store import append_evaluation


def _min_result(evaluation_id="eval_demo", run_id="rid123"):
    return {
        "schema_version": "1.0", "evaluation_id": evaluation_id, "run_id": run_id,
        "strategy": "momentum", "profile": "quick_triage", "profile_version": "1.0",
        "created_at": "2026-07-03T00:00:00+08:00",
        "verdict": {"label": "Weak", "truth_verdict": None, "live_oos_recommendation": "not_recommended",
                    "recommendation": {"action": "needs_more_research", "confidence": "medium", "reasons": []}},
        "headline_metrics": {"sharpe": 1.0, "cagr": 0.1}, "scorecards": [],
        "checks": [], "report_pack": "scorecard_pack",
        "report_pack_ref": None,
    }


@pytest.fixture
def client(tmp_path):
    ev_path = tmp_path / "ev.jsonl"
    result = _min_result()
    manifest = write_report_pack(result, {"equity": [1.0, 1.01]}, root=tmp_path / "packs")
    result["report_pack_ref"] = manifest["root_dir"] + "/manifest.json"
    append_evaluation(result, ev_path)
    app = create_app()
    app.dependency_overrides[get_evaluations_path] = lambda: ev_path
    return TestClient(app)


def test_list_profiles(client):
    r = client.get("/research/profiles")
    assert r.status_code == 200
    names = [p["name"] for p in r.json()["data"]]
    assert names == ["quick_triage", "fixed_hypothesis_oos", "grid_search_selection", "deployment_strict"]


def test_get_profile(client):
    r = client.get("/research/profiles/deployment_strict")
    assert r.status_code == 200
    assert r.json()["data"]["wraps_primitives"] == ["truth_gate"]


def test_get_profile_unknown_404(client):
    r = client.get("/research/profiles/ghost")
    assert r.status_code == 404
    body = r.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["detail"]["resource"] == "profile"


def test_get_evaluation(client):
    r = client.get("/research/evaluations/eval_demo")
    assert r.status_code == 200
    assert r.json()["data"]["run_id"] == "rid123"
    assert r.json()["meta"]["data_source"] == "ledger"


def test_get_evaluation_404(client):
    r = client.get("/research/evaluations/nope")
    assert r.status_code == 404
    assert r.json()["error"]["detail"]["resource"] == "evaluation"


def test_get_evaluation_report_manifest(client):
    r = client.get("/research/evaluations/eval_demo/report")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["run_id"] == "rid123"
    names = {f["name"] for f in data["files"]}
    assert {"summary.json", "scorecards.json", "report.md"} <= names
