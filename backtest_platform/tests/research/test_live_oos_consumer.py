"""Live-OOS queue consumer (rebuild Goal 10) — enroll / replay / sync, injected seams.

The enroll / status / replay seams are injected, so these tests wire tiny stubs — no
JSONL registry, no calendar, no network. They pin the Goal 10 acceptance: only queued
items run (an unselected candidate is never touched), a berth is enrolled ``queued →
running`` while a full cabin waits, a paper_replay runs once ``queued → completed``, and
a running berth re-folds to paused / expired / completed as the registry moves.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from backtest_platform.research import live_oos_consumer as consumer
from backtest_platform.research import live_oos_queue as q
from backtest_platform.research.watch_registry import (
    CabinFullError,
    NotPaperWatchError,
    OBSERVATION_DAYS,
    WatchStatus,
)

_AS_OF = date(2026, 7, 3)


@pytest.fixture
def path(tmp_path):
    return tmp_path / "queue.jsonl"


def _berth_status(strategy: str, *, state: str = "active", observed: int = 5, remaining: int = 85) -> WatchStatus:
    on = date(2026, 6, 1)
    return WatchStatus(
        strategy=strategy, state=state, enrolled_on=on, verdict_dsr=0.908,
        expiry_date=on + timedelta(days=OBSERVATION_DAYS),
        observed_trading_days=observed, days_remaining=remaining,
    )


def _enqueue_berth(path, strategy="inst_flow", dsr=0.908):
    return q.enqueue(f"cand_{strategy}", strategy, f"eval_{strategy}", selection_reason="band",
                     recommendation_at_selection="eligible", observation_kind="paper_watch_berth",
                     dsr=dsr, path=path)


def _enqueue_replay(path, strategy="four_layer_resonance"):
    return q.enqueue(f"cand_{strategy}", strategy, f"eval_{strategy}", selection_reason="probe",
                     recommendation_at_selection="not_recommended", override=True,
                     override_reason="worth a look", observation_kind="paper_replay", path=path)


# --------------------------------------------------------------------------- #
# acceptance #1 — ONLY queued items run; nothing else is auto-triggered        #
# --------------------------------------------------------------------------- #
def test_empty_queue_is_a_no_op(path):
    calls: list = []
    report = consumer.consume_queue(
        _AS_OF, queue_path=path,
        enroll_fn=lambda *a: calls.append(a) or _berth_status("x"),
        run_paper_replay_fn=lambda *a: calls.append(a),
    )
    assert report == consumer.ConsumeReport()
    assert calls == []  # nothing enrolled, nothing replayed


def test_only_queued_berth_is_enrolled(path):
    item = _enqueue_berth(path)
    seen: list = []

    def _enroll(strategy, dsr, as_of):
        seen.append((strategy, dsr, as_of))
        return _berth_status(strategy)

    report = consumer.consume_queue(_AS_OF, queue_path=path, enroll_fn=_enroll)
    assert report.enrolled == (item["queue_id"],)
    assert seen == [("inst_flow", 0.908, _AS_OF)]  # enrolled with the recorded numeric DSR
    folded = q.get_queue_item(item["queue_id"], path=path)
    assert folded["state"] == "running"
    assert folded["observation"]["observed_trading_days"] == 5  # berth folded onto the item


def test_running_berth_is_not_re_enrolled(path):
    # A berth already consumed (running) must never be enrolled again on the next tick.
    item = _enqueue_berth(path)
    q.advance(item["queue_id"], to_state="running", path=path,
              observation_patch={"observed_trading_days": 5, "days_remaining": 85})
    enroll_calls: list = []
    consumer.consume_queue(
        _AS_OF, queue_path=path,
        enroll_fn=lambda *a: enroll_calls.append(a) or _berth_status("inst_flow"),
        watch_status_fn=lambda s, d: _berth_status(s, observed=5, remaining=85),
    )
    assert enroll_calls == []  # running item skips the enroll path entirely


# --------------------------------------------------------------------------- #
# ≤ 2 berths — a full cabin leaves the item queued (retried next tick)          #
# --------------------------------------------------------------------------- #
def test_cabin_full_leaves_item_queued(path):
    item = _enqueue_berth(path)

    def _enroll(strategy, dsr, as_of):
        raise CabinFullError("觀察艙 full: 2/2 berths occupied")

    report = consumer.consume_queue(_AS_OF, queue_path=path, enroll_fn=_enroll)
    assert report.enrolled == ()
    assert report.skipped == ((item["queue_id"], "cabin_full"),)
    assert q.get_queue_item(item["queue_id"], path=path)["state"] == "queued"  # still waiting


def test_band_refusal_leaves_item_queued(path):
    item = _enqueue_berth(path, dsr=0.80)  # below the PAPER_WATCH band

    def _enroll(strategy, dsr, as_of):
        raise NotPaperWatchError("DSR 0.8 is not in the Paper-Watch band")

    report = consumer.consume_queue(_AS_OF, queue_path=path, enroll_fn=_enroll)
    assert report.enrolled == ()
    assert report.skipped[0][0] == item["queue_id"]
    assert "enroll_refused" in report.skipped[0][1]
    assert q.get_queue_item(item["queue_id"], path=path)["state"] == "queued"


# --------------------------------------------------------------------------- #
# paper_replay — runs once on consumption, queued → completed                   #
# --------------------------------------------------------------------------- #
def test_queued_replay_runs_once_and_completes(path):
    item = _enqueue_replay(path)
    runs: list = []

    class _Result:
        run_id = "paper_replay_four_layer_resonance_20260703"
        gate_status = "PAPER_WATCH"

    def _run(strategy, as_of):
        runs.append((strategy, as_of))
        return _Result()

    report = consumer.consume_queue(_AS_OF, queue_path=path, run_paper_replay_fn=_run)
    assert report.replayed == (item["queue_id"],)
    assert runs == [("four_layer_resonance", _AS_OF)]
    folded = q.get_queue_item(item["queue_id"], path=path)
    assert folded["state"] == "completed"
    assert folded["run"]["run_id"] == "paper_replay_four_layer_resonance_20260703"
    assert folded["run"]["gate_status"] == "PAPER_WATCH"


def test_failed_replay_stays_queued_and_does_not_raise(path):
    item = _enqueue_replay(path)

    def _boom(strategy, as_of):
        raise RuntimeError("finlab quota exhausted")

    report = consumer.consume_queue(_AS_OF, queue_path=path, run_paper_replay_fn=_boom)
    assert report.replayed == ()
    assert report.skipped[0][0] == item["queue_id"]
    assert "replay_failed" in report.skipped[0][1]
    assert q.get_queue_item(item["queue_id"], path=path)["state"] == "queued"  # retryable


# --------------------------------------------------------------------------- #
# state sync — a running berth re-folds to paused / expired / completed         #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "registry_state,expected_queue_state",
    [("paused", "paused"), ("expired", "expired"), ("exited", "completed"), ("active", "running")],
)
def test_running_berth_syncs_registry_state(path, registry_state, expected_queue_state):
    item = _enqueue_berth(path)
    # consume once → running
    consumer.consume_queue(_AS_OF, queue_path=path, enroll_fn=lambda *a: _berth_status("inst_flow"))
    # next tick: the registry has moved
    report = consumer.consume_queue(
        _AS_OF, queue_path=path,
        watch_status_fn=lambda s, d: _berth_status(s, state=registry_state, observed=9, remaining=81),
    )
    folded = q.get_queue_item(item["queue_id"], path=path)
    assert folded["state"] == expected_queue_state
    if expected_queue_state != "running":
        assert (item["queue_id"], expected_queue_state) in report.synced


def test_sync_refreshes_observation_clock_without_state_change(path):
    item = _enqueue_berth(path)
    consumer.consume_queue(_AS_OF, queue_path=path, enroll_fn=lambda *a: _berth_status("inst_flow", observed=5, remaining=85))
    # still active, but the observation clock advanced 5 → 12 trading days
    consumer.consume_queue(
        _AS_OF, queue_path=path,
        watch_status_fn=lambda s, d: _berth_status(s, observed=12, remaining=78),
    )
    folded = q.get_queue_item(item["queue_id"], path=path)
    assert folded["state"] == "running"
    assert folded["observation"]["observed_trading_days"] == 12
    assert folded["observation"]["days_remaining"] == 78


# --------------------------------------------------------------------------- #
# mixed queue — a selected berth and an unselected-elsewhere replay coexist     #
# --------------------------------------------------------------------------- #
def test_mixed_queue_consumes_each_kind_by_its_own_path(path):
    berth = _enqueue_berth(path, strategy="inst_flow")
    replay = _enqueue_replay(path, strategy="four_layer_resonance")

    class _Result:
        run_id = "rid"
        gate_status = "REJECTED"

    report = consumer.consume_queue(
        _AS_OF, queue_path=path,
        enroll_fn=lambda *a: _berth_status("inst_flow"),
        run_paper_replay_fn=lambda *a: _Result(),
    )
    assert report.enrolled == (berth["queue_id"],)
    assert report.replayed == (replay["queue_id"],)
    assert q.get_queue_item(berth["queue_id"], path=path)["state"] == "running"
    assert q.get_queue_item(replay["queue_id"], path=path)["state"] == "completed"
