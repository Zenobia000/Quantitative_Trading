"""``/runs/tag`` — run tagging (M3.3, owner: S5).

Pre-created in the M3 parallelization seam (registered in app.py). Records
orthogonal labels on a run via ``run_tags_store``. POST /runs/tag does not
collide with runs.py's GET /{run_id} (distinct method + literal path). Request
model lives here so this stream owns a disjoint file.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backtest_platform.api.envelope import Envelope, ok
from backtest_platform.research import run_tags_store

router = APIRouter(prefix="/runs", tags=["runs"])


class RunTagRequest(BaseModel):
    """Replace the tag set on a run."""

    model_config = {"extra": "forbid"}

    run_id: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)


@router.post("/tag", response_model=Envelope)
def tag_run(req: RunTagRequest) -> Envelope:
    return ok(run_tags_store.tag_run(req.run_id, req.tags))
