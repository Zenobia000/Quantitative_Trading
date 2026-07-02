"""``/runs/{id}`` computed series — equity / trades / candles (M3.2, owner: S4).

Serves the per-run series sidecar (``research.run_series_store``) that the run
executor (``run_and_judge_persist``) writes at run time. The lean runs ledger
holds metadata + metrics; the heavy equity/drawdown/trade arrays live in the
sidecar and are loaded only here. A run that predates the sidecar (or yielded no
tradable window) returns a typed-empty ``pending`` envelope rather than 404.

``/candles`` (Trade Review K-line) additionally reads the runs ledger — for the
run's ``stocks`` + IS window — and the parquet OHLC cache, then overlays entry/
exit markers re-derived from the run's signal pipeline (``research.run_candles``).
A missing symbol in the cache yields a typed-empty ``pending`` envelope, not a 500.

Path depth (/runs/{id}/equity) is more specific than runs.py's /{run_id}, so
route resolution is unambiguous regardless of include order.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from backtest_platform.api.deps import get_runs_path
from backtest_platform.api.envelope import Envelope, ok, pending
from backtest_platform.research import run_candles, run_series_store
from backtest_platform.research.runs_store import read_runs

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


def _find_run(run_id: str, runs_path: Path) -> dict[str, Any] | None:
    """Latest ledger record for ``run_id`` (last append wins), or ``None``."""
    match: dict[str, Any] | None = None
    for record in read_runs(runs_path):
        if str(record.get("run_id")) == run_id:
            match = record
    return match


@router.get("/{run_id}/candles", response_model=Envelope)
def run_candles_endpoint(
    run_id: str,
    stock: str | None = Query(
        None, description="symbol to chart; default = the run's first stock"
    ),
    runs_path: Path = Depends(get_runs_path),
) -> Envelope:
    """Daily OHLC candles + entry ▲ / exit ▼ markers for one stock of a run.

    Reads the run's ``stocks`` + IS window from the ledger (404 if the run is
    unknown), then loads OHLC from the parquet cache and overlays markers derived
    from the run's own signal pipeline (``research.run_candles``). A run with no
    stocks, or a symbol absent from the parquet cache, returns a typed-empty
    ``pending`` envelope — never a 500 or fabricated data (frontend/GOAL.md #8).
    """
    record = _find_run(run_id, runs_path)
    if record is None:
        raise HTTPException(status_code=404, detail=f"run {run_id!r} not found")

    stocks = [str(s) for s in (record.get("stocks") or [])]
    if not stocks:
        return pending(
            {"run_id": run_id, "stock": None, "stocks": [], "candles": [], "markers": []}
        )

    # Honor an explicit, in-run symbol; otherwise fall back to the first stock
    # (never serve OHLC for a symbol the run never traded).
    selected = stock if stock in stocks else stocks[0]
    base = {"run_id": run_id, "stock": selected, "stocks": stocks}

    payload = run_candles.build_candles(record, selected)
    if payload is None:
        return pending({**base, "candles": [], "markers": []})
    return ok({**base, "candles": payload["candles"], "markers": payload["markers"]})
