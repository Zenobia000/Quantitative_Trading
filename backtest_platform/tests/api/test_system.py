"""``/system`` zone — endpoints wired to real config (vs typed-empty stubs).

``/system/risk/spec`` is rule *definitions* (not live telemetry), so it ships
real now — it projects ``risk.risk_gate.risk_spec`` and carries no pending tag.
"""
from __future__ import annotations


def test_risk_spec_returns_real_rules_not_pending(client):
    body = client.get("/system/risk/spec").json()
    assert body["success"] is True
    # real config projection — NOT a pending stub (meta is null, not data_source=pending)
    assert (body.get("meta") or {}).get("data_source") != "pending"
    data = body["data"]
    assert len(data["rules"]) == 12
    assert data["rules"][0]["id"] == "EX-012"  # §2.2 order: circuit breaker first
    assert data["thresholds"]["max_positions"] == 15
