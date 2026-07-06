"""``GET /strategies`` — strategy catalog (replaces the deleted ``/presets``, ADR-028)."""
from __future__ import annotations


def test_list_strategies(client):
    body = client.get("/strategies").json()
    assert body["success"] is True
    data = body["data"]
    assert isinstance(data, list)
    # every catalog row is self-describing: name + title + config JSON-schema.
    for row in data:
        assert "name" in row
        assert "title" in row
        assert "config_schema" in row
    names = [row["name"] for row in data]
    assert "momentum" in names
