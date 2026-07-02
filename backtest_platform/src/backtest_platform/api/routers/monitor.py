"""``/monitor`` — Monitor-zone endpoints, shipped as **typed-empty stubs** (ADR-021 §5.4).

Monitor B/C/D + the fleet board have no live data source until M4 (no hosted
PaperBroker / CircuitBreaker daemon driving them). The trade-log writers
(``upsert_signals/orders/fills/equity_snapshots``) are implemented (7.A.2); what
is still missing is the daemon that *runs* a paper strategy and feeds them. Per
ADR-021, these endpoints ship now returning a typed
*empty* envelope tagged ``meta.data_source="pending_m4"`` so the frontend can build
against stable shapes and render an honest pending state — never fabricated data.
When the M4 producers land, each stub body is replaced; the shape stays.

8.H.8 (2026-06-15): ``/performance/equity`` and ``/positions/snapshot`` now read
**real** daemon-produced telemetry via an injected ``TelemetryReader`` (db_reader),
falling back to the same typed-empty pending envelope when no DB/telemetry exists.
The remaining endpoints stay stubs until their producers land.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from loguru import logger

from backtest_platform.api.deps import get_telemetry_reader
from backtest_platform.api.envelope import Envelope, ok

router = APIRouter(prefix="/monitor", tags=["monitor"])

_PENDING = "pending_m4"
_LIVE = "timescaledb"


def _stub(data: Any, ttl: int = 60, *, total: int | None = None) -> Envelope:
    """Typed-empty envelope marking an M4-deferred producer."""
    meta: dict[str, Any] = {"data_source": _PENDING, "ttl": ttl}
    if total is not None:
        meta |= {"total": total, "page": 1, "limit": 50}
    return ok(data, meta=meta)


def _served(data: Any, ttl: int, *, total: int | None = None) -> Envelope:
    """Envelope for data read from real TimescaleDB telemetry (8.H.8)."""
    meta: dict[str, Any] = {"data_source": _LIVE, "ttl": ttl}
    if total is not None:
        meta |= {"total": total, "page": 1, "limit": 50}
    return ok(data, meta=meta)


def _equity_kpis(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive headline KPIs from an equity series (reuses validation.metrics).

    Returns zeros (plus current equity) for a series too short to annualise (< 2
    points), so the Monitor KPI tile renders an honest early state."""
    if len(rows) < 2:
        return {
            "current_equity": float(rows[-1]["equity"]) if rows else 0.0,
            "total_return": 0.0, "cagr": 0.0, "sharpe": 0.0,
            "max_drawdown": 0.0, "calmar": 0.0, "n_points": len(rows),
        }
    import pandas as pd

    from backtest_platform.validation.metrics import (
        cagr,
        calmar,
        max_drawdown,
        sharpe,
        total_return,
    )

    # KPIs are index-agnostic (metrics annualise via periods_per_year, not dates),
    # so a plain ordered series avoids parsing the DB's mixed-precision ISO timestamps.
    eq = pd.Series([float(r["equity"]) for r in rows])
    ret = eq.pct_change().dropna()
    return {
        "current_equity": float(eq.iloc[-1]),
        "total_return": round(float(total_return(ret)), 6),
        "cagr": round(float(cagr(ret)), 6),
        "sharpe": round(float(sharpe(ret)), 4),
        "max_drawdown": round(float(max_drawdown(ret)), 6),
        "calmar": round(float(calmar(ret)), 4),
        "n_points": len(rows),
    }


# ---- fleet board (monitor_fleet) ----------------------------------------
def _registered_strategies() -> list[str]:
    """Available strategy names from the ADR-027 registry. Best-effort imports the
    production runners (registration is an import side-effect); empty if none load."""
    from backtest_platform.strategies.protocol import list_strategies

    for mod in (
        "backtest_platform.strategies.inst_flow.runner",
        "backtest_platform.strategies.momentum.runner",
        "backtest_platform.strategies.four_layer_resonance.runner",
    ):
        try:
            __import__(mod)
        except Exception:
            pass
    return list_strategies()


@router.get("/strategies", response_model=Envelope)
def strategies() -> Envelope:
    """Registered strategy catalog (ADR-027 registry). Typed-empty pending if none."""
    names = _registered_strategies()
    if not names:
        return _stub([])
    return _served([{"strategy_id": n} for n in names], ttl=300, total=len(names))


@router.get("/fleet", response_model=Envelope)
def fleet(reader: Any = Depends(get_telemetry_reader)) -> Envelope:
    """Live fleet board — latest equity per strategy from telemetry (8.H.8);
    pending fallback when no DB/telemetry."""
    try:
        rows = reader.fleet_summary()
    except Exception as exc:
        logger.warning("monitor /fleet degraded (no telemetry?): {}", exc)
        return _stub([])
    return _served(rows, ttl=60, total=len(rows))


@router.get("/portfolio-summary", response_model=Envelope)
def portfolio_summary(reader: Any = Depends(get_telemetry_reader)) -> Envelope:
    """Fleet roll-up — total equity / strategy count / open positions (8.H.8)."""
    try:
        rows = reader.fleet_summary()
    except Exception as exc:
        logger.warning("monitor /portfolio-summary degraded (no telemetry?): {}", exc)
        return _stub({})
    if not rows:
        return _served({"n_strategies": 0, "total_equity": 0.0, "total_open_positions": 0}, ttl=60)
    return _served(
        {
            "n_strategies": len(rows),
            "total_equity": round(sum(float(r["equity"]) for r in rows), 2),
            "total_open_positions": sum(int(r["open_positions"]) for r in rows),
        },
        ttl=60,
    )


