"""``/presets`` — list + single-preset lookup + unknown-name 404."""
from __future__ import annotations


def test_list_presets(client):
    body = client.get("/presets").json()
    assert body["success"] is True
    assert "v2" in body["data"]["presets"]
    assert "v3.1b" in body["data"]["presets"]
    # v2 baseline reproduces the original entry gate (all-AND, breakout-only).
    assert body["data"]["configs"]["v2"]["entry_min_layers"] == 4
    assert body["data"]["configs"]["v2"]["entry_min_structure"] == 2


def test_get_one_preset(client):
    body = client.get("/presets/v3.1b").json()
    assert body["success"] is True
    # dirB keeps structure strict (==2) while relaxing the transition gates.
    assert body["data"]["entry_min_structure"] == 2
    assert body["data"]["entry_min_layers"] == 3


def test_unknown_preset_returns_404_envelope(client):
    resp = client.get("/presets/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "NOT_FOUND"
    assert "does-not-exist" in body["error"]["message"]
