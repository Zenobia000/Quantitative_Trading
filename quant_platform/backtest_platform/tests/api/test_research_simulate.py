"""``POST /research/simulate`` — the research-only what-if endpoint (Goal 8).

Covers the envelope shape, 404 for an unknown run, 422 for out-of-range knobs, the
panel-vs-four-layer feasibility split, and that the ledger/series are never
written (read-only sandbox).
"""
from __future__ import annotations

from backtest_platform.api.routers import research_simulate

# A four-layer run: metrics + per-trade series (stop-loss / take-profit feasible).
_FOUR_LAYER = {
    "run_id": "fl1",
    "strategy": "four_layer",
    "params": {"fee_rate": 0.001425, "tax_stock_rate": 0.003, "slip_rate": 0.001},
    "metrics": {"trades": 3, "cagr": 0.10},
    "is_start": "2015-01-01",
    "is_end": "2020-12-31",
}
_FL_SERIES = {
    "run_id": "fl1",
    "equity": [1.0, 1.1, 1.21],
    "drawdown": [0.0, 0.0, 0.0],
    "trades": [
        {"ret": -0.20, "hold": 3, "entry_structure": 1},
        {"ret": 0.30, "hold": 5, "entry_structure": 2},
        {"ret": 0.05, "hold": 2, "entry_structure": 1},
    ],
}

# A panel run: cost_round_rate + avg_turnover, but no per-trade series.
_PANEL = {
    "run_id": "pn1",
    "strategy": "momentum",
    "params": {"cost_round_rate": 0.00671},
    "metrics": {"trades": 12, "n_rebalances": 12, "avg_turnover": 0.5},
    "is_start": "2015-01-01",
    "is_end": "2020-12-31",
}
_PANEL_SERIES = {"run_id": "pn1", "equity": [1.0, 1.05, 1.08], "drawdown": [0.0, 0.0, 0.0], "trades": []}


def _stub_series(mapping):
    return lambda rid: dict(mapping[rid]) if rid in mapping else None


def test_unknown_run_is_404(client, write_runs):
    write_runs([_FOUR_LAYER])
    body = client.post("/research/simulate", json={"run_id": "ghost"}).json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["detail"] == {"resource": "run", "id": "ghost"}


def test_out_of_range_param_is_422(client, write_runs):
    write_runs([_FOUR_LAYER])
    # cost_multiplier max is 3.0.
    res = client.post("/research/simulate", json={"run_id": "fl1", "cost_multiplier": 9.0})
    assert res.status_code == 422
    body = res.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert any("cost_multiplier" in d["loc"] for d in body["error"]["detail"])


def test_four_layer_stop_loss_take_profit_applies(client, write_runs, monkeypatch):
    write_runs([_FOUR_LAYER])
    monkeypatch.setattr(
        research_simulate.run_series_store, "read_series", _stub_series({"fl1": _FL_SERIES})
    )
    body = client.post(
        "/research/simulate",
        json={"run_id": "fl1", "stop_loss_pct": 0.10, "take_profit_pct": 0.25},
    ).json()
    assert body["success"] is True
    data = body["data"]
    assert data["run_id"] == "fl1"
    assert data["research_only"] is True
    assert data["trade_metrics"]["available"] is True
    # SL clamps trade1, TP clamps trade2 → 2 affected.
    assert data["affected_trades_count"] == 2
    assert data["branch_suggestion"]["actionable"] is False
    assert body["meta"]["data_source"] == "ledger"


def test_panel_cost_multiplier_applies_but_stop_loss_not_available(client, write_runs, monkeypatch):
    write_runs([_PANEL])
    monkeypatch.setattr(
        research_simulate.run_series_store, "read_series", _stub_series({"pn1": _PANEL_SERIES})
    )
    body = client.post(
        "/research/simulate",
        json={"run_id": "pn1", "cost_multiplier": 1.5, "stop_loss_pct": 0.10},
    ).json()
    data = body["data"]
    # cost multiplier: baseline cost_round_rate present + equity present → applied.
    cm = next(x for x in data["per_param"] if x["param"] == "cost_multiplier")
    assert cm["status"] == "applied"
    assert data["portfolio_metrics"]["available"] is True
    # stop-loss: no per-trade pnl → not_available with reason.
    sl = next(x for x in data["per_param"] if x["param"] == "stop_loss_pct")
    assert sl["status"] == "not_available"
    assert data["trade_metrics"]["available"] is False
    assert any(g["field"] == "stop_loss_pct" for g in data["data_gaps"])


def test_simulation_does_not_write_the_ledger(client, write_runs, runs_path, monkeypatch):
    write_runs([_FOUR_LAYER])
    before = runs_path.read_text(encoding="utf-8")
    monkeypatch.setattr(
        research_simulate.run_series_store, "read_series", _stub_series({"fl1": _FL_SERIES})
    )
    client.post("/research/simulate", json={"run_id": "fl1", "cost_multiplier": 2.0})
    # the ledger is byte-for-byte unchanged (research-only, never persisted).
    assert runs_path.read_text(encoding="utf-8") == before
