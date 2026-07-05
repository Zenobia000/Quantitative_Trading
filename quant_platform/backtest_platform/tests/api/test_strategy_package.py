"""Strategy Package API — descriptor + DOE optimization schema (ADR-008)."""
from __future__ import annotations


def test_strategy_asset_projects_package_descriptor(client):
    body = client.get("/strategies/momentum/asset").json()
    assert body["success"] is True
    data = body["data"]
    assert data["strategy"] == "momentum"
    assert data["package"] == "backtest_platform.strategies.momentum"
    assert data["package_path"].endswith("src/backtest_platform/strategies/momentum")
    files = {f["path"]: f for f in data["files"]}
    assert files["strategy.py"]["role"] == "alpha_logic"
    assert files["strategy.py"]["present"] is True
    assert files["runner.py"]["present"] is True
    assert files["research_config.py"]["present"] is True
    assert "doe" in data["workflows"]
    assert data["endpoints"]["optimization_schema"] == "/strategies/momentum/optimization-schema"


def test_strategy_asset_unknown_strategy_404(client):
    r = client.get("/strategies/nope/asset")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


def test_strategy_optimization_schema_projects_doe_grid(client):
    body = client.get("/strategies/momentum/optimization-schema").json()
    assert body["success"] is True
    data = body["data"]
    assert data["strategy"] == "momentum"
    assert "properties" in data["config_schema"]
    opt = data["optimization"]
    assert opt["workflow"] == "doe"
    assert opt["n_configs"] >= 1
    assert isinstance(opt["grid"], dict)
    assert opt["symbols_count"] >= len(opt["symbols_preview"])


def test_strategy_optimization_schema_unknown_strategy_404(client):
    r = client.get("/strategies/nope/optimization-schema")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"
