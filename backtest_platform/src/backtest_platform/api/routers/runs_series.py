"""``/runs/{id}`` computed series — equity / trades (M3.2, owner: S4).

Pre-created in the M3 parallelization seam (registered in app.py) so "expose
computed series" (8.H.3) fills these without touching ``runs.py`` or app.py.
Typed-empty until ``research.is_harness.run_and_judge_with_returns`` persists the
returns series + trade list into the runs ledger.

Path depth (/runs/{id}/equity) is more specific than runs.py's /{run_id}, so
route resolution is unambiguous regardless of include order.
"""
from __future__ import annotations

from fastapi import APIRouter

from backtest_platform.api.envelope import Envelope, pending

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("/{run_id}/equity", response_model=Envelope)
def run_equity(run_id: str) -> Envelope:
    return pending({"run_id": run_id, "equity": [], "drawdown": []})


@router.get("/{run_id}/trades", response_model=Envelope)
def run_trades(run_id: str) -> Envelope:
    return pending({"run_id": run_id, "trades": []})
