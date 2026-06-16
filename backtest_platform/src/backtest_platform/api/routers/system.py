"""``/system`` — System-zone endpoints (data management + alert config).

Most system data stores (bundle manifest, ingest jobs, alert history, channel
secrets) are not yet wired to a live source, so these ship as **typed-empty
stubs** tagged ``meta.data_source="pending"`` (ADR-021 §5.4) — stable shapes for
the frontend, no fabricated data. Secrets are always masked (``rules/security.md``):
``/system/alerts/channels`` never returns a real ``bot_token``.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from backtest_platform.api.envelope import Envelope, ok, pending
from backtest_platform.api.response_models import AlertRuleRow, RiskSpecData
from backtest_platform.jobs import job_store, submit
from backtest_platform.monitoring.alert_rules import rules_spec as _alert_rules_spec
from backtest_platform.risk.risk_gate import risk_spec as _risk_spec


class IngestRequest(BaseModel):
    """Trigger a bundle ingest as an async job (8.H.6)."""

    symbols: list[str] = Field(..., min_length=1)
    start: date
    end: date
    source: str = "finlab"  # "finlab" (ADR-006 primary) | "finmind" (fallback)

router = APIRouter(prefix="/system", tags=["system"])

_PENDING = "pending"


def _stub(data: Any, ttl: int = 300, *, total: int | None = None) -> Envelope:
    meta: dict[str, Any] = {"data_source": _PENDING, "ttl": ttl}
    if total is not None:
        meta |= {"total": total, "page": 1, "limit": 50}
    return ok(data, meta=meta)


# ---- risk spec (sys_alerts / mon_d config) ------------------------------
@router.get("/risk/spec", response_model=Envelope[RiskSpecData])
def risk_spec() -> Envelope:
    """The 12 ex-ante risk rules + active thresholds. Real config projection — this
    is rule *definitions* (not live telemetry), so it ships now, not at the M4 daemon."""
    return ok(_risk_spec())


@router.post("/risk/evaluate", response_model=Envelope)
def risk_evaluate() -> Envelope:
    return _stub({"results": []})


# ---- alerts (sys_alerts) ------------------------------------------------
@router.get("/alerts/rules", response_model=Envelope[list[AlertRuleRow]])
def alert_rules() -> Envelope:
    """The built-in §4.2 alert rules (real config projection). Rule definitions
    ship now; create/update (POST/PUT) and history stay pending on a rule store /
    the M4 producer."""
    rules = _alert_rules_spec()
    return ok(rules, meta={"total": len(rules), "page": 1, "limit": 50, "ttl": 300})


@router.get("/alerts/channels", response_model=Envelope)
def alert_channels() -> Envelope:
    # 秘密一律遮罩（rules/security.md §4）
    return _stub({"discord": {"enabled": False, "bot_token": "***"}})


@router.post("/alerts/test", response_model=Envelope)
def alert_test() -> Envelope:
    return _stub({"delivered": False})


@router.put("/alerts/channels", response_model=Envelope)
def alert_channels_put() -> Envelope:
    return _stub({"ok": True})


@router.post("/alerts/rules", response_model=Envelope)
def alert_rules_post() -> Envelope:
    return _stub({"id": "stub"})


@router.put("/alerts/rules", response_model=Envelope)
def alert_rules_put() -> Envelope:
    return _stub({"ok": True})


@router.get("/alerts/history", response_model=Envelope)
def alert_history(page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=200)) -> Envelope:
    return _stub([], total=0)


@router.post("/alerts/history/{event_id}/ack", response_model=Envelope)
def alert_ack(event_id: str) -> Envelope:
    return _stub({"id": event_id, "acked": True})


# ---- bundles / ingest (sys_data) ----------------------------------------
@router.get("/bundles", response_model=Envelope)
def bundles(page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=200)) -> Envelope:
    return _stub([], total=0)


@router.get("/bundles/{bundle_id}/quality", response_model=Envelope)
def bundle_quality(bundle_id: str) -> Envelope:
    return _stub({"id": bundle_id})


@router.post("/ingest", response_model=Envelope, status_code=202)
def ingest(req: IngestRequest) -> Envelope:
    """Enqueue a bundle ingest as an async job (8.H.6); returns ``{job_id, status}``
    (202). The job runs the real ETL (FinLab/FinMind via ``make_ingest``) off-thread
    so the API never blocks; poll :func:`ingest_status`."""
    from backtest_platform.orchestration.collaborators import make_ingest

    ing = make_ingest(start=req.start, end=req.end, source=req.source)

    def _run() -> dict[str, Any]:
        result = ing(list(req.symbols))
        return {
            "requested": len(req.symbols),
            "ok": sorted(s for s, good in result.items() if good),
            "failed": sorted(s for s, good in result.items() if not good),
        }

    key = f"{req.source}|{req.start}|{req.end}|{','.join(req.symbols)}"
    job = submit("ingest", key, _run)
    return ok({"job_id": job.job_id, "status": job.status.value})


@router.get("/ingest/{job_id}/status", response_model=Envelope)
def ingest_status(job_id: str) -> Envelope:
    """Poll an ingest job's status/result; typed-empty ``pending`` if unknown."""
    job = job_store.read_job(job_id)
    if job is None:
        return pending({"job_id": job_id, "status": None, "progress": None})
    return ok(job.to_dict())
