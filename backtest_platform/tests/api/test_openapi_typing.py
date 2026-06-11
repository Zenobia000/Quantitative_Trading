"""OpenAPI typing regression — Envelope[T] response models land in the schema.

Guards that typed endpoints carry a real ``data`` schema (so the frontend's
generated ``api.gen.ts`` gets types, not a generic blob) and — paired with the
field-preservation tests in test_runs.py (extra='allow' never drops data) — that
typing the contract can't silently break a consumer.
"""
from __future__ import annotations


def test_typed_models_are_in_openapi_components(client):
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    for model in ("RunSummary", "RunRecord", "SweepEstimate", "CompareReportData"):
        assert model in schemas, f"{model} missing from OpenAPI components"
    # the contract field is declared (typed), not erased
    assert "run_id" in schemas["RunSummary"]["properties"]
    # extra='allow' → additionalProperties kept so undeclared fields pass through
    assert schemas["RunSummary"].get("additionalProperties") is not False


def test_runs_endpoints_reference_typed_envelopes(client):
    paths = client.get("/openapi.json").json()["paths"]
    # GET /runs response references a typed Envelope wrapping RunSummary
    ref = paths["/runs"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    assert "Envelope_" in ref and "RunSummary" in ref  # e.g. Envelope_list_RunSummary__
