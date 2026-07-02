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


# --- /runs/{id}/candles (Trade Review K-line) -----------------------------
def test_candles_happy_path(client, write_runs, monkeypatch):
    write_runs([{"run_id": "r1", "strategy": "four_layer", "stocks": ["2330", "2317"]}])
    monkeypatch.setattr(
        runs_series.run_candles,
        "build_candles",
        lambda record, stock, **kw: {
            "candles": [{"time": "2020-01-01", "open": 1, "high": 2, "low": 0, "close": 1.5, "volume": 10}],
            "markers": [{"time": "2020-01-01", "kind": "entry", "price": 1.5}],
        },
    )
    body = client.get("/runs/r1/candles").json()
    assert body["success"] is True
    assert body["meta"] is None  # real data → no pending marker
    assert body["data"]["stock"] == "2330"  # default = first stock
    assert body["data"]["stocks"] == ["2330", "2317"]
    assert len(body["data"]["candles"]) == 1
    assert body["data"]["markers"][0]["kind"] == "entry"


def test_candles_unknown_run_404_envelope(client):
    resp = client.get("/runs/ghost/candles")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"


def test_candles_missing_parquet_is_pending(client, write_runs, monkeypatch):
    write_runs([{"run_id": "r1", "strategy": "four_layer", "stocks": ["2330"]}])
    monkeypatch.setattr(runs_series.run_candles, "build_candles", lambda record, stock, **kw: None)
    body = client.get("/runs/r1/candles").json()
    assert body["success"] is True
    assert body["data"]["candles"] == []
    assert body["data"]["markers"] == []
    assert body["meta"]["data_source"] == "pending"


def test_candles_stock_param_selects_symbol(client, write_runs, monkeypatch):
    write_runs([{"run_id": "r1", "strategy": "four_layer", "stocks": ["2330", "2317"]}])
    seen: dict[str, str] = {}

    def _fake(record, stock, **kw):
        seen["stock"] = stock
        return {"candles": [{"time": "2020-01-01", "open": 1, "high": 2, "low": 0, "close": 1.5, "volume": 10}], "markers": []}

    monkeypatch.setattr(runs_series.run_candles, "build_candles", _fake)
    body = client.get("/runs/r1/candles", params={"stock": "2317"}).json()
    assert seen["stock"] == "2317"
    assert body["data"]["stock"] == "2317"


def test_candles_unknown_stock_param_falls_back_to_first(client, write_runs, monkeypatch):
    write_runs([{"run_id": "r1", "strategy": "four_layer", "stocks": ["2330", "2317"]}])
    monkeypatch.setattr(
        runs_series.run_candles,
        "build_candles",
        lambda record, stock, **kw: {"candles": [{"time": "2020-01-01", "open": 1, "high": 2, "low": 0, "close": 1.5, "volume": 10}], "markers": []},
    )
    body = client.get("/runs/r1/candles", params={"stock": "9999"}).json()
    assert body["data"]["stock"] == "2330"  # not-in-run symbol → first stock


def test_candles_run_without_stocks_is_pending(client, write_runs):
    write_runs([{"run_id": "r1", "strategy": "four_layer"}])  # no stocks key
    body = client.get("/runs/r1/candles").json()
    assert body["data"]["stock"] is None
    assert body["data"]["candles"] == []
    assert body["meta"]["data_source"] == "pending"
