"""``/research/promote`` — promotion state machine + audit (M3.7, owner: S3).

Split out of ``research.py`` in the M3 parallelization seam. Backed by
``promotion_service`` (strict ordered draft→paper→live transitions into the
immutable ``promotion_store`` audit). POST advances one stage; the GETs project
current stage + audit.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backtest_platform.api.envelope import Envelope, ok
from backtest_platform.research import promotion_service

router = APIRouter(prefix="/research/promote", tags=["research"])


class PromoteRequest(BaseModel):
    """Advance a strategy one stage forward."""

    model_config = {"extra": "forbid"}

    to_stage: str = Field(..., description="next stage: paper | live")
    note: str = Field("", description="why (recorded in the immutable audit)")
    actor: str = Field("system", description="who triggered the promotion")


@router.get("/{strategy_id}", response_model=Envelope)
def promote_state(strategy_id: str) -> Envelope:
    """Current promotion stage + per-stage reached flags + audit trail."""
    return ok(promotion_service.promotion_state(strategy_id))


@router.post("/{strategy_id}", response_model=Envelope)
def promote_advance(strategy_id: str, req: PromoteRequest) -> Envelope:
    """Advance one stage forward; 422 on an illegal skip / regress / unknown stage."""
    try:
        return ok(
            promotion_service.promote(strategy_id, req.to_stage, note=req.note, actor=req.actor)
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.get("/{strategy_id}/audit", response_model=Envelope)
def promote_audit(strategy_id: str) -> Envelope:
    """Immutable promotion audit trail for a strategy."""
    from backtest_platform.research import promotion_store

    return ok(promotion_store.audit(strategy_id))
