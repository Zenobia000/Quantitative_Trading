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
    assert set(by_id) == {"four_layer", "momentum"}
    # 每 strategy 一筆 run → runs_count 1；FAIL → validation_status is_fail；stage draft
    assert by_id["momentum"]["runs_count"] == 1
    assert by_id["momentum"]["validation_status"] == "is_fail"
    assert by_id["momentum"]["stage"] == "draft"
    # best_kpi 取最高 Sharpe 的 metrics
    assert by_id["momentum"]["best_kpi"]["sharpe"] == 0.90


def test_strategies_pagination(client, write_runs, sample_runs):
    write_runs(sample_runs)
    page1 = client.get("/research/strategies", params={"page": 1, "limit": 1}).json()
    assert len(page1["data"]) == 1
    assert page1["meta"] == {"total": 2, "page": 1, "limit": 1}


def test_strategies_invalid_page_422(client):
    assert client.get("/research/strategies", params={"page": 0}).status_code == 422


# ---- /runs/estimate (sweep grid cardinality) ----------------------------

def test_estimate_grid_cardinality(client):
    body = client.get("/runs/estimate", params={"box_period": "40,60,80", "confirm_days": "1,2", "strategy": "four_layer"}).json()
    assert body["data"]["n_configs"] == 6  # 3 × 2（strategy 不計入軸）
    assert body["data"]["est_minutes"] == 3.0  # 6 × 0.5
    assert body["data"]["axes"] == {"box_period": 3, "confirm_days": 2}


def test_estimate_empty_grid_is_one(client):
    body = client.get("/runs/estimate").json()
    assert body["data"]["n_configs"] == 1


# ---- /research/universe-filters (real config) ---------------------------

def test_universe_filters_real_config(client):
    body = client.get("/research/universe-filters").json()
    d = body["data"]
    assert d["markets"] == ["TWSE", "TPEX"]
    assert d["min_market_cap"] == 5e9
    assert d["price_range"] == [10.0, 500.0]
    assert "market_cap_too_low" in d["exclude_reasons"]
