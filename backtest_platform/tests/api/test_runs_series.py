"""``/runs/{id}/equity`` · ``/trades`` — computed series from the run sidecar (S4)."""
from __future__ import annotations

from backtest_platform.api.routers import runs_series


def test_equity_found(client, monkeypatch):
    monkeypatch.setattr(
        runs_series.run_series_store,
        "read_series",
        lambda rid: {"run_id": rid, "equity": [1.0, 1.05], "drawdown": [0.0, -0.01], "trades": []},
    )
    body = client.get("/runs/abc/equity").json()
    assert body["success"] is True
    assert body["data"]["equity"] == [1.0, 1.05]
    assert body["data"]["drawdown"] == [0.0, -0.01]
    assert body["meta"] is None  # real data → no pending marker


def test_equity_missing_is_pending(client, monkeypatch):
    monkeypatch.setattr(runs_series.run_series_store, "read_series", lambda rid: None)
    body = client.get("/runs/ghost/equity").json()
    assert body["data"]["equity"] == []
    assert body["meta"]["data_source"] == "pending"


def test_trades_found(client, monkeypatch):
    monkeypatch.setattr(
        runs_series.run_series_store,
        "read_series",
        lambda rid: {"run_id": rid, "equity": [], "drawdown": [],
                     "trades": [{"ret": 0.04, "hold": 8, "entry_structure": 2}]},
    )
    body = client.get("/runs/abc/trades").json()
    assert body["success"] is True
    assert body["data"]["trades"][0]["hold"] == 8


def test_trades_missing_is_pending(client, monkeypatch):
    monkeypatch.setattr(runs_series.run_series_store, "read_series", lambda rid: None)
    body = client.get("/runs/ghost/trades").json()
    assert body["data"]["trades"] == []
    assert body["meta"]["data_source"] == "pending"
