"""``/research/validate`` — IS→WFA→OOS validation views (M3.7, owner: S3).

Split out of ``research.py`` in the M3 parallelization seam. ``gate-state`` is
backed by ``promotion_service`` (persisted, audited validation transitions);
``wfa`` is filled by S7 (WFA viz, 6.2.2) and ``redline`` (PBO/DSR matrix) remains
typed-empty until its persistence lands.
"""
from __future__ import annotations

from fastapi import APIRouter

from backtest_platform.api.envelope import Envelope, ok, pending
from backtest_platform.research import promotion_service

router = APIRouter(prefix="/research/validate", tags=["research"])


@router.get("/{run_id}/gate-state", response_model=Envelope)
def gate_state(run_id: str) -> Envelope:
    """Current validation status + stage + transition history for a run."""
    return ok(promotion_service.gate_state(run_id))


@router.get("/{run_id}/wfa", response_model=Envelope)
def validate_wfa(run_id: str) -> Envelope:
    return pending({"folds": [], "scatter": []})


@router.get("/{run_id}/redline", response_model=Envelope)
def validate_redline(run_id: str) -> Envelope:
    return pending({"pbo": None, "dsr_matrix": []})
