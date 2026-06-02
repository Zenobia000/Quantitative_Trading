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