@router.get("/board", response_model=Envelope)
def board(
    limit: int = Query(50, ge=1, le=500),
    reader: Any = Depends(get_telemetry_reader),
) -> Envelope:
    """Run board (A2) — latest research runs from the runs table: lifecycle
    status (running|done|failed, mirrored by run_persist / run-batch) + 審判庭
    verdict + metrics. Typed-empty pending fallback when no DB."""
    try:
        rows = reader.runs_board(limit=limit)
    except Exception as exc:
        logger.warning("monitor /board degraded (no DB?): {}", exc)
        return _stub([])
    return _served(rows, ttl=5, total=len(rows))


@router.get("/correlation", response_model=Envelope)
def correlation() -> Envelope:
    return _stub({"axes": [], "z": []}, ttl=300)


@router.post("/fleet/{strategy_id}/action", response_model=Envelope)
def fleet_action(strategy_id: str) -> Envelope:
    return _stub({"strategy_id": strategy_id, "applied": False})


# ---- performance (monitor_a) --------------------------------------------
@router.get("/performance/equity", response_model=Envelope)
def perf_equity(reader: Any = Depends(get_telemetry_reader)) -> Envelope:
    """Equity curve from real paper/live telemetry (8.H.8); typed-empty pending
    when no DB / telemetry exists yet (graceful degradation)."""
    try:
        rows = reader.equity_series()
    except Exception as exc:
        logger.warning("monitor /performance/equity degraded (no telemetry?): {}", exc)
        return _stub([], ttl=300)
    return _served(rows, ttl=300, total=len(rows))


@router.get("/performance/benchmark", response_model=Envelope)
def perf_benchmark() -> Envelope:
    return _stub([], ttl=300)


@router.get("/performance/monthly", response_model=Envelope)
def perf_monthly() -> Envelope:
    return _stub([], ttl=300)


@router.get("/performance/kpi", response_model=Envelope)
def perf_kpi(reader: Any = Depends(get_telemetry_reader)) -> Envelope:
    """Headline KPIs (return/CAGR/Sharpe/MDD/Calmar) derived from the real equity
    series (8.H.8); typed-empty pending when no DB/telemetry."""
    try:
        kpis = _equity_kpis(reader.equity_series())
    except Exception as exc:
        logger.warning("monitor /performance/kpi degraded (no telemetry?): {}", exc)
        return _stub({}, ttl=300)
    return _served(kpis, ttl=300)


# ---- positions (monitor_b) ----------------------------------------------
@router.get("/positions/snapshot", response_model=Envelope)
def pos_snapshot(reader: Any = Depends(get_telemetry_reader)) -> Envelope:
    """Open positions from real telemetry (8.H.8); pending fallback when no DB."""
    try:
        rows = reader.open_positions()
    except Exception as exc:
        logger.warning("monitor /positions/snapshot degraded (no telemetry?): {}", exc)
        return _stub([])
    return _served(rows, ttl=60, total=len(rows))


@router.get("/positions/prices", response_model=Envelope)
def pos_prices() -> Envelope:
    return _stub({})


@router.get("/positions/kpi", response_model=Envelope)
def pos_kpi() -> Envelope:
    return _stub({})


@router.get("/positions/industry-allocation", response_model=Envelope)
def pos_industry() -> Envelope:
    return _stub([])


@router.get("/positions/concentration", response_model=Envelope)
def pos_concentration() -> Envelope:
    return _stub({})


# ---- signals (monitor_c) ------------------------------------------------
@router.get("/signals", response_model=Envelope)
def signals(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    reader: Any = Depends(get_telemetry_reader),
) -> Envelope:
    """Recent signals from real telemetry (8.H.8); pending fallback when no DB."""
    try:
        rows = reader.recent_signals(limit=limit)
    except Exception as exc:
        logger.warning("monitor /signals degraded (no telemetry?): {}", exc)
        return _stub([], ttl=30, total=0)
    return _served(rows, ttl=30, total=len(rows))


@router.get("/signals/timeline", response_model=Envelope)
def signals_timeline() -> Envelope:
    return _stub([], ttl=300)


@router.get("/signals/funnel", response_model=Envelope)
def signals_funnel() -> Envelope:
    return _stub({}, ttl=30)


@router.get("/fills", response_model=Envelope)
def fills(
    limit: int = Query(50, ge=1, le=200),
    reader: Any = Depends(get_telemetry_reader),
) -> Envelope:
    """Recent order executions from real telemetry (8.H.8); pending fallback."""
    try:
        rows = reader.recent_fills(limit=limit)
    except Exception as exc:
        logger.warning("monitor /fills degraded (no telemetry?): {}", exc)
        return _stub([], ttl=300)
    return _served(rows, ttl=300, total=len(rows))


# ---- risk (monitor_d) ---------------------------------------------------
@router.get("/risk/metrics", response_model=Envelope)
def risk_metrics() -> Envelope:
    return _stub({}, ttl=30)


@router.get("/risk/mdd-trend", response_model=Envelope)
def risk_mdd_trend() -> Envelope:
    return _stub([], ttl=60)


@router.get("/risk/events", response_model=Envelope)
def risk_events(page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=200)) -> Envelope:
    return _stub([], total=0)


@router.get("/risk/events/{event_id}", response_model=Envelope)
def risk_event(event_id: str) -> Envelope:
    return _stub({"id": event_id})
