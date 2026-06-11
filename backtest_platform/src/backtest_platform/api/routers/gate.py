"""``/gate`` — the strategy-agnostic審判庭 over HTTP.

Two endpoints:

* ``GET  /gate/spec``     — the gate's criteria as data (ADR-016 K1/K2/K3 +
  ADR-019 health checks), so a client can render what is being judged.
* ``POST /gate/evaluate`` — feed a metrics dict, get per-criterion PASS/FAIL +
  signed gap + the overall PASS/FAIL/INCOMPLETE status.

Pure pass-through to ``validation.gate_state.evaluate_gate``; no IO.
"""
from __future__ import annotations

from fastapi import APIRouter

from backtest_platform.api.envelope import Envelope, ok
from backtest_platform.api.response_models import GateEvalData, GateSpecData
from backtest_platform.api.schemas import GateEvaluateRequest
from backtest_platform.validation.gate_state import DEFAULT_GATE, evaluate_gate

router = APIRouter(prefix="/gate", tags=["gate"])


@router.get("/spec", response_model=Envelope[GateSpecData])
def gate_spec() -> Envelope:
    """Return the default gate's criteria (key / op / threshold / kind / label)."""
    criteria = [
        {
            "key": c.key,
            "op": c.op,
            "threshold": c.threshold,
            "kind": c.kind,
            "label": c.label,
        }
        for c in DEFAULT_GATE
    ]
    return ok({"criteria": criteria})


@router.post("/evaluate", response_model=Envelope[GateEvalData])
def gate_evaluate(req: GateEvaluateRequest) -> Envelope:
    """Judge a metrics dict against the default gate."""
    result = evaluate_gate(req.metrics)
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
