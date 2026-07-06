"""S5 persistence stores — saved-views / run-tags / trials-counter (JSONL/JSON)."""
from __future__ import annotations

import pytest

from quant_platform.packages.adapters import run_tags_store, saved_views_store, trials_counter_store


# ---- saved_views_store --------------------------------------------------

def test_saved_views_create_then_list(tmp_path) -> None:
    p = tmp_path / "sv.jsonl"
    rec = saved_views_store.create_view("my view", {"cols": ["cagr"], "f": {"strategy": "four_layer"}}, path=p)
    assert rec["name"] == "my view"
    assert rec["id"]
    views = saved_views_store.list_views(path=p)
    assert len(views) == 1 and views[0]["id"] == rec["id"]


def test_saved_views_id_is_deterministic(tmp_path) -> None:
    p = tmp_path / "sv.jsonl"
    a = saved_views_store.create_view("v", {"x": 1}, path=p)
    b = saved_views_store.create_view("v", {"x": 1}, path=p)
    assert a["id"] == b["id"]  # same content → same id
    assert len(saved_views_store.list_views(path=p)) == 1  # latest-per-id wins


def test_saved_views_empty(tmp_path) -> None:
    assert saved_views_store.list_views(path=tmp_path / "none.jsonl") == []


# ---- run_tags_store -----------------------------------------------------

def test_run_tags_roundtrip_and_dedupe(tmp_path) -> None:
    p = tmp_path / "tags.jsonl"
    rec = run_tags_store.tag_run("run1", ["candidate", "candidate", "smallcap"], path=p)
    assert rec["tags"] == ["candidate", "smallcap"]  # deduped, order kept
    assert run_tags_store.tags_for("run1", path=p) == ["candidate", "smallcap"]


def test_run_tags_latest_wins(tmp_path) -> None:
    p = tmp_path / "tags.jsonl"
    run_tags_store.tag_run("run1", ["a"], path=p)
    run_tags_store.tag_run("run1", ["b", "c"], path=p)
    assert run_tags_store.tags_for("run1", path=p) == ["b", "c"]
    assert run_tags_store.tags_for("absent", path=p) == []


# ---- trials_counter_store -----------------------------------------------

def test_trials_increment_accumulates(tmp_path) -> None:
    p = tmp_path / "trials.json"
    space = {"box_period": [40, 60], "confirm_days": [1, 2]}
    assert trials_counter_store.increment(space, 1, path=p) == 1
    assert trials_counter_store.increment(space, 5, path=p) == 6
    assert trials_counter_store.cumulative(space, path=p) == 6


def test_trials_separate_param_spaces(tmp_path) -> None:
    p = tmp_path / "trials.json"
    trials_counter_store.increment({"a": 1}, 3, path=p)
    trials_counter_store.increment({"b": 2}, 2, path=p)
    assert trials_counter_store.cumulative({"a": 1}, path=p) == 3
    assert trials_counter_store.cumulative({"b": 2}, path=p) == 2


def test_trials_increment_rejects_zero(tmp_path) -> None:
    with pytest.raises(ValueError):
        trials_counter_store.increment({"a": 1}, 0, path=tmp_path / "t.json")


def test_trials_cumulative_unknown_is_zero(tmp_path) -> None:
    assert trials_counter_store.cumulative({"z": 9}, path=tmp_path / "none.json") == 0
