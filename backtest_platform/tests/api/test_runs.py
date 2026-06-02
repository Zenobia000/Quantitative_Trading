"""``/runs`` — list / get / compare / trigger, against a temp ledger + stub executor."""
from __future__ import annotations


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
        "run_id", "preset", "gate_status", "hypothesis", "metrics", "is_start", "is_end"
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


# ---- get ----------------------------------------------------------------

def test_get_run_found_returns_full_record(client, write_runs, sample_runs):
    write_runs(sample_runs)
    body = client.get("/runs/bbb222").json()
    assert body["data"]["preset"] == "v3.1b"
    assert body["data"]["hypothesis"] == "dirB strict structure"


def test_get_run_404(client):
    resp = client.get("/runs/nonexistent")
    assert resp.status_code == 404
    assert resp.json()["success"] is False


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


# ---- trigger (POST) -----------------------------------------------------

_VALID_PAYLOAD = {
    "hypothesis": "does v3.1b hold cross-window",
    "preset": "v3.1b",
    "stocks": ["2330", "1101"],
    "is_start": "2020-01-01",
    "is_end": "2024-12-31",
}


def test_create_run_appends_and_is_listable(client, runs_path, stub_executor):
    resp = client.post("/runs", json=_VALID_PAYLOAD)
    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["preset"] == "v3.1b"
    assert len(stub_executor.calls) == 1
    assert runs_path.exists()
    # now visible in the ledger list
    assert client.get("/runs").json()["meta"]["total"] == 1


def test_create_run_unknown_preset_422(client):
    payload = {**_VALID_PAYLOAD, "preset": "no-such-preset"}
    resp = client.post("/runs", json=payload)
    assert resp.status_code == 422
    assert resp.json()["success"] is False


def test_create_run_reversed_window_422(client):
    payload = {**_VALID_PAYLOAD, "is_start": "2024-01-01", "is_end": "2020-01-01"}
    resp = client.post("/runs", json=payload)
    assert resp.status_code == 422


def test_create_run_empty_stocks_422(client):
    payload = {**_VALID_PAYLOAD, "stocks": []}
    resp = client.post("/runs", json=payload)
    assert resp.status_code == 422
