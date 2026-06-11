"""``/research`` saved-views + trials persistence (M3.3/M3.4, owner: S5).

Split out of ``research.py`` in the M3 parallelization seam. Backs the research
Runs-Table saved presets and the cumulative trials counter (DSR deflation
guardrail) with append-only JSONL / JSON stores. Request models live here (not in
the shared schemas.py) so this stream owns a fully disjoint file.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backtest_platform.api.envelope import Envelope, ok
from backtest_platform.api.response_models import SavedView, TrialsData
from backtest_platform.research import saved_views_store, trials_counter_store

router = APIRouter(prefix="/research", tags=["research"])


class SavedViewCreate(BaseModel):
    """A named Runs-Table view (columns + filters), mirroring the FE URL state."""

    model_config = {"extra": "forbid"}

    name: str = Field(..., min_length=1)
    query: dict[str, Any] = Field(default_factory=dict, description="columns / filters state")


class TrialsIncrement(BaseModel):
    """Record N additional trials searched over a param-space (DSR deflation)."""

    model_config = {"extra": "forbid"}

    param_space: Any = Field(..., description="param-space dict (or stable key string)")
    count: int = Field(1, ge=1, description="trials to add")


@router.get("/saved-views", response_model=Envelope[list[SavedView]])
def saved_views() -> Envelope:
    return ok(saved_views_store.list_views())


@router.post("/saved-views", response_model=Envelope[SavedView], status_code=201)
def saved_views_create(req: SavedViewCreate) -> Envelope:
    return ok(saved_views_store.create_view(req.name, req.query))


@router.post("/trials/increment", response_model=Envelope[TrialsData])
def trials_increment(req: TrialsIncrement) -> Envelope:
    total = trials_counter_store.increment(req.param_space, req.count)
    return ok({"cumulative_trials": total})
