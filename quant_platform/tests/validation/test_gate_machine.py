"""gate_machine — IS→WFA→OOS irreversible workflow gate + OOS sealed vault.

Upgrades the v0.1 read-only ``gate_state`` judge into a stateful, *enforcing*
workflow machine (8.G.3-full). A run must clear each gate in order; you cannot
skip a gate, you cannot silently regress to a higher state, and — critically —
you cannot peek at the sealed OOS data before IS+WFA have passed (the classic
look-ahead leak that turns OOS into in-sample).

No IO. Synthetic / injected data only; ``evaluate_gate`` does the real judging.
"""
from __future__ import annotations

import pytest

from quant_platform.services.research_validation.validation.gate_machine import (
    IS_VERDICT_TO_STATUS,
    GateState,
    OOSSealedError,
    ValidationGate,
    coerce_gate_state,
    derive_is_state,
)
from quant_platform.services.research_validation.validation.gate_state import GateStatus

# A metrics dict that clears the real DEFAULT_GATE (mirrors test_gate_state._PASS).
_IS_PASS = {
    "cagr": 0.25, "sharpe": 1.5, "slippage_sharpe": 1.2,
    "struct1_pct": 0.10, "churn_pct": 0.10, "avg_hold": 8.0,
}
# Real v3 numbers — must be judged FAIL by the gate.
_IS_FAIL = {
    "cagr": -0.024, "sharpe": -0.43, "slippage_sharpe": -0.43,
    "struct1_pct": 0.716, "churn_pct": 0.274, "avg_hold": 5.5,
}
# Missing a gated metric → evaluate_gate returns INCOMPLETE (not PASS).
_IS_INCOMPLETE = {k: v for k, v in _IS_PASS.items() if k != "slippage_sharpe"}


# --------------------------------------------------------------------------- #
# initial state
# --------------------------------------------------------------------------- #
def test_starts_pending() -> None:
    g = ValidationGate()
    assert g.state is GateState.PENDING
    assert g.n_resets == 0


def test_state_is_a_str_enum() -> None:
    assert issubclass(GateState, str)
    assert GateState.IS_PASS == "IS_PASS"


# --------------------------------------------------------------------------- #
# happy path: full IS → WFA → OOS → APPROVED transition
# --------------------------------------------------------------------------- #
def test_full_happy_path() -> None:
    g = ValidationGate()
    assert g.submit_is(_IS_PASS) is GateState.IS_PASS
    assert g.state is GateState.IS_PASS

    assert g.submit_wfa(True) is GateState.WFA_PASS
    assert g.state is GateState.WFA_PASS

    assert g.submit_oos(True) is GateState.OOS_PASS
    assert g.state is GateState.OOS_PASS

    assert g.approve() is GateState.APPROVED
    assert g.state is GateState.APPROVED


# --------------------------------------------------------------------------- #
# submit_is delegates the verdict to evaluate_gate
# --------------------------------------------------------------------------- #
def test_submit_is_pass_moves_to_is_pass() -> None:
    g = ValidationGate()
    assert g.submit_is(_IS_PASS) is GateState.IS_PASS


def test_submit_is_fail_moves_to_failed() -> None:
    g = ValidationGate()
    assert g.submit_is(_IS_FAIL) is GateState.FAILED
    assert g.state is GateState.FAILED


def test_submit_is_incomplete_metrics_is_failed_not_pass() -> None:
    """An INCOMPLETE gate (missing metric) must never be treated as a pass."""
    g = ValidationGate()
    assert g.submit_is(_IS_INCOMPLETE) is GateState.FAILED


def test_submit_is_records_last_gate_result() -> None:
    g = ValidationGate()
    g.submit_is(_IS_PASS)
    assert g.last_is_result is not None
    assert g.last_is_result.passed is True


# --------------------------------------------------------------------------- #
# gate-skipping is blocked (must clear the previous gate first)
# --------------------------------------------------------------------------- #
def test_cannot_submit_wfa_before_is() -> None:
    g = ValidationGate()
    with pytest.raises(ValueError):
        g.submit_wfa(True)


def test_cannot_submit_oos_before_wfa() -> None:
    g = ValidationGate()
    g.submit_is(_IS_PASS)  # IS_PASS, but WFA not done
    with pytest.raises(ValueError):
        g.submit_oos(True)


