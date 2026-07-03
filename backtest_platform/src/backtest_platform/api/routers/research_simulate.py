"""``POST /research/simulate`` — research-only what-if over a finished run (Goal 8).

Reruns *nothing*: it reads the run's persisted equity/trades sidecar
(``run_series_store``) and recomputes before/after metrics for a set of what-if
knobs (cost multiplier, slippage, capacity, stop-loss, take-profit). The original
config / ledger / report pack are never touched and the result is never persisted
— it is a sandbox answer the frontend labels "research-only", returning a
*branch suggestion* (a config delta description) rather than mutating anything
(spec Goal 8 acceptance). The heavy lifting is the pure ``research.simulation``
module; this router only resolves the run, derives the cost-model scalars from the
record, and wraps the result in the standard envelope.

Errors follow doc 25 §2: ``404 {resource:"run", id}`` for an unknown run,
``422 [{loc,msg}]`` for out-of-range parameters (Pydantic field bounds, handled by
the app-wide ``RequestValidationError`` hook).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backtest_platform.api.deps import get_runs_path
from backtest_platform.api.envelope import DataSource, Envelope, ok
from backtest_platform.research import run_series_store, simulation
from backtest_platform.research.runs_store import read_runs

router = APIRouter(prefix="/research", tags=["research-simulation"])

_RESEARCH_TTL = 300


class SimulationRequest(BaseModel):
    """What-if parameters for one run. Bounds are enforced at the boundary so an
    out-of-range knob is a clean ``422`` (not a silent clamp). Optional per-trade
    knobs default ``None`` = "don't apply"."""

    run_id: str = Field(..., min_length=1, description="the finished run to simulate over")
    cost_multiplier: float = Field(
        1.0, ge=0.5, le=3.0, description="scale the run's transaction cost (1.0 = unchanged)"
    )
    slippage_bps: float = Field(
        0.0, ge=0.0, le=50.0, description="additional slippage in basis points per unit turnover"
    )
    stop_loss_pct: float | None = Field(
        None, gt=0.0, lt=1.0, description="per-trade stop-loss (four-layer-type runs only)"
    )
    take_profit_pct: float | None = Field(
        None, gt=0.0, le=5.0, description="per-trade take-profit (four-layer-type runs only)"
    )
    capacity_scale: float = Field(
        1.0, gt=0.0, le=3.0, description="exposure/leverage multiplier (1.0 = unchanged)"
    )


def _find_run(run_id: str, runs_path: Path) -> dict[str, Any] | None:
    """Latest ledger record for ``run_id`` (last append wins), or ``None``."""
    match: dict[str, Any] | None = None
    for record in read_runs(runs_path):
        if str(record.get("run_id")) == run_id:
            match = record
    return match


def _cost_inputs(
    record: dict[str, Any], series_trades: list[dict[str, Any]]
) -> tuple[int, float]:
    """Derive ``(n_cost_events, turnover_units)`` for the cost model from the record.

    ``n_cost_events`` = the number of cost-incurring trades/rebalances (per-trade
    list length when present, else the metrics ``trades`` / ``n_rebalances`` count).
    ``turnover_units`` = ``avg_turnover · n_rebalances`` for panel runs (each
    rebalance turns over a fraction), else the cost-event count (each four-layer
    trade is one round-trip unit).
    """
    metrics = record.get("metrics") or {}
    if simulation.has_per_trade_returns(series_trades):
        n_events = len(series_trades)
    else:
        n_events = int(metrics.get("trades") or metrics.get("n_rebalances") or 0)
    avg_turnover = metrics.get("avg_turnover")
    n_rebalances = metrics.get("n_rebalances") or metrics.get("trades")
    if isinstance(avg_turnover, (int, float)) and isinstance(n_rebalances, (int, float)):
        turnover_units = float(avg_turnover) * float(n_rebalances)
    else:
        turnover_units = float(n_events)
    return n_events, turnover_units


@router.post("/simulate", response_model=Envelope)
def run_simulation(
    req: SimulationRequest, runs_path: Path = Depends(get_runs_path)
) -> Envelope:
    """Compute a research-only what-if for one run. 404 if the run is unknown;
    every unsupported knob comes back ``not_available`` with a reason (never
    fabricated). The result is returned and discarded — nothing is persisted."""
    record = _find_run(req.run_id, runs_path)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail={"resource": "run", "id": req.run_id, "message": f"no run {req.run_id!r}"},
        )

    series = run_series_store.read_series(req.run_id) or {}
    equity = series.get("equity") or []
    trades = series.get("trades") or []
    n_events, turnover_units = _cost_inputs(record, trades)

    result = simulation.simulate(
        equity,
        trades,
        strategy=record.get("strategy"),
        cost_multiplier=req.cost_multiplier,
        slippage_bps=req.slippage_bps,
        stop_loss_pct=req.stop_loss_pct,
        take_profit_pct=req.take_profit_pct,
        capacity_scale=req.capacity_scale,
        n_trades=n_events,
        turnover_units=turnover_units,
        round_trip_cost=simulation.base_round_trip_cost(record.get("params")),
    )
    result["run_id"] = req.run_id
    return ok(result, meta={"data_source": DataSource.LEDGER, "ttl": _RESEARCH_TTL})
