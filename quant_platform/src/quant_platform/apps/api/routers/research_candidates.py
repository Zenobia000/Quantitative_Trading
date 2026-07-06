"""``/research/candidates`` + ``/research/live-oos/queue`` — the candidate pool API.

The semi-automatic decision surface (rebuild Goal 4): list the folded candidate pool,
read one candidate with its full append-only decision trail, append a decision
(state-machine validated, override paths require a reason), and select a candidate
for live OOS (enqueues a queue item). Reuses the project envelope, the #176
pagination (``page`` + ``limit`` ≤ 500 + ``page_meta``) and the doc 25 §2 error
codes (404 ``{resource,id}`` · 400 ``{hint}`` · 409 ``{resource_id,state}`` · 422).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from quant_platform.apps.api.deps import (
    get_candidate_decisions_path,
    get_candidates_path,
    get_live_oos_queue_path,
)
from quant_platform.apps.api.envelope import DataSource, Envelope, ok, page_meta
from quant_platform.services.governance_release import live_oos_queue
from quant_platform.packages.adapters import candidate_store as cs
from quant_platform.packages.domain.candidate_state import DECISION_ACTIONS, IllegalTransitionError

router = APIRouter(prefix="/research", tags=["research-candidates"])

_TTL = 300


class DecisionRequest(BaseModel):
    """A candidate decision (keep / archive / rerun / mark_data_issue / unarchive)."""

    action: str
    reason: str | None = None
    label: str | None = None  # keep target: promising | weak | negative


class SelectLiveOOSRequest(BaseModel):
    """Select a candidate for live OOS (optionally overriding a not-recommended one)."""

    reason: str | None = None
    override: bool = False
    observation_kind: str = "paper_replay"


def _not_found(candidate_id: str) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"resource": "candidate", "id": candidate_id, "message": f"no candidate {candidate_id!r}"},
    )


@router.get("/candidates", response_model=Envelope)
def list_candidates(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    state: str | None = Query(None),
    strategy: str | None = Query(None),
    candidates_path: Path = Depends(get_candidates_path),
    decisions_path: Path = Depends(get_candidate_decisions_path),
) -> Envelope:
    """Paginated candidate pool (newest-created first), filterable by state / strategy."""
    cands = cs.list_candidates(
        state=state, strategy=strategy,
        candidates_path=candidates_path, decisions_path=decisions_path,
    )
    total = len(cands)
    start = (page - 1) * limit
    window = cands[start : start + limit]
    meta = {**page_meta(total, page, limit), "data_source": DataSource.LEDGER, "ttl": _TTL}
    return ok(window, meta=meta)


@router.get("/candidates/{candidate_id}", response_model=Envelope)
def get_candidate(
    candidate_id: str,
    candidates_path: Path = Depends(get_candidates_path),
    decisions_path: Path = Depends(get_candidate_decisions_path),
) -> Envelope:
    """One candidate with its full append-only ``decisions[]`` trail."""
    cand = cs.get_candidate(candidate_id, candidates_path=candidates_path, decisions_path=decisions_path)
    if cand is None:
        raise _not_found(candidate_id)
    return ok(cand, meta={"data_source": DataSource.LEDGER, "ttl": _TTL})


@router.post("/candidates/{candidate_id}/decision", response_model=Envelope, status_code=201)
def post_decision(
    candidate_id: str,
    req: DecisionRequest,
    candidates_path: Path = Depends(get_candidates_path),
    decisions_path: Path = Depends(get_candidate_decisions_path),
) -> Envelope:
    """Append a candidate decision (state-machine validated); returns the event."""
    if req.action not in DECISION_ACTIONS:
        raise HTTPException(
            status_code=422,
            detail={"message": f"action must be one of {sorted(DECISION_ACTIONS)}; "
                               "use /select-live-oos to select for live OOS"},
        )
    try:
        event = cs.record_decision(
            candidate_id, req.action, reason=req.reason, target_label=req.label,
            candidates_path=candidates_path, decisions_path=decisions_path,
        )
    except cs.CandidateNotFoundError:
        raise _not_found(candidate_id) from None
    except IllegalTransitionError as exc:
        raise HTTPException(status_code=400, detail={"hint": str(exc), "message": "illegal transition"}) from None
    except cs.MissingReasonError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc)}) from None
    return ok(event)


@router.post("/candidates/{candidate_id}/select-live-oos", response_model=Envelope, status_code=201)
def post_select_live_oos(
    candidate_id: str,
    req: SelectLiveOOSRequest,
    candidates_path: Path = Depends(get_candidates_path),
    decisions_path: Path = Depends(get_candidate_decisions_path),
    queue_path: Path = Depends(get_live_oos_queue_path),
) -> Envelope:
    """Select a candidate for live OOS: enqueue a queue item + append the decision."""
    try:
        out = cs.select_live_oos(
            candidate_id, reason=req.reason, override=req.override,
            observation_kind=req.observation_kind,
            candidates_path=candidates_path, decisions_path=decisions_path, queue_path=queue_path,
            enqueue=live_oos_queue.enqueue,
        )
    except cs.CandidateNotFoundError:
        raise _not_found(candidate_id) from None
    except cs.BlockedSelectionError as exc:
        cand = cs.get_candidate(candidate_id, candidates_path=candidates_path, decisions_path=decisions_path)
        raise HTTPException(
            status_code=409,
            detail={"resource_id": candidate_id, "state": (cand or {}).get("state"), "message": str(exc)},
        ) from None
    except cs.MissingReasonError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc)}) from None
    except IllegalTransitionError as exc:
        raise HTTPException(status_code=400, detail={"hint": str(exc), "message": "illegal transition"}) from None
    except ValueError as exc:  # unknown observation_kind
        raise HTTPException(status_code=422, detail={"message": str(exc)}) from None
    return ok(out["queue_item"])


@router.get("/live-oos/queue", response_model=Envelope)
def list_live_oos_queue(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    state: str | None = Query(None),
    queue_path: Path = Depends(get_live_oos_queue_path),
) -> Envelope:
    """Paginated live-OOS queue (human-selected candidates awaiting/undergoing OOS)."""
    items = live_oos_queue.list_queue(state=state, path=queue_path)
    total = len(items)
    start = (page - 1) * limit
    window = items[start : start + limit]
    meta = {**page_meta(total, page, limit), "data_source": DataSource.WATCH_REGISTRY, "ttl": _TTL}
    return ok(window, meta=meta)