def test_cannot_approve_before_oos() -> None:
    g = ValidationGate()
    g.submit_is(_IS_PASS)
    g.submit_wfa(True)  # WFA_PASS, but OOS not done
    with pytest.raises(ValueError):
        g.approve()


def test_cannot_submit_is_twice() -> None:
    """IS is only valid from PENDING; resubmitting must be rejected, not silently rerun."""
    g = ValidationGate()
    g.submit_is(_IS_PASS)
    with pytest.raises(ValueError):
        g.submit_is(_IS_PASS)


# --------------------------------------------------------------------------- #
# a failed gate stops the workflow (FAILED is terminal-ish)
# --------------------------------------------------------------------------- #
def test_failed_is_blocks_wfa() -> None:
    g = ValidationGate()
    g.submit_is(_IS_FAIL)
    assert g.state is GateState.FAILED
    with pytest.raises(ValueError):
        g.submit_wfa(True)


def test_failed_wfa_moves_to_failed_and_blocks_oos() -> None:
    g = ValidationGate()
    g.submit_is(_IS_PASS)
    assert g.submit_wfa(False) is GateState.FAILED
    with pytest.raises(ValueError):
        g.submit_oos(True)


def test_failed_oos_moves_to_failed_and_blocks_approve() -> None:
    g = ValidationGate()
    g.submit_is(_IS_PASS)
    g.submit_wfa(True)
    assert g.submit_oos(False) is GateState.FAILED
    with pytest.raises(ValueError):
        g.approve()


# --------------------------------------------------------------------------- #
# irreversibility: no regressing to a lower-ordinal state except via reset()
# --------------------------------------------------------------------------- #
def test_no_backward_transition_via_normal_methods() -> None:
    """Once WFA_PASS, you cannot re-run IS to drop back to IS_PASS."""
    g = ValidationGate()
    g.submit_is(_IS_PASS)
    g.submit_wfa(True)
    # submit_is is only legal from PENDING → blocked here
    with pytest.raises(ValueError):
        g.submit_is(_IS_PASS)
    assert g.state is GateState.WFA_PASS  # state unchanged


def test_approved_is_terminal() -> None:
    g = ValidationGate()
    g.submit_is(_IS_PASS)
    g.submit_wfa(True)
    g.submit_oos(True)
    g.approve()
    for call in (lambda: g.submit_is(_IS_PASS),
                 lambda: g.submit_wfa(True),
                 lambda: g.submit_oos(True),
                 lambda: g.approve()):
        with pytest.raises(ValueError):
            call()
    assert g.state is GateState.APPROVED


# --------------------------------------------------------------------------- #
# reset(): the only legal way back to PENDING, and it counts
# --------------------------------------------------------------------------- #
def test_reset_returns_to_pending_and_counts() -> None:
    g = ValidationGate()
    g.submit_is(_IS_PASS)
    g.submit_wfa(True)
    assert g.reset() is GateState.PENDING
    assert g.state is GateState.PENDING
    assert g.n_resets == 1


def test_reset_accumulates() -> None:
    g = ValidationGate()
    g.submit_is(_IS_FAIL)
    g.reset()
    g.submit_is(_IS_FAIL)
    g.reset()
    assert g.n_resets == 2
    assert g.state is GateState.PENDING


def test_reset_clears_last_is_result() -> None:
    g = ValidationGate()
    g.submit_is(_IS_PASS)
    g.reset()
    assert g.last_is_result is None


def test_reset_then_rerun_full_path() -> None:
    """After a reset you can drive the whole workflow again from scratch."""
    g = ValidationGate()
    g.submit_is(_IS_FAIL)
    g.reset()
    assert g.submit_is(_IS_PASS) is GateState.IS_PASS
    assert g.submit_wfa(True) is GateState.WFA_PASS
    assert g.submit_oos(True) is GateState.OOS_PASS
    assert g.approve() is GateState.APPROVED


# --------------------------------------------------------------------------- #
# OOS sealed vault: no peeking before IS+WFA cleared
# --------------------------------------------------------------------------- #
def _loader() -> str:
    return "OOS_BUNDLE"


def test_read_oos_sealed_before_wfa_raises_and_counts_blocked() -> None:
    g = ValidationGate()
    with pytest.raises(OOSSealedError):
        g.read_oos(_loader)
    assert g.n_oos_blocked == 1
    assert g.n_oos_access == 0


