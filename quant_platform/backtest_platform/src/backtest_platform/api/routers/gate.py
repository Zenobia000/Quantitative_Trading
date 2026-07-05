"""``/gate`` — the strategy-agnostic審判庭 over HTTP.

Two endpoints:

* ``GET  /gate/spec``     — the gate's criteria as data (ADR-016 K1/K2/K3 +
  ADR-019 health checks), so a client can render what is being judged.
* ``POST /gate/evaluate`` — feed a metrics dict, get per-criterion PASS/FAIL +
  signed gap + the overall PASS/FAIL/INCOMPLETE status.

Both accept an optional ``strategy`` so the审判庭 dispatches that strategy's own
declared gate (``get_strategy_gate``) — a panel strategy is judged by its panel
gate, not four-layer's health checks it never produces (審查缺陷 #8). Omitting
``strategy`` keeps the four-layer ``DEFAULT_GATE`` for back-compat.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backtest_platform.api.envelope import Envelope, ok
from backtest_platform.api.response_models import GateEvalData, GateSpecData
from backtest_platform.api.schemas import GateEvaluateRequest
from backtest_platform.validation.gate_state import DEFAULT_GATE, evaluate_gate

router = APIRouter(prefix="/gate", tags=["gate"])


def _resolve_gate(strategy: str | None):
    """The strategy's declared gate, or the four-layer DEFAULT_GATE when omitted.

    Unknown strategy / a strategy without a declared gate raise ValueError, which
    the callers map to **HTTP 404** (an unknown *named resource*, standardized with
    ``/research/workflows/{workflow}`` — A4).
    """
    if not strategy:
        return DEFAULT_GATE
    from backtest_platform.research import runners as _runners  # noqa: F401 — register
    from backtest_platform.strategies.protocol import get_strategy_gate

    return get_strategy_gate(strategy)


def _gate_or_404(strategy: str | None):
    """Resolve the gate or raise a structured 404 for an unknown strategy."""
    try:
        return _resolve_gate(strategy)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={"resource": "strategy", "id": strategy, "message": str(exc)},
        ) from None


@router.get("/spec", response_model=Envelope[GateSpecData])
def gate_spec(strategy: str | None = Query(None)) -> Envelope:
    """Return a gate's criteria (key / op / threshold / kind / label).

    ``strategy`` → that strategy's declared gate; omitted → four-layer DEFAULT_GATE.
    """
    gate = _gate_or_404(strategy)
    criteria = [
        {
            "key": c.key,
            "op": c.op,
            "threshold": c.threshold,
            "kind": c.kind,
            "label": c.label,
        }
        for c in gate
    ]
    return ok({"criteria": criteria})


@router.post("/evaluate", response_model=Envelope[GateEvalData])
def gate_evaluate(req: GateEvaluateRequest) -> Envelope:
    """Judge a metrics dict against a gate.

    ``req.strategy`` → that strategy's declared gate; omitted → four-layer default.
    """
    gate = _gate_or_404(req.strategy)
    result = evaluate_gate(req.metrics, gate)
    payload = {
        "status": result.status.value,
        "passed": result.passed,
        "summary": result.summary(),
        "results": [
            {
                "key": r.criterion.key,
                "label": r.criterion.label,
                "op": r.criterion.op,
                "threshold": r.criterion.threshold,
                "kind": r.criterion.kind,
                "value": r.value,
                "passed": r.passed,
                "gap": r.gap,
            }
            for r in result.results
        ],
    }
    return ok(payload)
