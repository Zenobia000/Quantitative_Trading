"""``/monitor`` — Monitor-zone endpoints, shipped as **typed-empty stubs** (ADR-021 §5.4).

Monitor B/C/D + the fleet board have no live data source until M4 (no hosted
PaperBroker / CircuitBreaker daemon driving them). The trade-log writers
(``upsert_signals/orders/fills/equity_snapshots``) are implemented (7.A.2); what
is still missing is the daemon that *runs* a paper strategy and feeds them. Per
ADR-021, these endpoints ship now returning a typed
*empty* envelope tagged ``meta.data_source="pending_m4"`` so the frontend can build
against stable shapes and render an honest pending state — never fabricated data.
When the M4 producers land, each stub body is replaced; the shape stays.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from backtest_platform.api.envelope import Envelope, ok

router = APIRouter(prefix="/monitor", tags=["monitor"])

_PENDING = "pending_m4"


def _stub(data: Any, ttl: int = 60, *, total: int | None = None) -> Envelope:
    """Typed-empty envelope marking an M4-deferred producer."""
    meta: dict[str, Any] = {"data_source": _PENDING, "ttl": ttl}
    if total is not None:
        meta |= {"total": total, "page": 1, "limit": 50}
    return ok(data, meta=meta)


# ---- fleet board (monitor_fleet) ----------------------------------------
@router.get("/strategies", response_model=Envelope)
def strategies() -> Envelope:
    return _stub([])


@router.get("/fleet", response_model=Envelope)
def fleet() -> Envelope:
    return _stub([])


@router.get("/portfolio-summary", response_model=Envelope)
def portfolio_summary() -> Envelope:
    return _stub({})


@router.get("/correlation", response_model=Envelope)
def correlation() -> Envelope:
    return _stub({"axes": [], "z": []}, ttl=300)


@router.post("/fleet/{strategy_id}/action", response_model=Envelope)
def fleet_action(strategy_id: str) -> Envelope:
    return _stub({"strategy_id": strategy_id, "applied": False})


# ---- performance (monitor_a) --------------------------------------------
@router.get("/performance/equity", response_model=Envelope)
def perf_equity() -> Envelope:
    return _stub([], ttl=300)


@router.get("/performance/benchmark", response_model=Envelope)
def perf_benchmark() -> Envelope:
    return _stub([], ttl=300)


@router.get("/performance/monthly", response_model=Envelope)
def perf_monthly() -> Envelope:
    return _stub([], ttl=300)


@router.get("/performance/kpi", response_model=Envelope)
def perf_kpi() -> Envelope:
    return _stub({}, ttl=300)


# ---- positions (monitor_b) ----------------------------------------------
@router.get("/positions/snapshot", response_model=Envelope)
def pos_snapshot() -> Envelope:
    return _stub([])


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
def signals(page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=200)) -> Envelope:
    return _stub([], ttl=30, total=0)


@router.get("/signals/timeline", response_model=Envelope)
def signals_timeline() -> Envelope:
    return _stub([], ttl=300)


@router.get("/signals/funnel", response_model=Envelope)
def signals_funnel() -> Envelope:
    return _stub({}, ttl=30)


@router.get("/fills", response_model=Envelope)
def fills() -> Envelope:
    return _stub([], ttl=300)


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
