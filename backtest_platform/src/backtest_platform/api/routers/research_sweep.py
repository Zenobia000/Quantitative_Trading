"""``/research/sweep`` — async sweep jobs (M3.5, owner: S2).

Pre-created in the M3 parallelization seam (registered in app.py) so the async
job runner (8.H.6) fills these in its own file without touching app.py. Typed-empty
until the ``jobs/`` module persists job lifecycle (queued→running→done|failed).
"""
from __future__ import annotations

from fastapi import APIRouter

from backtest_platform.api.envelope import Envelope, pending

router = APIRouter(prefix="/research/sweep", tags=["research"])


@router.get("/{job_id}/status", response_model=Envelope)
def sweep_status(job_id: str) -> Envelope:
    return pending({"job_id": job_id, "status": None, "progress": None})
