"""Tests for the Paper-Watch 觀察艙 registry (ADR-033 enforcement).

Every seam that matters is injectable — the observation-day counter takes an
``is_trading_day`` stub (a plain Mon–Fri lambda) and the store path is a tmp file,
so these tests touch no calendar extra, no network and no shared state. They pin
the ADR-033 clauses the registry turns from discipline into machine enforcement:
≤ 2 berths, a 90-day window, and the one-shot re-entry bar.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from backtest_platform.research.watch_registry import (
    MAX_ACTIVE_WATCHES,
    OBSERVATION_DAYS,
    AlreadyActiveError,
    CabinFullError,
    NotPaperWatchError,
    ReEnrollBlockedError,
    active_watches,
    enroll,
    expire_due,
    record_exit,
    status,
)

_WEEKDAY = staticmethod(lambda d: d.weekday() < 5)  # deterministic trading-day stub


def _weekday(d: date) -> bool:
    return d.weekday() < 5


# --------------------------------------------------------------------------- #
# enroll — happy path + derived status fields                                 #
# --------------------------------------------------------------------------- #
def test_enroll_creates_active_watch_with_90_day_expiry(tmp_path):
    reg = tmp_path / "watch.jsonl"
    on = date(2026, 7, 2)
    st = enroll("inst_flow", verdict_dsr=0.908, enrolled_on=on,
                is_trading_day=_weekday, path=reg)
    assert st.state == "active"
    assert st.strategy == "inst_flow"
    assert st.enrolled_on == on
    assert st.verdict_dsr == 0.908
    assert st.expiry_date == on + timedelta(days=OBSERVATION_DAYS)
    # freshly enrolled → full window remaining, zero trading days observed yet
    assert st.days_remaining == OBSERVATION_DAYS
    assert st.observed_trading_days == 0


def test_status_reflects_observed_trading_days_and_remaining(tmp_path):
    reg = tmp_path / "watch.jsonl"
    on = date(2026, 7, 2)  # Thursday
    enroll("inst_flow", verdict_dsr=0.908, enrolled_on=on, is_trading_day=_weekday, path=reg)
    # 12 calendar days later → count only the Mon–Fri in between
    later = on + timedelta(days=12)
    st = status("inst_flow", as_of=later, is_trading_day=_weekday, path=reg)
    expected = sum(1 for i in range(1, 13) if _weekday(on + timedelta(days=i)))
    assert st.observed_trading_days == expected
    assert st.days_remaining == OBSERVATION_DAYS - 12
    assert st.state == "active"


def test_status_none_for_unknown_strategy(tmp_path):
    assert status("never_seen", as_of=date(2026, 7, 2), path=tmp_path / "watch.jsonl") is None


# --------------------------------------------------------------------------- #
# verdict band gate — only DSR ∈ [0.90, 0.95) may enter the觀察艙            #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("dsr", [0.899, 0.80, 0.0])
def test_enroll_rejects_below_band_rejected_dsr(tmp_path, dsr):
    with pytest.raises(NotPaperWatchError):
        enroll("bad", verdict_dsr=dsr, enrolled_on=date(2026, 7, 2),
               is_trading_day=_weekday, path=tmp_path / "watch.jsonl")


@pytest.mark.parametrize("dsr", [0.95, 0.96, 1.0])
def test_enroll_rejects_at_or_above_deploy_bar_real_dsr(tmp_path, dsr):
    # DSR ≥ 0.95 is REAL (deployable), not观察艙 — enrolling it is a category error.
    with pytest.raises(NotPaperWatchError):
        enroll("too_good", verdict_dsr=dsr, enrolled_on=date(2026, 7, 2),
               is_trading_day=_weekday, path=tmp_path / "watch.jsonl")


# --------------------------------------------------------------------------- #
# cabin cap — at most MAX_ACTIVE_WATCHES berths                               #
# --------------------------------------------------------------------------- #
def test_third_concurrent_enroll_raises_cabin_full(tmp_path):
    reg = tmp_path / "watch.jsonl"
    on = date(2026, 7, 2)
    enroll("a", 0.91, on, is_trading_day=_weekday, path=reg)
    enroll("b", 0.92, on, is_trading_day=_weekday, path=reg)
    assert len(active_watches(as_of=on, is_trading_day=_weekday, path=reg)) == MAX_ACTIVE_WATCHES
    with pytest.raises(CabinFullError):
        enroll("c", 0.93, on, is_trading_day=_weekday, path=reg)


def test_berth_frees_after_expiry_allows_new_enroll(tmp_path):
    reg = tmp_path / "watch.jsonl"
    on = date(2026, 7, 2)
    enroll("a", 0.91, on, is_trading_day=_weekday, path=reg)
    enroll("b", 0.92, on, is_trading_day=_weekday, path=reg)
    # a expires → a berth frees → c may enter
    past_expiry = on + timedelta(days=OBSERVATION_DAYS + 1)
    expire_due(past_expiry, is_trading_day=_weekday, path=reg)
    st = enroll("c", 0.93, past_expiry, is_trading_day=_weekday, path=reg)
    assert st.state == "active"


# --------------------------------------------------------------------------- #
# one-shot — an expired/exited strategy cannot re-enter without new evidence   #
# --------------------------------------------------------------------------- #
def test_reenroll_after_expiry_blocked_without_evidence(tmp_path):
    reg = tmp_path / "watch.jsonl"
    on = date(2026, 7, 2)
    enroll("inst_flow", 0.908, on, is_trading_day=_weekday, path=reg)
    past = on + timedelta(days=OBSERVATION_DAYS + 1)
    expire_due(past, is_trading_day=_weekday, path=reg)
    assert status("inst_flow", as_of=past, is_trading_day=_weekday, path=reg).state == "expired"
    with pytest.raises(ReEnrollBlockedError):
        enroll("inst_flow", 0.912, past, is_trading_day=_weekday, path=reg)


def test_reenroll_after_expiry_allowed_with_evidence(tmp_path):
    reg = tmp_path / "watch.jsonl"
    on = date(2026, 7, 2)
    enroll("inst_flow", 0.908, on, is_trading_day=_weekday, path=reg)
    past = on + timedelta(days=OBSERVATION_DAYS + 1)
    expire_due(past, is_trading_day=_weekday, path=reg)
    st = enroll("inst_flow", 0.921, past, re_enroll_evidence="3mo live OOS DSR recomputed",
                is_trading_day=_weekday, path=reg)
    assert st.state == "active"
    assert st.re_enroll_evidence == "3mo live OOS DSR recomputed"


def test_reenroll_after_exit_blocked_without_evidence(tmp_path):
    reg = tmp_path / "watch.jsonl"
    on = date(2026, 7, 2)
    enroll("inst_flow", 0.908, on, is_trading_day=_weekday, path=reg)
    record_exit("inst_flow", reason="dropped after re-eval", path=reg)
    assert status("inst_flow", as_of=on, is_trading_day=_weekday, path=reg).state == "exited"
    with pytest.raises(ReEnrollBlockedError):
        enroll("inst_flow", 0.912, on + timedelta(days=1), is_trading_day=_weekday, path=reg)


def test_duplicate_enroll_of_active_strategy_raises(tmp_path):
    reg = tmp_path / "watch.jsonl"
    on = date(2026, 7, 2)
    enroll("inst_flow", 0.908, on, is_trading_day=_weekday, path=reg)
    with pytest.raises(AlreadyActiveError):
        enroll("inst_flow", 0.908, on, is_trading_day=_weekday, path=reg)


# --------------------------------------------------------------------------- #
# expire_due — transitions due watches, idempotent                            #
# --------------------------------------------------------------------------- #
def test_expire_due_marks_only_due_watches(tmp_path):
    reg = tmp_path / "watch.jsonl"
    early = date(2026, 4, 1)
    late = date(2026, 7, 2)
    enroll("old", 0.91, early, is_trading_day=_weekday, path=reg)
    enroll("new", 0.92, late, is_trading_day=_weekday, path=reg)
    # as-of past 'old' expiry but well within 'new' window
    as_of = early + timedelta(days=OBSERVATION_DAYS + 1)
    expired = expire_due(as_of, is_trading_day=_weekday, path=reg)
    assert expired == ["old"]
    assert status("old", as_of=as_of, is_trading_day=_weekday, path=reg).state == "expired"
    assert status("new", as_of=as_of, is_trading_day=_weekday, path=reg).state == "active"


def test_expire_due_is_idempotent(tmp_path):
    reg = tmp_path / "watch.jsonl"
    on = date(2026, 7, 2)
    enroll("inst_flow", 0.908, on, is_trading_day=_weekday, path=reg)
    past = on + timedelta(days=OBSERVATION_DAYS + 1)
    first = expire_due(past, is_trading_day=_weekday, path=reg)
    second = expire_due(past, is_trading_day=_weekday, path=reg)
    assert first == ["inst_flow"]
    assert second == []  # already expired → nothing new


def test_active_watches_excludes_expired(tmp_path):
    reg = tmp_path / "watch.jsonl"
    on = date(2026, 7, 2)
    enroll("a", 0.91, on, is_trading_day=_weekday, path=reg)
    enroll("b", 0.92, on, is_trading_day=_weekday, path=reg)
    past = on + timedelta(days=OBSERVATION_DAYS + 1)
    expire_due(past, is_trading_day=_weekday, path=reg)
    actives = active_watches(as_of=past, is_trading_day=_weekday, path=reg)
    assert [w.strategy for w in actives] == []  # both expired at this as-of


# --------------------------------------------------------------------------- #
# persistence — append-only JSONL, event-sourced                              #
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# integration — a real truth-gate verdict drives the enrollment decision        #
# --------------------------------------------------------------------------- #
def test_paper_watch_verdict_enrolls_but_rejected_verdict_is_refused(tmp_path):
    """The enroll band gate is aligned with the truth gate: a PAPER_WATCH verdict's
    DSR enrolls; a REJECTED verdict's DSR is out of band and is refused."""
    from backtest_platform.validation.two_stage_gate import (
        TruthGateInput,
        TruthVerdict,
        evaluate_truth_gate,
    )

    reg = tmp_path / "watch.jsonl"
    on = date(2026, 7, 2)

    # All hard-fails pass, DSR ∈ [0.90, 0.95) → PAPER_WATCH → admitted.
    watch_in = TruthGateInput(
        survivorship_clean=True, pre_registered=True,
        wfa_oos_positive_frac=1.0, dsr=0.908,
        slippage_sharpe=0.85, oos_holdout_sharpe=0.89,
    )
    assert evaluate_truth_gate(watch_in).verdict is TruthVerdict.PAPER_WATCH
    st = enroll("inst_flow", watch_in.dsr, on, is_trading_day=_weekday, path=reg)
    assert st.state == "active"

    # DSR < 0.90 → REJECTED → enroll refuses (out of the Paper-Watch band).
    rej_in = TruthGateInput(
        survivorship_clean=True, pre_registered=True,
        wfa_oos_positive_frac=1.0, dsr=0.80,
        slippage_sharpe=0.85, oos_holdout_sharpe=0.89,
    )
    assert evaluate_truth_gate(rej_in).verdict is TruthVerdict.REJECTED
    with pytest.raises(NotPaperWatchError):
        enroll("rejected_one", rej_in.dsr, on, is_trading_day=_weekday, path=reg)


def test_events_are_append_only_jsonl(tmp_path):
    reg = tmp_path / "watch.jsonl"
    on = date(2026, 7, 2)
    enroll("inst_flow", 0.908, on, is_trading_day=_weekday, path=reg)
    expire_due(on + timedelta(days=OBSERVATION_DAYS + 1), is_trading_day=_weekday, path=reg)
    lines = [json.loads(x) for x in reg.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert [e["event"] for e in lines] == ["enroll", "expire"]
    assert lines[0]["strategy"] == "inst_flow" and lines[0]["verdict_dsr"] == 0.908
    assert "at" in lines[0] and "at" in lines[1]
