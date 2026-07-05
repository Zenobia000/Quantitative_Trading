"""``/system/alerts`` — alert rule/channel config (monitoring_ops domain).

Split out of the former ``system.py`` monolith (W6.1a). The built-in §4.2 alert
rule *definitions* ship now as a real config projection; create/update, channels,
test-send, history and ack stay **typed-empty stubs** (ADR-021 §5.4) until a rule
store / the M4 producer exists. Secrets are always masked (``rules/security.md``):
``/system/alerts/channels`` never returns a real ``bot_token``.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from backtest_platform.api.envelope import DataSource, Envelope, ok, page_meta
from backtest_platform.api.response_models import AlertRuleRow
from backtest_platform.monitoring.alert_rules import rules_spec as _alert_rules_spec

router = APIRouter(prefix="/system", tags=["system"])


def _stub(
    data: Any, ttl: int = 300, *, total: int | None = None, page: int = 1, limit: int = 50
) -> Envelope:
    """Typed-empty stub (``DataSource.PENDING``); paginated stubs echo real page/limit."""
    meta: dict[str, Any] = {"data_source": DataSource.PENDING, "ttl": ttl}
    if total is not None:
        meta |= page_meta(total, page, limit)
    return ok(data, meta=meta)


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
def alert_history(page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=500)) -> Envelope:
    """Alert history — offset-paginated (A3). No producer yet, so the slice is empty,
    but ``page``/``limit`` are echoed honestly rather than hard-coded."""
    return _stub([], total=0, page=page, limit=limit)


@router.post("/alerts/history/{event_id}/ack", response_model=Envelope)
def alert_ack(event_id: str) -> Envelope:
    return _stub({"id": event_id, "acked": True})
