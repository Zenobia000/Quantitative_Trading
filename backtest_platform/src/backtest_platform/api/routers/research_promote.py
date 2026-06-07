"""``/research/promote`` — promotion state machine + audit (M3.6, owner: S3).

Split out of ``research.py`` in the M3 parallelization seam. Typed-empty until
``research.promotion_service`` persists stage transitions + immutable
``promotion_audit`` (8.H.7).
"""
from __future__ import annotations

from fastapi import APIRouter

from backtest_platform.api.envelope import Envelope, pending

router = APIRouter(prefix="/research/promote", tags=["research"])


@router.get("/{strategy_id}", response_model=Envelope)
def promote_state(strategy_id: str) -> Envelope:
    return pending({"strategy_id": strategy_id, "stage": "draft", "history": [], "gates": []})


@router.get("/{strategy_id}/audit", response_model=Envelope)
def promote_audit(strategy_id: str) -> Envelope:
    return pending([])
