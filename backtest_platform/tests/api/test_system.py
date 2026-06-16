"""``/system`` zone — endpoints wired to real config (vs typed-empty stubs).

``/system/risk/spec`` is rule *definitions* (not live telemetry), so it ships
real now — it projects ``risk.risk_gate.risk_spec`` and carries no pending tag.
"""
from __future__ import annotations


def test_risk_spec_returns_real_rules_not_pending(client):
    body = client.get("/system/risk/spec").json()
    assert body["success"] is True
    # real config projection — NOT a pending stub (meta is null, not data_source=pending)
    assert (body.get("meta") or {}).get("data_source") != "pending"
    data = body["data"]
    assert len(data["rules"]) == 12
    assert data["rules"][0]["id"] == "EX-012"  # §2.2 order: circuit breaker first
    assert data["thresholds"]["max_positions"] == 15


def test_alert_rules_returns_real_builtin_rules_not_pending(client):
    body = client.get("/system/alerts/rules").json()
    assert body["success"] is True
    assert (body.get("meta") or {}).get("data_source") != "pending"
    rules = body["data"]
    assert len(rules) > 0
    assert body["meta"]["total"] == len(rules)
    sample = rules[0]
    assert set(sample) == {"rule_id", "level", "title"}
    assert sample["level"] in {"CRITICAL", "HIGH", "INFO"}


# ---- ingest async job (8.H.6) -------------------------------------------

import time  # noqa: E402

import pytest  # noqa: E402

from backtest_platform.jobs import job_store  # noqa: E402

_INGEST_REQ = {
    "symbols": ["2330", "2317"],
    "start": "2023-01-01",
    "end": "2023-12-31",
    "source": "finlab",
}


@pytest.fixture
def isolate_jobs(tmp_path, monkeypatch):
    monkeypatch.setattr(job_store, "DEFAULT_JOBS_PATH", tmp_path / "jobs.jsonl")


def _poll_status(client, job_id, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        body = client.get(f"/system/ingest/{job_id}/status").json()
        if body["data"].get("status") in ("done", "failed"):
            return body["data"]
        time.sleep(0.01)
    raise AssertionError("ingest job did not finish in time")


def test_ingest_submits_job_then_status_done(client, monkeypatch, isolate_jobs):
    # stub the real ETL (no live FinLab) — 2330 ok, 2317 fails
    monkeypatch.setattr(
        "backtest_platform.data.finlab_source.ingest_universe_finlab",
        lambda syms, s, e, **k: type("R", (), {"failed_symbols": ("2317",)})(),
    )
    r = client.post("/system/ingest", json=_INGEST_REQ)
    assert r.status_code == 202
    job_id = r.json()["data"]["job_id"]
    assert r.json()["data"]["status"] == "queued"
    final = _poll_status(client, job_id)
    assert final["status"] == "done"
    assert final["result"]["requested"] == 2
    assert final["result"]["ok"] == ["2330"]
    assert final["result"]["failed"] == ["2317"]


def test_ingest_status_unknown_is_pending(client, isolate_jobs):
    body = client.get("/system/ingest/ghost/status").json()
    assert body["data"]["status"] is None
    assert body["meta"]["data_source"] == "pending"


def test_ingest_empty_symbols_422(client, isolate_jobs):
    r = client.post("/system/ingest", json={**_INGEST_REQ, "symbols": []})
    assert r.status_code == 422
