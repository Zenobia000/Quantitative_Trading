"""promotion_service + validation_store + promotion_store (8.H.7, S3)."""
from __future__ import annotations

import pytest

from backtest_platform.research import (
    promotion_service,
    promotion_store,
    validation_store,
)

_PASS = {"cagr": 0.25, "sharpe": 1.3, "slippage_sharpe": 1.1,
         "struct1_pct": 0.1, "churn_pct": 0.1, "avg_hold": 8.0}
_FAIL = {"cagr": -0.05, "sharpe": -0.2, "slippage_sharpe": -0.3,
         "struct1_pct": 0.7, "churn_pct": 0.5, "avg_hold": 2.0}


# ---- validation_store ----------------------------------------------------

def test_validation_event_log_is_append_only_audit(tmp_path):
    p = tmp_path / "val.jsonl"
    validation_store.record("r1", "is_fail", "draft", path=p)
    validation_store.record("r1", "is_pass", "is_validated", path=p)
    hist = validation_store.history("r1", path=p)
    assert [e["validation_status"] for e in hist] == ["is_fail", "is_pass"]  # full audit kept
    assert validation_store.current("r1", path=p)["validation_status"] == "is_pass"


def test_validation_current_none_when_absent(tmp_path):
    assert validation_store.current("ghost", path=tmp_path / "v.jsonl") is None


# ---- promotion_service: IS verdict --------------------------------------

def test_record_is_result_pass_and_fail(tmp_path):
    p = tmp_path / "val.jsonl"
    assert promotion_service.record_is_result("rp", _PASS, path=p)["validation_status"] == "is_pass"
    assert promotion_service.record_is_result("rf", _FAIL, path=p)["validation_status"] == "is_fail"
    state = promotion_service.gate_state("rp", path=p)
    assert state["stage"] == "is_validated"
    assert len(state["history"]) == 1


def test_record_is_incomplete_when_metric_missing(tmp_path):
    p = tmp_path / "val.jsonl"
    out = promotion_service.record_is_result("ri", {"cagr": 0.2}, path=p)
    assert out["validation_status"] == "incomplete"


# ---- promotion_service: ordered promotion -------------------------------

def test_promote_forward_by_one(tmp_path):
    p = tmp_path / "promo.jsonl"
    assert promotion_service.promote("s1", "paper", note="ok", path=p)["stage"] == "paper"
    assert promotion_service.promote("s1", "live", note="go", actor="zeno", path=p)["stage"] == "live"
    st = promotion_service.promotion_state("s1", path=p)
    assert st["stage"] == "live"
    assert [g["reached"] for g in st["gates"]] == [True, True, True]
    assert len(st["history"]) == 2  # immutable audit


def test_promote_rejects_skip(tmp_path):
    with pytest.raises(ValueError, match="forward-by-one"):
        promotion_service.promote("s2", "live", path=tmp_path / "p.jsonl")  # draft→live skips paper


def test_promote_rejects_unknown_stage(tmp_path):
    with pytest.raises(ValueError, match="unknown stage"):
        promotion_service.promote("s3", "production", path=tmp_path / "p.jsonl")


def test_promotion_state_default_draft(tmp_path):
    st = promotion_service.promotion_state("never", path=tmp_path / "p.jsonl")
    assert st["stage"] == "draft"
    assert [g["reached"] for g in st["gates"]] == [True, False, False]


def test_promotion_audit_trail(tmp_path):
    p = tmp_path / "promo.jsonl"
    promotion_service.promote("s4", "paper", note="first", path=p)
    trail = promotion_store.audit("s4", path=p)
    assert trail[0]["note"] == "first" and trail[0]["stage"] == "paper"
