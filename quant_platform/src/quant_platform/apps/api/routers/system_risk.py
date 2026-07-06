"""``/system/risk`` — ex-ante risk-rule spec + evaluate (risk_gate domain).

Split out of the former ``system.py`` monolith (W6.1a): the risk slice ships the
12 ex-ante rule *definitions* now (a real config projection), while
``/system/risk/evaluate`` stays a typed-empty stub until the M4 daemon.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from quant_platform.apps.api.envelope import DataSource, Envelope, ok, page_meta
from quant_platform.apps.api.response_models import RiskSpecData
from quant_platform.services.risk_gate.risk_gate import risk_spec as _risk_spec

router = APIRouter(prefix="/system", tags=["system"])


def _stub(
    data: Any, ttl: int = 300, *, total: int | None = None, page: int = 1, limit: int = 50
) -> Envelope:
    """Typed-empty stub (``DataSource.PENDING``); paginated stubs echo real page/limit."""
    meta: dict[str, Any] = {"data_source": DataSource.PENDING, "ttl": ttl}
    if total is not None:
        meta |= page_meta(total, page, limit)
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
