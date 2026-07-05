"""research.live_oos_queue — enqueue / list / get (rebuild Goal 4)."""
from __future__ import annotations

import pytest

from backtest_platform.governance import live_oos_queue as q


@pytest.fixture
def path(tmp_path):
    return tmp_path / "queue.jsonl"


def test_enqueue_paper_replay_has_null_berth_fields(path):
    item = q.enqueue("cand_x", "momentum", "eval_1", selection_reason="look",
                     recommendation_at_selection="not_recommended", observation_kind="paper_replay",
                     path=path, at="2026-07-03T08:30:00+08:00")
    assert item["state"] == "queued"
    assert item["observation"]["kind"] == "paper_replay"
    assert item["observation"]["enrolled_on"] is None
    assert item["observation"]["watch_registry_ref"] is None
    assert item["observation"]["position_size"] == 0.0


def test_enqueue_paper_watch_berth_sets_ref_and_band(path):
    item = q.enqueue("cand_x", "inst_flow", "eval_2", selection_reason="berth",
                     recommendation_at_selection="eligible", observation_kind="paper_watch_berth",
                     dsr=0.908, path=path, at="2026-07-03T09:00:00+08:00")
    assert item["observation"]["watch_registry_ref"] == "inst_flow"
    assert item["observation"]["dsr_band"] == "paper_watch"  # dsr_band(0.908) → PAPER_WATCH → lowercased


def test_unknown_kind_raises(path):
    with pytest.raises(ValueError, match="observation_kind"):
        q.enqueue("c", "s", "e", selection_reason=None, recommendation_at_selection="eligible",
                  observation_kind="teleport", path=path)


def test_list_and_get(path):
    a = q.enqueue("c1", "s1", "e1", selection_reason=None, recommendation_at_selection="eligible",
                  path=path, at="2026-07-01T08:00:00+08:00")
    q.enqueue("c2", "s2", "e2", selection_reason=None, recommendation_at_selection="eligible",
              path=path, at="2026-07-02T08:00:00+08:00")
    items = q.list_queue(path=path)
    assert len(items) == 2
    assert items[0]["selected_at"] >= items[1]["selected_at"]  # newest first
    assert q.get_queue_item(a["queue_id"], path=path)["candidate_id"] == "c1"


def test_list_filters_by_state(path):
    q.enqueue("c1", "s1", "e1", selection_reason=None, recommendation_at_selection="eligible", path=path)
    assert len(q.list_queue(state="queued", path=path)) == 1
    assert len(q.list_queue(state="running", path=path)) == 0


def test_get_missing_returns_none(path):
    assert q.get_queue_item("nope", path=path) is None


def test_enqueue_records_numeric_verdict_dsr(path):
    # Goal 10: the consumer needs the numeric DSR (not just the band) to re-enroll a berth.
    item = q.enqueue("cand_x", "inst_flow", "eval_2", selection_reason="berth",
                     recommendation_at_selection="eligible", observation_kind="paper_watch_berth",
                     dsr=0.908, path=path)
    assert item["observation"]["verdict_dsr"] == 0.908


# --------------------------------------------------------------------------- #
# advance — folded state transitions (Goal 10 state machine)                   #
# --------------------------------------------------------------------------- #
def test_advance_folds_latest_state(path):
    item = q.enqueue("c1", "s1", "e1", selection_reason=None, recommendation_at_selection="eligible",
                     observation_kind="paper_watch_berth", dsr=0.91, path=path)
    q.advance(item["queue_id"], to_state="running", path=path,
              observation_patch={"observed_trading_days": 3, "days_remaining": 87})
    folded = q.get_queue_item(item["queue_id"], path=path)
    assert folded["state"] == "running"
    assert folded["observation"]["observed_trading_days"] == 3
    # unchanged audit fields survive the copy-restamp
    assert folded["candidate_id"] == "c1"
    assert "updated_at" in folded


def test_advance_attaches_run_block(path):
    item = q.enqueue("c1", "s1", "e1", selection_reason=None, recommendation_at_selection="not_recommended",
                     observation_kind="paper_replay", path=path)
    q.advance(item["queue_id"], to_state="completed", path=path,
              run={"run_id": "paper_replay_s1_20260703", "gate_status": "PAPER_WATCH"})
    folded = q.get_queue_item(item["queue_id"], path=path)
    assert folded["state"] == "completed"
    assert folded["run"]["run_id"] == "paper_replay_s1_20260703"


def test_advance_unknown_state_raises(path):
    item = q.enqueue("c1", "s1", "e1", selection_reason=None, recommendation_at_selection="eligible", path=path)
    with pytest.raises(ValueError, match="queue state"):
        q.advance(item["queue_id"], to_state="teleported", path=path)


def test_advance_unknown_id_raises(path):
    with pytest.raises(ValueError, match="no queue item"):
        q.advance("loq_missing", to_state="running", path=path)
