"""api.research_candidates — candidate pool + live-OOS queue endpoints (Goal 4)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backtest_platform.api.app import create_app
from backtest_platform.api.deps import (
    get_candidate_decisions_path,
    get_candidates_path,
    get_live_oos_queue_path,
)
from backtest_platform.research import candidate_store as cs


def _result(strategy="momentum", label="Weak", truth=None, reco="not_recommended", eval_id="eval_1"):
    return {
        "evaluation_id": eval_id, "strategy": strategy, "profile": "quick_triage",
        "verdict": {"label": label, "truth_verdict": truth, "live_oos_recommendation": reco},
        "headline_metrics": {"sharpe": 1.02, "cagr": 0.16, "dsr": 0.908, "trades": 60},
        "scorecards": [{"category": "profitability", "status": "warn"}],
        "universe": {"survivorship_clean": True},
        "report_pack_ref": "reports/research_runs/x/manifest.json",
    }


@pytest.fixture
def ctx(tmp_path):
    cp, dp, qp = tmp_path / "c.jsonl", tmp_path / "d.jsonl", tmp_path / "q.jsonl"
    sp = {"candidates_path": cp, "decisions_path": dp}
    cs.ingest_evaluation(_result(strategy="momentum", reco="not_recommended"), **sp)
    cs.ingest_evaluation(_result(strategy="inst_flow", reco="eligible", truth="PAPER_WATCH", eval_id="eval_if"), **sp)
    app = create_app()
    app.dependency_overrides[get_candidates_path] = lambda: cp
    app.dependency_overrides[get_candidate_decisions_path] = lambda: dp
    app.dependency_overrides[get_live_oos_queue_path] = lambda: qp
    return TestClient(app), sp, qp


def test_list_candidates_paginated(ctx):
    client, *_ = ctx
    r = client.get("/research/candidates")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["total"] == 2
    assert body["meta"]["data_source"] == "ledger"
    assert body["meta"]["page"] == 1


def test_list_candidates_filter_state(ctx):
    client, *_ = ctx
    r = client.get("/research/candidates", params={"strategy": "inst_flow"})
    assert len(r.json()["data"]) == 1
    assert r.json()["data"][0]["strategy"] == "inst_flow"


def test_get_candidate_with_decisions(ctx):
    client, *_ = ctx
    r = client.get("/research/candidates/cand_momentum")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["state"] == "triaged"
    assert data["decisions"][0]["action"] == "auto_label"


def test_get_candidate_404(ctx):
    client, *_ = ctx
    r = client.get("/research/candidates/cand_ghost")
    assert r.status_code == 404
    assert r.json()["error"]["detail"]["resource"] == "candidate"


def test_post_decision_keep(ctx):
    client, *_ = ctx
    r = client.post("/research/candidates/cand_momentum/decision",
                    json={"action": "keep", "label": "weak"})
    assert r.status_code == 201
    assert r.json()["data"]["to_state"] == "weak"


def test_post_decision_archive_without_reason_422(ctx):
    client, *_ = ctx
    r = client.post("/research/candidates/cand_momentum/decision", json={"action": "archive"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_post_decision_illegal_transition_400(ctx):
    client, *_ = ctx
    r = client.post("/research/candidates/cand_momentum/decision", json={"action": "unarchive"})
    assert r.status_code == 400
    assert "hint" in r.json()["error"]["detail"]


def test_post_decision_unknown_action_422(ctx):
    client, *_ = ctx
    r = client.post("/research/candidates/cand_momentum/decision", json={"action": "select_live_oos"})
    assert r.status_code == 422


def test_post_decision_unknown_candidate_404(ctx):
    client, *_ = ctx
    r = client.post("/research/candidates/cand_ghost/decision", json={"action": "keep", "label": "weak"})
    assert r.status_code == 404


def test_select_live_oos_eligible(ctx):
    client, sp, qp = ctx
    r = client.post("/research/candidates/cand_inst_flow/select-live-oos",
                    json={"observation_kind": "paper_watch_berth"})
    assert r.status_code == 201
    item = r.json()["data"]
    assert item["state"] == "queued"
    assert item["observation"]["kind"] == "paper_watch_berth"


def test_select_live_oos_not_recommended_needs_reason_422(ctx):
    client, *_ = ctx
    r = client.post("/research/candidates/cand_momentum/select-live-oos", json={})
    assert r.status_code == 422


def test_select_live_oos_override(ctx):
    client, *_ = ctx
    r = client.post("/research/candidates/cand_momentum/select-live-oos",
                    json={"reason": "manual paper look", "override": True})
    assert r.status_code == 201
    assert r.json()["data"]["override"] is True


def test_select_live_oos_blocked_409(ctx):
    client, sp, qp = ctx
    cs.ingest_evaluation(_result(strategy="reversal", reco="blocked", label="Negative", truth="REJECTED", eval_id="eval_rv"), **sp)
    r = client.post("/research/candidates/cand_reversal/select-live-oos", json={"reason": "x"})
    assert r.status_code == 409
    assert r.json()["error"]["detail"]["resource_id"] == "cand_reversal"


def test_live_oos_queue_lists_selected(ctx):
    client, *_ = ctx
    client.post("/research/candidates/cand_inst_flow/select-live-oos",
                json={"observation_kind": "paper_watch_berth"})
    r = client.get("/research/live-oos/queue")
    assert r.status_code == 200
    assert r.json()["meta"]["total"] == 1
    assert r.json()["meta"]["data_source"] == "watch_registry"
