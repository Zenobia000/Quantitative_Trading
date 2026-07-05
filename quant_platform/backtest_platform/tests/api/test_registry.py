"""S5 endpoints — /research/saved-views, /research/trials/increment, /runs/tag.

Isolated by pointing each store's module-level DEFAULT path at tmp_path (the
stores resolve it at call time), so these exercise the real store end-to-end.
"""
from __future__ import annotations

import pytest

from backtest_platform.research.adapters import (
    run_tags_store,
    saved_views_store,
    trials_counter_store,
)


@pytest.fixture
def isolate_stores(tmp_path, monkeypatch):
    monkeypatch.setattr(saved_views_store, "DEFAULT_SAVED_VIEWS_PATH", tmp_path / "sv.jsonl")
    monkeypatch.setattr(run_tags_store, "DEFAULT_RUN_TAGS_PATH", tmp_path / "tags.jsonl")
    monkeypatch.setattr(trials_counter_store, "DEFAULT_TRIALS_PATH", tmp_path / "trials.json")


def test_saved_views_create_and_list(client, isolate_stores):
    assert client.get("/research/saved-views").json()["data"] == []
    created = client.post(
        "/research/saved-views", json={"name": "v3 winners", "query": {"preset": "v3"}}
    )
    assert created.status_code == 201
    vid = created.json()["data"]["id"]
    listed = client.get("/research/saved-views").json()["data"]
    assert [v["id"] for v in listed] == [vid]


def test_saved_views_rejects_blank_name(client, isolate_stores):
    assert client.post("/research/saved-views", json={"name": "", "query": {}}).status_code == 422


def test_trials_increment_accumulates(client, isolate_stores):
    space = {"param_space": {"box": [40, 60]}, "count": 2}
    assert client.post("/research/trials/increment", json=space).json()["data"]["cumulative_trials"] == 2
    assert client.post("/research/trials/increment", json=space).json()["data"]["cumulative_trials"] == 4


def test_tag_run_dedupes(client, isolate_stores):
    body = client.post("/runs/tag", json={"run_id": "r1", "tags": ["a", "a", "b"]}).json()
    assert body["success"] is True
    assert body["data"]["tags"] == ["a", "b"]
