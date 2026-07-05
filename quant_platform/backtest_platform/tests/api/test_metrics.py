"""``/metrics`` — summary (A/B/C) + trades (E) + validation/edge cases."""
from __future__ import annotations

import pytest


def test_metrics_summary_returns_all_families(client):
    returns = [0.01, -0.02, 0.03, 0.005, -0.01] * 10
    body = client.post("/metrics/summary", json={"daily_returns": returns}).json()
    assert body["success"] is True
    for key in (
        "total_return", "cagr", "max_drawdown", "ulcer_index",
        "downside_deviation", "sharpe", "sortino", "calmar",
    ):
        assert key in body["data"]
        assert isinstance(body["data"][key], (int, float))


def test_metrics_summary_risk_free_changes_sharpe(client):
    returns = [0.01, 0.012, 0.009, 0.011, 0.0105] * 10
    a = client.post("/metrics/summary", json={"daily_returns": returns}).json()
    b = client.post(
        "/metrics/summary", json={"daily_returns": returns, "risk_free": 0.10}
    ).json()
    assert a["data"]["sharpe"] != b["data"]["sharpe"]


def test_metrics_summary_empty_rejected(client):
    resp = client.post("/metrics/summary", json={"daily_returns": []})
    assert resp.status_code == 422


def test_metrics_trades(client):
    trades = [
        {"pnl": 100, "hold_days": 5},
        {"pnl": -50, "hold_days": 3},
        {"pnl": 200, "hold_days": 8},
    ]
    body = client.post("/metrics/trades", json={"trades": trades}).json()
    assert body["data"]["win_rate"] == pytest.approx(2 / 3)
    assert body["data"]["avg_hold"] == pytest.approx((5 + 3 + 8) / 3)
    assert body["data"]["profit_factor"] == pytest.approx(300 / 50)


def test_metrics_trades_missing_key_is_400(client):
    resp = client.post("/metrics/trades", json={"trades": [{"foo": 1}]})
    assert resp.status_code == 400
    assert resp.json()["success"] is False
