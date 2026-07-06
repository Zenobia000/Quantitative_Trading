"""``/gate`` — spec + evaluate (PASS / FAIL / INCOMPLETE) + extra-field rejection."""
from __future__ import annotations

# Full metrics dict that clears every default criterion (edge + health).
_PASSING = {
    "cagr": 0.25,
    "sharpe": 1.5,
    "slippage_sharpe": 1.2,
    "struct1_pct": 0.10,
    "churn_pct": 0.10,
    "avg_hold": 8.0,
}


def test_gate_spec_lists_default_criteria(client):
    body = client.get("/gate/spec").json()
    keys = {c["key"] for c in body["data"]["criteria"]}
    assert {"cagr", "sharpe", "slippage_sharpe", "struct1_pct", "churn_pct", "avg_hold"} <= keys
    # criteria carry their edge/health kind so a client can group them.
    kinds = {c["kind"] for c in body["data"]["criteria"]}
    assert kinds == {"edge", "health"}


def test_gate_evaluate_pass(client):
    body = client.post("/gate/evaluate", json={"metrics": _PASSING}).json()
    assert body["data"]["status"] == "PASS"
    assert body["data"]["passed"] is True
    assert all(r["passed"] for r in body["data"]["results"])


def test_gate_evaluate_fail(client):
    failing = {**_PASSING, "cagr": 0.01, "sharpe": 0.2}
    body = client.post("/gate/evaluate", json={"metrics": failing}).json()
    assert body["data"]["status"] == "FAIL"
    assert body["data"]["passed"] is False
    assert any(r["passed"] is False for r in body["data"]["results"])


def test_gate_evaluate_incomplete_when_metric_missing(client):
    body = client.post("/gate/evaluate", json={"metrics": {"cagr": 0.25}}).json()
    # missing gated metrics → cannot claim PASS
    assert body["data"]["status"] == "INCOMPLETE"
    assert body["data"]["passed"] is False


def test_gate_evaluate_rejects_extra_field(client):
    resp = client.post("/gate/evaluate", json={"metrics": {}, "bogus": 1})
    assert resp.status_code == 422
    assert resp.json()["success"] is False


# ---- per-strategy gate dispatch (審查缺陷 #8) ----------------------------------

def test_gate_spec_dispatches_strategy_gate(client):
    """?strategy=momentum → momentum's panel gate (avg_holdings health), not the
    four-layer entry-quality health checks."""
    body = client.get("/gate/spec", params={"strategy": "momentum"}).json()
    keys = {c["key"] for c in body["data"]["criteria"]}
    assert "avg_holdings" in keys
    assert "struct1_pct" not in keys  # four-layer-only health check


def test_gate_evaluate_momentum_metrics_not_incomplete(client):
    """Momentum metrics (no four-layer health keys) reach a real verdict when
    judged by momentum's own gate — the whole point of the fix."""
    momentum_metrics = {
        "cagr": 0.25, "sharpe": 1.5, "slippage_sharpe": 1.2, "avg_holdings": 8.0,
    }
    body = client.post(
        "/gate/evaluate", json={"metrics": momentum_metrics, "strategy": "momentum"}
    ).json()
    assert body["data"]["status"] == "PASS"


def test_gate_evaluate_unknown_strategy_is_404(client):
    # A4: an unknown *named resource* is 404 everywhere (standardized with
    # /research/workflows/{workflow}); detail is structured {resource, id}.
    resp = client.post(
        "/gate/evaluate", json={"metrics": {}, "strategy": "does_not_exist"}
    )
    assert resp.status_code == 404
    err = resp.json()["error"]
    assert err["code"] == "NOT_FOUND"
    assert err["detail"] == {"resource": "strategy", "id": "does_not_exist"}


def test_gate_spec_unknown_strategy_is_404(client):
    resp = client.get("/gate/spec", params={"strategy": "does_not_exist"})
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"
