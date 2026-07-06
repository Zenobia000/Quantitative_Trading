"""``/research/sweep`` — async sweep jobs (M3.5, owner: S2).

Submits a parameter-grid expansion as a background job (``jobs`` package) so the
research loop never blocks: POST returns a ``job_id``, GET polls status. v1 runs
the grid-expansion (the deterministic, data-free sweep *plan* the Sweep page
consumes pre-run) as the job body; per-config backtest execution (needs the
parquet loader) is the deferred heavy step.
"""
from __future__ import annotations

import itertools
import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from quant_platform.apps.api.envelope import Envelope, ok
from quant_platform.services.monitoring_ops.jobs import job_store, submit

router = APIRouter(prefix="/research/sweep", tags=["research"])


class SweepRequest(BaseModel):
    """A parameter grid to expand into the sweep plan."""

    model_config = {"extra": "forbid"}

    grid: dict[str, list[Any]] = Field(..., description="axis name → candidate values")


def _expand_plan(grid: dict[str, list[Any]]) -> dict[str, Any]:
    """Cartesian product of the grid → {n_configs, combos} (data-free plan)."""
    if not grid:
        return {"n_configs": 1, "combos": [{}]}
    names = list(grid)
    combos = [dict(zip(names, vals)) for vals in itertools.product(*(grid[n] for n in names))]
    return {"n_configs": len(combos), "combos": combos}


@router.post("", response_model=Envelope, status_code=202)
def submit_sweep(req: SweepRequest) -> Envelope:
    """Enqueue a sweep-plan job; returns {job_id, status} (202 Accepted)."""
    key = json.dumps(req.grid, sort_keys=True, default=str)
    grid = req.grid
    job = submit("sweep", key, lambda: _expand_plan(grid))
    return ok({"job_id": job.job_id, "status": job.status.value})


@router.get("/{job_id}/status", response_model=Envelope)
def sweep_status(job_id: str) -> Envelope:
    """Poll a sweep job's status; **404 NOT_FOUND** if the id is unknown (A4 / doc 25
    §5.2 — an unknown/expired job surfaces as an error, not an infinite pending)."""
    job = job_store.read_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail={"resource": "job", "id": job_id})
    return ok(job.to_dict())
