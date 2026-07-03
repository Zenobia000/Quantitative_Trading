"""``/research/branches`` — branch-experiment lineage + compare (rebuild Goal 9).

An explicit strategy-iteration surface above the evaluation ledger: fork a branch
from a parent ``EvaluationResult`` with a ``config_delta``, list a strategy's / a
parent's branches, run the branch (quick_triage, synchronous — profile-light), and
read the branch-vs-parent headline delta table with a deterministic decision.

Every branch links its parent (``parent_evaluation_id`` / ``parent_run_id`` /
``strategy``); the parent's records are never mutated (Goal 9 acceptance). Reuses the
project envelope, the #176 pagination, and the doc 25 §2 error codes: 404
``{resource,id}`` (unknown parent/branch) · 409 ``{resource_id,state}`` (overlay-only
branch not re-runnable) · 422 (illegal config_delta key/value — Pydantic + the
``branch_store`` classifier).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backtest_platform.api.deps import (
    get_branch_evaluator,
    get_branches_path,
    get_evaluations_path,
)
from backtest_platform.api.envelope import DataSource, Envelope, ok, page_meta
from backtest_platform.research import branch_store as bs

router = APIRouter(prefix="/research", tags=["research-branches"])

_TTL = 300


class ConfigDeltaEntry(BaseModel):
    """One config change ``{key, to, from?}`` — ``from`` is advisory (server resolves
    the authoritative value from the parent config)."""

    key: str = Field(..., min_length=1)
    to: Any = None
    from_: Any = Field(None, alias="from")

    model_config = {"populate_by_name": True}


class CreateBranchRequest(BaseModel):
    """Fork a branch from a parent evaluation with an explicit config delta."""

    parent_evaluation_id: str = Field(..., min_length=1)
    config_delta: list[ConfigDeltaEntry] = Field(..., min_length=1)
    origin: str = "manual"
    note: str | None = None
    profile: str = "quick_triage"


def _branch_404(branch_id: str) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"resource": "branch", "id": branch_id, "message": f"no branch {branch_id!r}"},
    )


@router.post("/branches", response_model=Envelope, status_code=201)
def create_branch(
    req: CreateBranchRequest,
    branches_path: Path = Depends(get_branches_path),
    evaluations_path: Path = Depends(get_evaluations_path),
) -> Envelope:
    """Fork a branch from a parent evaluation. 404 unknown parent; 422 illegal delta."""
    delta = [{"key": e.key, "to": e.to, "from": e.from_} for e in req.config_delta]
    try:
        branch = bs.create_branch(
            req.parent_evaluation_id, delta, origin=req.origin, note=req.note, profile=req.profile,
            branches_path=branches_path, evaluations_path=evaluations_path,
        )
    except bs.ParentNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"resource": "evaluation", "id": req.parent_evaluation_id, "message": str(exc)},
        ) from None
    except bs.IllegalDeltaError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc)}) from None
    return ok(branch, meta={"data_source": DataSource.LEDGER})


@router.get("/branches", response_model=Envelope)
def list_branches(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    strategy: str | None = Query(None),
    parent_evaluation_id: str | None = Query(None),
    parent_run_id: str | None = Query(None),
    branches_path: Path = Depends(get_branches_path),
) -> Envelope:
    """Paginated branch list (newest-created first), filterable by strategy / parent."""
    branches = bs.list_branches(
        strategy=strategy, parent_evaluation_id=parent_evaluation_id,
        parent_run_id=parent_run_id, branches_path=branches_path,
    )
    total = len(branches)
    start = (page - 1) * limit
    window = branches[start : start + limit]
    meta = {**page_meta(total, page, limit), "data_source": DataSource.LEDGER, "ttl": _TTL}
    return ok(window, meta=meta)


@router.get("/branches/{branch_id}", response_model=Envelope)
def get_branch(
    branch_id: str, branches_path: Path = Depends(get_branches_path)
) -> Envelope:
    """One branch (latest folded record)."""
    branch = bs.get_branch(branch_id, branches_path=branches_path)
    if branch is None:
        raise _branch_404(branch_id)
    return ok(branch, meta={"data_source": DataSource.LEDGER, "ttl": _TTL})


@router.post("/branches/{branch_id}/evaluate", response_model=Envelope, status_code=201)
def evaluate_branch(
    branch_id: str,
    branches_path: Path = Depends(get_branches_path),
    evaluations_path: Path = Depends(get_evaluations_path),
    evaluator: Any = Depends(get_branch_evaluator),
) -> Envelope:
    """Run the branch config (quick_triage, synchronous) → backfill its evaluation id.

    404 unknown branch; 409 for an overlay-only branch the runner cannot re-run
    (would reproduce the parent). Returns the evaluated branch record.
    """
    try:
        out = evaluator(
            branch_id, branches_path=branches_path, evaluations_path=evaluations_path,
        )
    except bs.BranchNotFoundError:
        raise _branch_404(branch_id) from None
    except bs.BranchNotEvaluableError as exc:
        raise HTTPException(
            status_code=409,
            detail={"resource_id": branch_id, "state": "draft", "message": str(exc)},
        ) from None
    return ok(out["branch"], meta={"data_source": DataSource.LEDGER})


@router.get("/branches/{branch_id}/compare", response_model=Envelope)
def compare_branch(
    branch_id: str,
    branches_path: Path = Depends(get_branches_path),
    evaluations_path: Path = Depends(get_evaluations_path),
) -> Envelope:
    """Branch-vs-parent headline delta table + a deterministic decision. 404 unknown."""
    try:
        result = bs.compare_branch(
            branch_id, branches_path=branches_path, evaluations_path=evaluations_path,
        )
    except bs.BranchNotFoundError:
        raise _branch_404(branch_id) from None
    return ok(result, meta={"data_source": DataSource.LEDGER, "ttl": _TTL})
