"""S3 endpoints — /research/validate/{id}/gate-state, /research/promote/{id} (+audit).

Isolated by pointing the stores' module-level DEFAULT paths at tmp_path.
"""
from __future__ import annotations

import pytest

from backtest_platform.research import promotion_service, promotion_store, validation_store


@pytest.fixture
def isolate_stores(tmp_path, monkeypatch):
    monkeypatch.setattr(validation_store, "DEFAULT_VALIDATION_PATH", tmp_path / "val.jsonl")
    monkeypatch.setattr(promotion_store, "DEFAULT_PROMOTION_PATH", tmp_path / "promo.jsonl")


def test_gate_state_empty_then_recorded(client, isolate_stores):
    body = client.get("/research/validate/r1/gate-state").json()
    assert body["success"] is True
    assert body["data"]["validation_status"] is None
    # drive a transition through the service (same default path)
    promotion_service.record_is_result(
        "r1",
        {"cagr": 0.25, "sharpe": 1.3, "slippage_sharpe": 1.1,
         "struct1_pct": 0.1, "churn_pct": 0.1, "avg_hold": 8.0},
    )
    body = client.get("/research/validate/r1/gate-state").json()
    assert body["data"]["validation_status"] == "is_pass"
    assert len(body["data"]["history"]) == 1


def test_promote_advance_and_audit(client, isolate_stores):
    assert client.get("/research/promote/s1").json()["data"]["stage"] == "draft"
    r = client.post("/research/promote/s1", json={"to_stage": "paper", "note": "ok"})
    assert r.status_code == 200 and r.json()["data"]["stage"] == "paper"
    audit = client.get("/research/promote/s1/audit").json()["data"]
    assert audit[0]["stage"] == "paper" and audit[0]["note"] == "ok"


def test_promote_illegal_skip_422(client, isolate_stores):
    assert client.post("/research/promote/s2", json={"to_stage": "live"}).status_code == 422


def test_validate_wfa_redline_still_pending(client, isolate_stores):
    for sub in ("wfa", "redline"):
        body = client.get(f"/research/validate/r1/{sub}").json()
        assert body["meta"]["data_source"] == "pending"


def test_validate_health_projects_v2_bands(client, write_runs, sample_runs):
    write_runs(sample_runs)
    # bbb222: cagr 0.12 → yellow (8-18%), sharpe 0.90 → yellow (0.5-1.0)
    body = client.get("/research/validate/bbb222/health").json()
    assert body["success"] is True
    rows = {r["key"]: r for r in body["data"]["rows"]}
    assert len(body["data"]["rows"]) == 13
    assert rows["cagr"]["light"] == "yellow"
    assert rows["sharpe"]["light"] == "yellow"
    assert rows["sortino"]["light"] == "na"  # not in the run's metrics
    assert body["data"]["all_green"] is False


def test_validate_health_unknown_run_all_na(client, write_runs, sample_runs):
    write_runs(sample_runs)
    body = client.get("/research/validate/ghost/health").json()
    assert body["data"]["counts"]["na"] == 13


def test_validate_wfa_folds_from_run_window(client, write_runs, sample_runs):
    write_runs(sample_runs)
    # aaa111 window 2015-01-01..2020-12-31 (~6yr) → multiple IS252/OOS63 folds
    body = client.get("/research/validate/aaa111/wfa").json()
    assert body["success"] is True
    folds = body["data"]["folds"]
    assert len(folds) > 1
    # each fold respects is_start < is_end <= oos_start < oos_end
    f0 = folds[0]
    assert f0["is_start"] < f0["is_end"] <= f0["oos_start"] < f0["oos_end"]
    assert body["data"]["scatter"] == []  # per-fold perf parquet-gated
    assert body["meta"]["scatter"] == "pending"
    assert "criteria" in body["data"]


def test_validate_wfa_unknown_run_pending(client, write_runs, sample_runs):
    write_runs(sample_runs)
    body = client.get("/research/validate/ghost/wfa").json()
    assert body["data"]["folds"] == []
    assert body["meta"]["data_source"] == "pending"
