"""Contract gate (doc 25 §2 / ADR-021): ``error`` is a structured object.

Every failure response carries ``error = {code, message, detail}`` where ``code``
is the stable enum the frontend switches on and HTTP status ↔ code is one-to-one.
These tests pin that contract so a regression (reverting to a bare string, or
mismapping a status) fails loudly.
"""
from __future__ import annotations


def _error(body: dict) -> dict:
    """Assert the envelope is a well-formed failure and return its error object."""
    assert body["success"] is False
    assert body["data"] is None
    err = body["error"]
    assert set(err) == {"code", "message", "detail"}, err
    assert isinstance(err["code"], str) and err["code"]
    assert isinstance(err["message"], str) and err["message"]
    return err


def test_404_maps_to_not_found_code(client):
    resp = client.get("/runs/no-such-run")
    assert resp.status_code == 404
    err = _error(resp.json())
    assert err["code"] == "NOT_FOUND"


def test_422_validation_carries_per_field_detail(client):
    # Empty body → missing required RunConfig fields → 422 VALIDATION_ERROR.
    resp = client.post("/runs", json={})
    assert resp.status_code == 422
    err = _error(resp.json())
    assert err["code"] == "VALIDATION_ERROR"
    assert isinstance(err["detail"], list) and err["detail"]
    assert {"loc", "msg"} <= set(err["detail"][0])


def test_success_envelope_has_null_error(client):
    body = client.get("/health").json()
    assert body["success"] is True
    assert body["error"] is None
