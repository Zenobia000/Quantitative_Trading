"""``/research/strategies`` — strategy roster projected over the runs ledger."""
from __future__ import annotations


def test_strategies_empty(client):
    body = client.get("/research/strategies").json()
    assert body["success"] is True
    assert body["data"] == []
    assert body["meta"] == {"total": 0, "page": 1, "limit": 50}


def test_strategies_projected_from_ledger(client, write_runs, sample_runs):
    write_runs(sample_runs)
    body = client.get("/research/strategies").json()
    assert body["meta"]["total"] == 2
    by_id = {s["strategy_id"]: s for s in body["data"]}
    assert set(by_id) == {"v2", "v3.1b"}
    # 每 preset 一筆 run → runs_count 1；FAIL → validation_status is_fail；stage draft
    assert by_id["v3.1b"]["runs_count"] == 1
    assert by_id["v3.1b"]["validation_status"] == "is_fail"
    assert by_id["v3.1b"]["stage"] == "draft"
    # best_kpi 取最高 Sharpe 的 metrics
    assert by_id["v3.1b"]["best_kpi"]["sharpe"] == 0.90


def test_strategies_pagination(client, write_runs, sample_runs):
    write_runs(sample_runs)
    page1 = client.get("/research/strategies", params={"page": 1, "limit": 1}).json()
    assert len(page1["data"]) == 1
    assert page1["meta"] == {"total": 2, "page": 1, "limit": 1}


def test_strategies_invalid_page_422(client):
    assert client.get("/research/strategies", params={"page": 0}).status_code == 422
