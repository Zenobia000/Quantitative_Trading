"""research.candidate_store — ingest, decisions, select-live-oos (rebuild Goal 4)."""
from __future__ import annotations

import pytest

from backtest_platform.research import candidate_store as cs
from backtest_platform.research import live_oos_queue
from backtest_platform.research.candidate_state import IllegalTransitionError


def _result(strategy="momentum", label="Weak", truth=None, reco="not_recommended", eval_id="eval_1"):
    return {
        "evaluation_id": eval_id,
        "strategy": strategy,
        "profile": "quick_triage",
        "verdict": {"label": label, "truth_verdict": truth, "live_oos_recommendation": reco},
        "headline_metrics": {"sharpe": 1.02, "cagr": 0.16, "max_drawdown": 0.27, "dsr": 0.908,
                             "trades": 60, "avg_turnover": 0.83, "oos_holdout_sharpe": 0.89},
        "scorecards": [{"category": "profitability", "status": "warn"}],
        "universe": {"survivorship_clean": True},
        "report_pack_ref": "reports/research_runs/x/manifest.json",
    }


@pytest.fixture
def store(tmp_path):
    return {
        "candidates_path": tmp_path / "cand.jsonl",
        "decisions_path": tmp_path / "dec.jsonl",
        "queue_path": tmp_path / "queue.jsonl",
    }


def _sp(store):  # candidate-store kwargs
    return {"candidates_path": store["candidates_path"], "decisions_path": store["decisions_path"]}


def test_ingest_creates_candidate_and_auto_labels(store):
    cand = cs.ingest_evaluation(_result(), **_sp(store))
    assert cand["candidate_id"] == "cand_momentum"
    assert cand["state"] == "triaged"
    assert cand["decisions"][0]["action"] == "auto_label"
    assert cand["decisions"][0]["actor"] == "system"


def test_ingest_data_issue_marks_state(store):
    cand = cs.ingest_evaluation(_result(label="Data Issue", reco="blocked"), **_sp(store))
    assert cand["state"] == "data_issue"
    assert cand["decisions"][0]["action"] == "mark_data_issue"


def test_reingest_preserves_human_state(store):
    cs.ingest_evaluation(_result(), **_sp(store))
    cs.record_decision("cand_momentum", "keep", target_label="promising", **_sp(store))
    cand = cs.ingest_evaluation(_result(eval_id="eval_2", label="Weak"), **_sp(store))
    assert cand["state"] == "promising"  # re-eval does not reset the human label
    assert cand["latest_evaluation_id"] == "eval_2"


def test_keep_transitions_to_label(store):
    cs.ingest_evaluation(_result(), **_sp(store))
    dec = cs.record_decision("cand_momentum", "keep", target_label="weak", **_sp(store))
    assert dec["to_state"] == "weak"
    assert dec["from_state"] == "triaged"


def test_archive_requires_reason(store):
    cs.ingest_evaluation(_result(), **_sp(store))
    with pytest.raises(cs.MissingReasonError):
        cs.record_decision("cand_momentum", "archive", **_sp(store))
    dec = cs.record_decision("cand_momentum", "archive", reason="landscape overfit", **_sp(store))
    assert dec["to_state"] == "archived"


def test_illegal_transition_raises(store):
    cs.ingest_evaluation(_result(), **_sp(store))
    with pytest.raises(IllegalTransitionError):
        cs.record_decision("cand_momentum", "unarchive", **_sp(store))  # not archived


def test_decision_on_unknown_candidate(store):
    with pytest.raises(cs.CandidateNotFoundError):
        cs.record_decision("cand_ghost", "keep", target_label="weak", **_sp(store))


def test_select_live_oos_eligible_no_reason(store):
    cs.ingest_evaluation(_result(reco="eligible", truth="PAPER_WATCH", label="Weak"), **_sp(store))
    cs.record_decision("cand_momentum", "keep", target_label="weak", **_sp(store))
    out = cs.select_live_oos("cand_momentum", **_sp(store), queue_path=store["queue_path"], enqueue=live_oos_queue.enqueue)
    assert out["decision"]["action"] == "select_live_oos"
    assert out["decision"]["to_state"] == "live_oos_selected"
    assert out["queue_item"]["state"] == "queued"
    assert out["decision"]["queue_ref"] == out["queue_item"]["queue_id"]


def test_select_not_recommended_requires_reason(store):
    cs.ingest_evaluation(_result(reco="not_recommended"), **_sp(store))
    with pytest.raises(cs.MissingReasonError):
        cs.select_live_oos("cand_momentum", **_sp(store), queue_path=store["queue_path"], enqueue=live_oos_queue.enqueue)
    out = cs.select_live_oos("cand_momentum", reason="worth a paper look", override=True,
                             **_sp(store), queue_path=store["queue_path"], enqueue=live_oos_queue.enqueue)
    assert out["decision"]["action"] == "override_select"
    assert out["queue_item"]["override"] is True


def test_select_blocked_without_override_is_blocked(store):
    cs.ingest_evaluation(_result(reco="blocked", label="Negative", truth="REJECTED"), **_sp(store))
    with pytest.raises(cs.BlockedSelectionError):
        cs.select_live_oos("cand_momentum", reason="x", **_sp(store), queue_path=store["queue_path"], enqueue=live_oos_queue.enqueue)


def test_select_blocked_with_override_enqueues(store):
    cs.ingest_evaluation(_result(reco="blocked", label="Negative", truth="REJECTED"), **_sp(store))
    out = cs.select_live_oos("cand_momentum", reason="manual override", override=True,
                             **_sp(store), queue_path=store["queue_path"], enqueue=live_oos_queue.enqueue)
    assert out["queue_item"]["override"] is True
    assert len(live_oos_queue.list_queue(path=store["queue_path"])) == 1


def test_list_candidates_filters(store):
    cs.ingest_evaluation(_result(strategy="momentum"), **_sp(store))
    cs.ingest_evaluation(_result(strategy="inst_flow", eval_id="eval_if"), **_sp(store))
    assert len(cs.list_candidates(**_sp(store))) == 2
    assert len(cs.list_candidates(strategy="inst_flow", **_sp(store))) == 1
    assert len(cs.list_candidates(state="triaged", **_sp(store))) == 2


def test_no_orphan_queue_on_illegal_select(store):
    cs.ingest_evaluation(_result(reco="eligible", truth="PAPER_WATCH"), **_sp(store))
    cs.select_live_oos("cand_momentum", **_sp(store), queue_path=store["queue_path"], enqueue=live_oos_queue.enqueue)
    # already live_oos_selected → a second select is an illegal transition, no new queue row
    with pytest.raises(IllegalTransitionError):
        cs.select_live_oos("cand_momentum", **_sp(store), queue_path=store["queue_path"], enqueue=live_oos_queue.enqueue)
    assert len(live_oos_queue.list_queue(path=store["queue_path"])) == 1