def test_read_oos_sealed_at_is_pass_still_raises() -> None:
    """IS_PASS is not enough — WFA must clear before OOS unseals."""
    g = ValidationGate()
    g.submit_is(_IS_PASS)
    with pytest.raises(OOSSealedError):
        g.read_oos(_loader)
    assert g.n_oos_blocked == 1


def test_read_oos_does_not_call_loader_when_sealed() -> None:
    g = ValidationGate()
    calls = {"n": 0}

    def spy() -> str:
        calls["n"] += 1
        return "LEAK"

    with pytest.raises(OOSSealedError):
        g.read_oos(spy)
    assert calls["n"] == 0  # loader never touched → no leak path


def test_read_oos_unsealed_at_wfa_pass_returns_loader_and_counts_access() -> None:
    g = ValidationGate()
    g.submit_is(_IS_PASS)
    g.submit_wfa(True)
    assert g.read_oos(_loader) == "OOS_BUNDLE"
    assert g.n_oos_access == 1
    assert g.n_oos_blocked == 0


def test_read_oos_unsealed_at_oos_pass_and_approved() -> None:
    g = ValidationGate()
    g.submit_is(_IS_PASS)
    g.submit_wfa(True)
    g.submit_oos(True)
    assert g.read_oos(_loader) == "OOS_BUNDLE"
    g.approve()
    assert g.read_oos(_loader) == "OOS_BUNDLE"
    assert g.n_oos_access == 2


def test_oos_blocked_and_access_counts_are_independent() -> None:
    g = ValidationGate()
    with pytest.raises(OOSSealedError):  # blocked (sealed)
        g.read_oos(_loader)
    g.submit_is(_IS_PASS)
    g.submit_wfa(True)
    g.read_oos(_loader)  # access (unsealed)
    assert g.n_oos_blocked == 1
    assert g.n_oos_access == 1


def test_reset_reseals_oos_vault() -> None:
    """After reset the workflow is back at PENDING, so OOS must re-seal."""
    g = ValidationGate()
    g.submit_is(_IS_PASS)
    g.submit_wfa(True)
    g.read_oos(_loader)  # unsealed access
    g.reset()
    with pytest.raises(OOSSealedError):
        g.read_oos(_loader)
    assert g.n_oos_blocked == 1


def test_oos_sealed_error_is_runtime_error() -> None:
    assert issubclass(OOSSealedError, RuntimeError)


# ---- canonical IS-status vocabulary bridge (code-audit 2026-06-10) -------- #

def test_derive_is_state_matches_submit_is() -> None:
    # the stateless derivation applies the same rule as the stateful machine
    assert derive_is_state(_IS_PASS) is GateState.IS_PASS
    assert derive_is_state(_IS_FAIL) is GateState.FAILED
    assert derive_is_state({}) is GateState.FAILED  # INCOMPLETE → non-pass


def test_coerce_gate_state_accepts_enum_vocabulary() -> None:
    assert coerce_gate_state("IS_PASS") is GateState.IS_PASS
    assert coerce_gate_state("APPROVED") is GateState.APPROVED
    assert coerce_gate_state("FAILED") is GateState.FAILED


def test_coerce_gate_state_accepts_persisted_verdict_vocabulary() -> None:
    # the vocabulary promotion_service actually writes — previously dropped on the floor
    assert coerce_gate_state("is_pass") is GateState.IS_PASS
    assert coerce_gate_state("is_fail") is GateState.FAILED
    assert coerce_gate_state("incomplete") is GateState.FAILED  # cannot-evaluate → non-pass


def test_coerce_gate_state_unknown_or_empty_is_none() -> None:
    assert coerce_gate_state(None) is None
    assert coerce_gate_state("") is None
    assert coerce_gate_state("garbage") is None


def test_verdict_vocabulary_round_trips_writer_to_reader() -> None:
    # the drift guard: every status promotion_service can WRITE must be a value
    # the CLI can READ back to a coherent GateState — writer/reader cannot diverge.
    assert coerce_gate_state(IS_VERDICT_TO_STATUS[GateStatus.PASS]) is GateState.IS_PASS
    assert coerce_gate_state(IS_VERDICT_TO_STATUS[GateStatus.FAIL]) is GateState.FAILED
    assert coerce_gate_state(IS_VERDICT_TO_STATUS[GateStatus.INCOMPLETE]) is GateState.FAILED
