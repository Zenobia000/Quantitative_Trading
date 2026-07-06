"""``/research/promote`` — promotion state machine + audit (M3.7, owner: S3).

Split out of ``research.py`` in the M3 parallelization seam. Backed by
``promotion_service`` (strict ordered draft→paper→live transitions into the
immutable ``promotion_store`` audit). POST advances one stage; the GETs project
current stage + audit.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from quant_platform.apps.api.envelope import Envelope, ok
from quant_platform.apps.api.response_models import PromotionEvent, PromotionStateData
from quant_platform.services.governance_release import promotion_service

router = APIRouter(prefix="/research/promote", tags=["research"])


class PromoteRequest(BaseModel):
    """Advance a strategy one stage forward."""

    model_config = {"extra": "forbid"}

    to_stage: str = Field(..., description="next stage: paper | live")
    note: str = Field("", description="why (recorded in the immutable audit)")
    actor: str = Field("system", description="who triggered the promotion")


@router.get("/{strategy_id}", response_model=Envelope[PromotionStateData])
def promote_state(strategy_id: str) -> Envelope:
    """Current promotion stage + per-stage reached flags + audit trail."""
    return ok(promotion_service.promotion_state(strategy_id))


@router.post("/{strategy_id}", response_model=Envelope)
def promote_advance(strategy_id: str, req: PromoteRequest) -> Envelope:
    """Advance one stage forward.

    A domain ``ValueError`` (illegal skip / regress / unknown stage) maps to **400
    BAD_REQUEST** (A4 — domain errors are 400 uniformly, not 422 which is reserved
    for schema validation). ``promote`` is a pure ordered stage machine: every
    ``ValueError`` it raises is an *illegal transition*, so 400 is the whole story.
    The **409 IS_GATE_NOT_PASSED** code (``_STATUS_TO_CODE`` in ``app.py``) is the
    reserved backstop for a future gate-blocked advance; the current stage machine
    performs no IS-gate check (see ``test_promote_advance_and_audit``), so it is not
    raised here — the FE already gates by ``validation_status`` client-side."""
    try:
        return ok(
            promotion_service.promote(strategy_id, req.to_stage, note=req.note, actor=req.actor)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from None


@router.get("/{strategy_id}/audit", response_model=Envelope[list[PromotionEvent]])
def promote_audit(strategy_id: str) -> Envelope:
    """Immutable promotion audit trail for a strategy."""
    from quant_platform.services.governance_release import promotion_store

    return ok(promotion_store.audit(strategy_id))
