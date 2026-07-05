"""S2 endpoints — POST /research/sweep (async job) + GET /{id}/status."""
from __future__ import annotations

import time

import pytest

from backtest_platform.services.monitoring_ops.jobs import job_store


@pytest.fixture
def isolate_jobs(tmp_path, monkeypatch):
    monkeypatch.setattr(job_store, "DEFAULT_JOBS_PATH", tmp_path / "jobs.jsonl")


def _poll_done(client, job_id, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        body = client.get(f"/research/sweep/{job_id}/status").json()
        if body["data"].get("status") in ("done", "failed"):
            return body["data"]
        time.sleep(0.01)
    raise AssertionError("sweep job did not finish in time")


def test_submit_sweep_then_poll_plan(client, isolate_jobs):
    r = client.post("/research/sweep", json={"grid": {"box_period": [40, 60], "confirm_days": [1, 2]}})
    assert r.status_code == 202
    job_id = r.json()["data"]["job_id"]
    assert r.json()["data"]["status"] == "queued"
    final = _poll_done(client, job_id)
    assert final["status"] == "done"
    assert final["result"]["n_configs"] == 4  # 2 x 2 grid


def test_sweep_status_unknown_is_404(client, isolate_jobs):
    # A4 / doc 25 §5.2: an unknown/expired sweep job id is 404 (not an infinite pending).
    resp = client.get("/research/sweep/ghost/status")
    assert resp.status_code == 404
    err = resp.json()["error"]
    assert err["code"] == "NOT_FOUND"
    assert err["detail"] == {"resource": "job", "id": "ghost"}


def test_submit_empty_grid_single_config(client, isolate_jobs):
    r = client.post("/research/sweep", json={"grid": {}})
    final = _poll_done(client, r.json()["data"]["job_id"])
    assert final["result"]["n_configs"] == 1
