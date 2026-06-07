"""``/research`` registry + saved-views + trials (M3.3/M3.4, owner: S5).

Split out of ``research.py`` in the M3 parallelization seam so strategy
registry / saved-views / trials-DSR persistence (8.H.4 + 8.H.5) own a disjoint
file. Typed-empty until the JSONL stores (saved_views_store / run_tags_store /
trials_counter_store) land.
"""
from __future__ import annotations

from fastapi import APIRouter

from backtest_platform.api.envelope import Envelope, pending

router = APIRouter(prefix="/research", tags=["research"])


@router.get("/saved-views", response_model=Envelope)
def saved_views() -> Envelope:
    return pending([])


@router.post("/saved-views", response_model=Envelope)
def saved_views_create() -> Envelope:
    return pending({"id": "stub"})


@router.post("/trials/increment", response_model=Envelope)
def trials_increment() -> Envelope:
    return pending({"cumulative_trials": None})
