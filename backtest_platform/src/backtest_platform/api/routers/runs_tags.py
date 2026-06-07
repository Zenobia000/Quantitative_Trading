"""``/runs/tag`` — run tagging (M3.3, owner: S5).

Pre-created in the M3 parallelization seam (registered in app.py) so run tagging
(8.H.4) fills this without touching ``runs.py`` or app.py. POST /runs/tag does
not collide with runs.py's GET /{run_id} (distinct method + literal path).
Typed-empty until ``research.run_tags_store`` lands.
"""
from __future__ import annotations

from fastapi import APIRouter

from backtest_platform.api.envelope import Envelope, pending

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("/tag", response_model=Envelope)
def tag_run() -> Envelope:
    return pending({"run_id": None, "tags": []})
