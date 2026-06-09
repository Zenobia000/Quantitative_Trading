"""Validation + promotion service (8.H.7) — the orchestration layer.

Sits between the pure gate logic (``validation.gate_state`` / ``gate_machine``),
the runs ledger, and the append-only stores (``validation_store`` /
``promotion_store``). It is the single place that:

- judges a run's IS metrics and persists the verdict + transition (auditable),
- exposes a run's current validation state + history for the API,
- advances a strategy's promotion stage with strict ordered enforcement
  (draft → paper → live, no skips / no silent regress) into the immutable audit.

Pure orchestration over the stores; the threshold source stays ``DEFAULT_GATE``
and the stage logic lives here as data (``PROMOTION_STAGES``).
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backtest_platform.research import promotion_store, validation_store
from backtest_platform.validation.gate_machine import IS_VERDICT_TO_STATUS
from backtest_platform.validation.gate_state import GateStatus, evaluate_gate

#: Ordered promotion ladder. Index = ordinal; forward-by-one only.
PROMOTION_STAGES: tuple[str, ...] = ("draft", "paper", "live")

#: IS verdict → promotion stage. Only a full PASS validates; FAIL/INCOMPLETE stay draft.
_STAGE_BY_VERDICT: dict[GateStatus, str] = {
    GateStatus.PASS: "is_validated",
    GateStatus.FAIL: "draft",
    GateStatus.INCOMPLETE: "draft",
}


def _is_status(metrics: Mapping[str, float], gate=None) -> tuple[str, str]:
    """Map an IS gate verdict to (validation_status, stage).

    The status string comes from the shared ``IS_VERDICT_TO_STATUS`` bridge so
    the CLI (which reads it back via ``coerce_gate_state``) and this writer share
    one vocabulary — they cannot drift (code-audit 2026-06-10).
    """
    result = evaluate_gate(metrics) if gate is None else evaluate_gate(metrics, gate)
    verdict = result.status  # GateStatus.PASS | FAIL | INCOMPLETE
    return IS_VERDICT_TO_STATUS[verdict], _STAGE_BY_VERDICT[verdict]


def record_is_result(
    run_id: str,
    metrics: Mapping[str, float],
    gate=None,
    path=None,
) -> dict[str, Any]:
    """Judge a run's IS metrics and persist the transition; returns current state."""
    status, stage = _is_status(metrics, gate)
    validation_store.record(run_id, status, stage, note="IS gate evaluated", path=path)
    return {"run_id": run_id, "validation_status": status, "stage": stage}


def gate_state(run_id: str, path=None) -> dict[str, Any]:
    """Current validation state + full transition history for a run."""
    cur = validation_store.current(run_id, path)
    return {
        "run_id": run_id,
        "validation_status": cur["validation_status"] if cur else None,
        "stage": cur["stage"] if cur else None,
        "history": validation_store.history(run_id, path),
    }


def promote(
    strategy_id: str,
    to_stage: str,
    note: str = "",
    actor: str = "system",
    path=None,
) -> dict[str, Any]:
    """Advance a strategy one stage forward (draft→paper→live) into the audit.

    Raises ``ValueError`` on an unknown stage, a skip (>1 forward), or a regress
    — promotion is monotonic and accountable; the only legal move is the next
    stage up.
    """
    if to_stage not in PROMOTION_STAGES:
        raise ValueError(f"unknown stage {to_stage!r}; choose from {PROMOTION_STAGES}")
    current = promotion_store.current_stage(strategy_id, path)
    cur_i, to_i = PROMOTION_STAGES.index(current), PROMOTION_STAGES.index(to_stage)
    if to_i != cur_i + 1:
        raise ValueError(
            f"illegal promotion {current!r}→{to_stage!r}: only forward-by-one allowed "
            f"(next legal stage is {PROMOTION_STAGES[cur_i + 1] if cur_i + 1 < len(PROMOTION_STAGES) else 'none'})"
        )
    promotion_store.record(strategy_id, to_stage, note=note, actor=actor, path=path)
    return {"strategy_id": strategy_id, "stage": to_stage}


def promotion_state(strategy_id: str, path=None) -> dict[str, Any]:
    """Current stage + per-stage reached flags + immutable audit trail."""
    stage = promotion_store.current_stage(strategy_id, path)
    reached = PROMOTION_STAGES.index(stage)
    gates = [{"stage": s, "reached": i <= reached} for i, s in enumerate(PROMOTION_STAGES)]
    return {
        "strategy_id": strategy_id,
        "stage": stage,
        "gates": gates,
        "history": promotion_store.audit(strategy_id, path),
    }
