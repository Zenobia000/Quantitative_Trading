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


# ---- bundles manifest scan (C1) -----------------------------------------

import json as _json  # noqa: E402

_DEFAULT_MANIFEST = {
    "schema_version": 1,
    "stocks": {"2330": {"start": "2020-01-02", "end": "2024-12-31", "rows": 1200, "data_hash": "a"}},
    "stock_count": 1,
    "coverage": {"start": "2020-01-02", "end": "2024-12-31"},
    "data_hash": "deadbeefcafef00d",
    "generated_at": "2026-07-01T00:00:00+00:00",
}
_UNIVERSE_MANIFEST = {
    "strategy": "inst_flow",
    "params": {"span_start": "2010-01-01", "span_end": "2024-12-31", "top_n": 200, "min_turnover": 5e7},
    "symbols": ["2330", "2317", "2454"],
    "n_symbols": 3,
    "n_alive": 2,
    "n_delisted": 1,
    "ingest": {"ok": 3, "failed": 0, "failed_symbols": []},
    "generated_at": "2026-07-02T00:00:00+00:00",
}


def _seed_manifest(root, dirname, filename, manifest):
    d = root / dirname
    d.mkdir(parents=True, exist_ok=True)
    (d / filename).write_text(_json.dumps(manifest), encoding="utf-8")


def test_bundles_empty_when_no_manifests(client):
    body = client.get("/system/bundles").json()
    assert body["success"] is True
    assert body["data"] == []
    # typed-empty from a real scan (NOT the old "pending" stub)
    assert body["meta"]["data_source"] == "parquet_scan"
    assert body["meta"]["total"] == 0


def test_bundles_lists_default_and_universe_caches(client, data_root):
    _seed_manifest(data_root, "parquet", "manifest.json", _DEFAULT_MANIFEST)
    _seed_manifest(data_root, "parquet_finlab_universe", "universe_manifest.json", _UNIVERSE_MANIFEST)
    body = client.get("/system/bundles").json()
    assert body["meta"]["total"] == 2
    by_id = {b["id"]: b for b in body["data"]}
    assert by_id["parquet"]["kind"] == "default"
    assert by_id["parquet"]["stock_count"] == 1
    assert by_id["parquet"]["data_hash"] == "deadbeefcafef00d"
    uni = by_id["parquet_finlab_universe"]
    assert uni["kind"] == "universe"
    assert uni["stock_count"] == 3
    assert uni["coverage_start"] == "2010-01-01"
    assert uni["strategy"] == "inst_flow"


def test_bundles_corrupt_manifest_is_skipped_not_500(client, data_root):
    d = data_root / "parquet"
    d.mkdir(parents=True, exist_ok=True)
    (d / "manifest.json").write_text("{ broken", encoding="utf-8")
    r = client.get("/system/bundles")
    assert r.status_code == 200
    assert r.json()["data"] == []


def test_bundle_quality_default_row_stats(client, data_root):
    _seed_manifest(data_root, "parquet", "manifest.json", _DEFAULT_MANIFEST)
    body = client.get("/system/bundles/parquet/quality").json()
    assert body["success"] is True
    q = body["data"]
    assert q["kind"] == "default"
    assert q["total_rows"] == 1200
    assert q["data_hash"] == "deadbeefcafef00d"


def test_bundle_quality_universe_tallies(client, data_root):
    _seed_manifest(data_root, "parquet_finlab_universe", "universe_manifest.json", _UNIVERSE_MANIFEST)
    body = client.get("/system/bundles/parquet_finlab_universe/quality").json()
    q = body["data"]
    assert q["kind"] == "universe"
    assert q["n_alive"] == 2
    assert q["n_delisted"] == 1
    assert q["n_ingested_ok"] == 3


def test_bundle_quality_unknown_is_typed_empty(client):
    body = client.get("/system/bundles/ghost/quality").json()
    assert body["success"] is True
    assert body["data"] is None
    assert body["meta"]["data_source"] == "not_found"


# ---- universe build async job (C2) --------------------------------------

_BUILD_REQ = {
    "strategy": "inst_flow",
    "span_start": "2010-01-01",
    "span_end": "2024-12-31",
    "top_n": 200,
    "min_turnover": 50000000.0,
    "cache_dir": "data/parquet_test_universe",
}


class _FakeBuildResult:
    """Stand-in for UniverseBuildResult (only the fields the endpoint reads)."""

    strategy = "inst_flow"
    universe = ("2330", "2317", "2454")
    n_alive = 2
    n_delisted = 1
    n_ingested_ok = 3
    n_ingested_failed = 0
    manifest_path = "data/parquet_test_universe/universe_manifest.json"


def test_universe_build_submits_job_then_status_done(client, monkeypatch, isolate_jobs):
    # stub the real FinLab-touching workflow — no network, deterministic result
    monkeypatch.setattr(
        "backtest_platform.research.workflows.universe.run_build_universe",
        lambda cfg, getter=None: _FakeBuildResult(),
    )
    r = client.post("/system/universe/build", json=_BUILD_REQ)
    assert r.status_code == 202
    job_id = r.json()["data"]["job_id"]
    assert r.json()["data"]["status"] == "queued"

    final = _poll_status_at(client, "/system/universe/build", job_id)
    assert final["status"] == "done"
    assert final["result"]["n_symbols"] == 3
    assert final["result"]["n_alive"] == 2
    assert final["result"]["n_ingested_ok"] == 3
    assert final["result"]["manifest_path"].endswith("universe_manifest.json")


def test_universe_build_failure_captured_as_failed(client, monkeypatch, isolate_jobs):
    def _boom(cfg, getter=None):
        raise RuntimeError("FINLAB_API_TOKEN not set")

    monkeypatch.setattr(
        "backtest_platform.research.workflows.universe.run_build_universe", _boom
    )
    r = client.post("/system/universe/build", json=_BUILD_REQ)
    job_id = r.json()["data"]["job_id"]
    final = _poll_status_at(client, "/system/universe/build", job_id)
    assert final["status"] == "failed"
    assert "FINLAB_API_TOKEN" in final["error"]


def test_universe_build_bad_span_422(client, isolate_jobs):
    r = client.post(
        "/system/universe/build", json={**_BUILD_REQ, "span_start": "2025-01-01", "span_end": "2024-12-31"}
    )
    assert r.status_code == 422


def test_universe_build_bad_top_n_422(client, isolate_jobs):
    r = client.post("/system/universe/build", json={**_BUILD_REQ, "top_n": 0})
    assert r.status_code == 422


def test_universe_build_status_unknown_is_pending(client, isolate_jobs):
    body = client.get("/system/universe/build/ghost/status").json()
    assert body["data"]["status"] is None
    assert body["meta"]["data_source"] == "pending"


def _poll_status_at(client, base, job_id, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        body = client.get(f"{base}/{job_id}/status").json()
        if body["data"].get("status") in ("done", "failed"):
            return body["data"]
        time.sleep(0.01)
    raise AssertionError("job did not finish in time")
