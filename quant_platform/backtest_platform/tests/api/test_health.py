"""``/health`` + envelope-shape smoke tests."""
from __future__ import annotations


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["error"] is None
    assert body["data"]["status"] == "ok"
    assert body["data"]["version"]


def test_envelope_shape_has_all_keys(client):
    """Every response carries the full {success,data,error,meta} contract."""
    body = client.get("/health").json()
    assert set(body) == {"success", "data", "error", "meta"}
