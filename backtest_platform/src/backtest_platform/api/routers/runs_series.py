"""``/runs/{id}`` computed series — equity / trades (M3.2, owner: S4).

Serves the per-run series sidecar (``research.run_series_store``) that the run
executor (``run_and_judge_persist``) writes at run time. The lean runs ledger
holds metadata + metrics; the heavy equity/drawdown/trade arrays live in the
sidecar and are loaded only here. A run that predates the sidecar (or yielded no
tradable window) returns a typed-empty ``pending`` envelope rather than 404.

Path depth (/runs/{id}/equity) is more specific than runs.py's /{run_id}, so
route resolution is unambiguous regardless of include order.
"""
from __future__ import annotations

from fastapi import APIRouter

from backtest_platform.api.envelope import Envelope, ok, pending
from backtest_platform.research import run_series_store

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("/{run_id}/equity", response_model=Envelope)
def run_equity(run_id: str) -> Envelope:
    """Equity curve + running drawdown for one run (from the series sidecar)."""
    series = run_series_store.read_series(run_id)
    if series is None:
        return pending({"run_id": run_id, "equity": [], "drawdown": []})
    return ok(
        {
            "run_id": run_id,
            "equity": series.get("equity", []),
            "drawdown": series.get("drawdown", []),
        }
    )


@router.get("/{run_id}/trades", response_model=Envelope)
def run_trades(run_id: str) -> Envelope:
    """Per-trade list ({ret, hold, entry_structure}) for one run."""
    series = run_series_store.read_series(run_id)
    if series is None:
        return pending({"run_id": run_id, "trades": []})
    return ok({"run_id": run_id, "trades": series.get("trades", [])})
