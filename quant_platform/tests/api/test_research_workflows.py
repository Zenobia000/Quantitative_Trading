"""api.research_workflows — POST /research/workflows/{workflow} + GET /{strategy}."""
from __future__ import annotations

from fastapi.testclient import TestClient

from quant_platform.apps.api.app import create_app

client = TestClient(create_app())


def test_get_workflows_inst_flow():
    r = client.get("/research/workflows/inst_flow")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert "doe" in data["data"]["workflows"]
    assert data["data"]["strategy"] == "inst_flow"


def test_get_workflows_four_layer_only_doe():
    r = client.get("/research/workflows/four_layer")
    assert r.status_code == 200
    assert r.json()["data"]["workflows"] == ["doe"]


def test_get_workflows_unknown_strategy_400():
    r = client.get("/research/workflows/nonexistent_xyz")
    assert r.status_code == 400


def test_post_doe_queues_job():
    r = client.post("/research/workflows/doe", json={"strategy": "template"})
    assert r.status_code == 202
    data = r.json()
    assert data["success"] is True
    assert "job_id" in data["data"]
    assert data["data"]["status"] in ("queued", "running", "done")


def test_post_doe_unknown_strategy_400():
    r = client.post("/research/workflows/doe", json={"strategy": "nonexistent"})
    assert r.status_code == 400


def test_post_unknown_workflow_404():
    r = client.post("/research/workflows/invalid_wf", json={"strategy": "momentum"})
    assert r.status_code == 404


def test_post_build_universe_is_a_known_workflow():
    """build_universe must be registered (400 for a bad strategy, never 404).

    Uses an unknown strategy so the config getter fails before enqueue — proving the
    workflow key is recognized without spawning a live FinLab ingest job.
    """
    r = client.post("/research/workflows/build_universe", json={"strategy": "nonexistent"})
    assert r.status_code == 400


# --- overrides re-validation at the boundary (審查缺陷 #11) -------------------
# ``model_copy(update=...)`` bypassed every validator, so a bad override enqueued a
# job that blew up deep inside the workflow thread. Overrides must re-validate at
# the HTTP edge → 422 VALIDATION_ERROR, never a silent 202.


def test_post_doe_valid_override_still_queues():
    r = client.post(
        "/research/workflows/doe",
        json={"strategy": "momentum", "overrides": {"hypothesis_prefix": "EXP"}},
    )
    assert r.status_code == 202, r.text
    assert r.json()["success"] is True


def test_post_doe_override_wrong_type_422():
    r = client.post(
        "/research/workflows/doe",
        json={"strategy": "momentum", "overrides": {"is_start": "not-a-date"}},
    )
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_post_doe_override_unknown_field_422():
    r = client.post(
        "/research/workflows/doe",
        json={"strategy": "momentum", "overrides": {"nonexistent_knob": 1}},
    )
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_post_doe_override_inverted_window_422():
    r = client.post(
        "/research/workflows/doe",
        json={
            "strategy": "momentum",
            "overrides": {"is_start": "2025-01-01", "is_end": "2020-01-01"},
        },
    )
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
