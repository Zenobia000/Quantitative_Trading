"""``/runs`` — list / get / compare / trigger, against a temp ledger + stub executor."""
from __future__ import annotations

import json
import time

import pytest

from quant_platform.services.monitoring_ops.jobs import job_store


def _seed_universe(data_root, dirname, symbols):
    """Write a minimal ``universe_manifest.json`` so a named pool resolves (Slice 2)."""
    d = data_root / dirname
    d.mkdir(parents=True, exist_ok=True)
    manifest = {
        "strategy": "inst_flow",
        "params": {"span_start": "2010-01-01", "span_end": "2024-12-31"},
        "symbols": list(symbols),
        "n_symbols": len(symbols),
        "generated_at": "2026-07-02T00:00:00+00:00",
    }
    (d / "universe_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

# ---- list ---------------------------------------------------------------

def test_list_runs_empty(client):
    body = client.get("/runs").json()
    assert body["data"] == []
    assert body["meta"] == {"total": 0, "page": 1, "limit": 50}


def test_list_runs_seeded(client, write_runs, sample_runs):
    write_runs(sample_runs)
    body = client.get("/runs").json()
    assert body["meta"]["total"] == 2
    assert {item["run_id"] for item in body["data"]} == {"aaa111", "bbb222"}
    # list view is a projection (summary keys only)
    assert set(body["data"][0]) == {
        "run_id", "strategy", "gate_status", "hypothesis", "metrics", "is_start", "is_end"
    }


def test_list_runs_pagination(client, write_runs, sample_runs):
    write_runs(sample_runs)
    page1 = client.get("/runs", params={"page": 1, "limit": 1}).json()
    assert len(page1["data"]) == 1
    assert page1["meta"] == {"total": 2, "page": 1, "limit": 1}
    page2 = client.get("/runs", params={"page": 2, "limit": 1}).json()
    assert len(page2["data"]) == 1
    assert page1["data"][0]["run_id"] != page2["data"][0]["run_id"]


def test_list_runs_invalid_page_422(client):
    assert client.get("/runs", params={"page": 0}).status_code == 422


def test_list_runs_dedupes_duplicate_run_id(client, write_runs, sample_runs):
    # append-only ledger: aaa111 re-run with an updated gate_status → latest wins,
    # the table shows one current row per run_id (audit F5 root fix).
    dup = dict(sample_runs[0], gate_status="PASS")
    write_runs(sample_runs + [dup])  # 3 lines, 2 distinct run_ids
    body = client.get("/runs").json()
    assert body["meta"]["total"] == 2
    rows = {item["run_id"]: item for item in body["data"]}
    assert set(rows) == {"aaa111", "bbb222"}
    assert rows["aaa111"]["gate_status"] == "PASS"  # latest append, not the original FAIL


# ---- get ----------------------------------------------------------------

def test_get_run_found_returns_full_record(client, write_runs, sample_runs):
    write_runs(sample_runs)
    body = client.get("/runs/bbb222").json()
    assert body["data"]["strategy"] == "momentum"
    assert body["data"]["hypothesis"] == "dirB strict structure"


def test_get_run_404(client):
    resp = client.get("/runs/nonexistent")
    assert resp.status_code == 404
    assert resp.json()["success"] is False


def test_get_run_returns_latest_for_duplicate_run_id(client, write_runs, sample_runs):
    dup = dict(sample_runs[0], gate_status="PASS")
    write_runs(sample_runs + [dup])
    body = client.get("/runs/aaa111").json()
    assert body["data"]["gate_status"] == "PASS"  # latest append, consistent with list


# ---- compare ------------------------------------------------------------

def test_compare_with_baseline(client, write_runs, sample_runs):
    write_runs(sample_runs)
    data = client.get("/runs/compare", params={"baseline": "aaa111"}).json()["data"]
    assert data["baseline_id"] == "aaa111"
    assert len(data["comparisons"]) == 2
    bbb = next(c for c in data["comparisons"] if c["run_id"] == "bbb222")
    # dirB has higher sharpe than baseline → positive delta
    assert bbb["delta"]["sharpe"] > 0


def test_compare_unknown_baseline_404(client, write_runs, sample_runs):
    write_runs(sample_runs)
    resp = client.get("/runs/compare", params={"baseline": "zzz999"})
    assert resp.status_code == 404
    assert resp.json()["success"] is False


def test_compare_empty_ledger(client):
    data = client.get("/runs/compare").json()["data"]
    assert data["baseline_id"] is None
    assert data["comparisons"] == []


def test_compare_run_ids_subset_compares_only_selected(client, write_runs, sample_runs):
    # three in the ledger; the frontend multi-select picks two → only those compare
    third = dict(sample_runs[1], run_id="ccc333", strategy="momentum")
    write_runs(sample_runs + [third])
    data = client.get(
        "/runs/compare", params={"run_ids": "aaa111,ccc333", "baseline": "aaa111"}
    ).json()["data"]
    assert data["baseline_id"] == "aaa111"
    assert {c["run_id"] for c in data["comparisons"]} == {"aaa111", "ccc333"}  # bbb222 excluded


def test_compare_run_ids_unknown_member_404(client, write_runs, sample_runs):
    write_runs(sample_runs)
    resp = client.get("/runs/compare", params={"run_ids": "aaa111,nope999"})
    assert resp.status_code == 404
    assert "nope999" in resp.json()["error"]["message"]


# ---- trigger (POST) -----------------------------------------------------

_VALID_PAYLOAD = {
    "hypothesis": "does four_layer hold cross-window",
    "strategy": "four_layer",
    "params": {},
    "stocks": ["2330", "1101"],
    "is_start": "2020-01-01",
    "is_end": "2024-12-31",
}


def test_create_run_appends_and_is_listable(client, runs_path, stub_executor):
    resp = client.post("/runs", json=_VALID_PAYLOAD)
    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["strategy"] == "four_layer"
    assert len(stub_executor.calls) == 1
    assert runs_path.exists()
    # now visible in the ledger list
    assert client.get("/runs").json()["meta"]["total"] == 1


def test_create_run_reversed_window_422(client):
    payload = {**_VALID_PAYLOAD, "is_start": "2024-01-01", "is_end": "2020-01-01"}
    resp = client.post("/runs", json=payload)
    assert resp.status_code == 422


def test_create_run_no_pool_falls_back_to_default_universe(client, stub_executor):
    # SPEC-01 Slice 2 / ADR-007: a run never *requires* hand-typed symbols —
    # omitting both stocks and universe resolves to the system default universe.
    from quant_platform.packages.infrastructure.config.universe import DEFAULT_UNIVERSE

    payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "stocks"}
    resp = client.post("/runs", json=payload)
    assert resp.status_code == 201
    assert tuple(stub_executor.calls[-1].stocks) == DEFAULT_UNIVERSE


