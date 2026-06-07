"""``/research/validate`` — IS→WFA→OOS validation views (M3.6, owner: S3).

Split out of ``research.py`` in the M3 parallelization seam so the
validation+promotion service (8.H.7) owns a disjoint file. Endpoints are
typed-empty (``pending``) until ``research.promotion_service`` persists the
gate-state machine; ``validate/{run_id}/wfa`` is filled by S7 (WFA viz, 6.2.2).
"""
from __future__ import annotations

from fastapi import APIRouter

from backtest_platform.api.envelope import Envelope, pending

router = APIRouter(prefix="/research/validate", tags=["research"])


@router.get("/{run_id}/gate-state", response_model=Envelope)
def gate_state(run_id: str) -> Envelope:
    return pending({"run_id": run_id, "validation_status": None, "stage": None})


@router.get("/{run_id}/wfa", response_model=Envelope)
def validate_wfa(run_id: str) -> Envelope:
    return pending({"folds": [], "scatter": []})


@router.get("/{run_id}/redline", response_model=Envelope)
def validate_redline(run_id: str) -> Envelope:
    return pending({"pbo": None, "dsr_matrix": []})