def test_create_run_with_universe_resolves_symbols(client, data_root, stub_executor):
    _seed_universe(data_root, "parquet_finlab_universe", ["2330", "2317", "2454"])
    payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "stocks"}
    payload["universe"] = "parquet_finlab_universe"
    resp = client.post("/runs", json=payload)
    assert resp.status_code == 201
    assert tuple(stub_executor.calls[-1].stocks) == ("2330", "2317", "2454")


def test_create_run_unknown_universe_422(client):
    payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "stocks"}
    payload["universe"] = "does_not_exist"
    resp = client.post("/runs", json=payload)
    assert resp.status_code == 422


def test_create_run_explicit_stocks_win_over_universe(client, data_root, stub_executor):
    _seed_universe(data_root, "parquet_finlab_universe", ["2330", "2317"])
    payload = {**_VALID_PAYLOAD, "stocks": ["1101"], "universe": "parquet_finlab_universe"}
    resp = client.post("/runs", json=payload)
    assert resp.status_code == 201
    assert tuple(stub_executor.calls[-1].stocks) == ("1101",)


# ---- async (8.H.6) ------------------------------------------------------

@pytest.fixture
def isolate_jobs(tmp_path, monkeypatch):
    monkeypatch.setattr(job_store, "DEFAULT_JOBS_PATH", tmp_path / "jobs.jsonl")


def _poll_log(client, job_id, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        body = client.get(f"/runs/{job_id}/log").json()
        if body["data"].get("status") in ("done", "failed"):
            return body["data"]
        time.sleep(0.01)
    raise AssertionError("async run did not finish in time")


def test_create_run_async_submits_then_logs_done(client, runs_path, stub_executor, isolate_jobs):
    resp = client.post("/runs/async", json=_VALID_PAYLOAD)
    assert resp.status_code == 202
    job_id = resp.json()["data"]["job_id"]
    assert resp.json()["data"]["status"] == "queued"
    final = _poll_log(client, job_id)
    assert final["status"] == "done"
    assert final["result"]["strategy"] == "four_layer"
    assert len(stub_executor.calls) == 1
    # the async job appended to the ledger → now listable (sync POST unaffected)
    assert client.get("/runs").json()["meta"]["total"] == 1


def test_run_log_unknown_is_404(client, isolate_jobs):
    # A4 / doc 25 §5.2: an unknown/expired job id is 404, so the FE poller surfaces
    # an error state instead of an infinite pending.
    resp = client.get("/runs/ghost/log")
    assert resp.status_code == 404
    err = resp.json()["error"]
    assert err["code"] == "NOT_FOUND"
    assert err["detail"] == {"resource": "job", "id": "ghost"}
