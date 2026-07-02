"""Research workflow HTTP endpoints (ADR-029).

``POST /research/workflows/{workflow}`` enqueues a workflow (doe / go_gates /
truth_gate / paper_replay) as a background job and returns ``{job_id, status}``
(202) — the research loop never blocks. ``GET /research/workflows/{strategy}``
lists which workflows a strategy declares. Mirrors the async pattern in
``research_sweep``.
"""
from __future__ import annotations

import importlib

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

from backtest_platform.api.envelope import Envelope, ok
from backtest_platform.jobs import submit
from backtest_platform.research.workflows.config import revalidate_with_overrides
from backtest_platform.research.workflows.loader import (
    get_doe_config,
    get_go_gates_config,
    get_paper_replay_config,
    get_truth_gate_config,
    get_universe_config,
    list_workflow_configs,
)

router = APIRouter(prefix="/research/workflows", tags=["research-workflows"])

# workflow name → (config getter, "module:function" of the runner)
_WORKFLOWS: dict[str, tuple] = {
    "doe": (get_doe_config, "backtest_platform.research.workflows.doe:run_doe"),
    "go_gates": (get_go_gates_config, "backtest_platform.research.workflows.go_gates:run_go_gates"),
    "truth_gate": (get_truth_gate_config, "backtest_platform.research.workflows.truth_gate:run_truth_gate"),
    "paper_replay": (
        get_paper_replay_config,
        "backtest_platform.research.workflows.paper_replay:run_paper_replay_workflow",
    ),
    "build_universe": (
        get_universe_config,
        "backtest_platform.research.workflows.universe:run_build_universe",
    ),
}


class _WorkflowRequest(BaseModel):
    strategy: str
    overrides: dict = {}


def _overrides_detail(exc: ValidationError) -> str:
    """Collapse override validation errors into one readable 422 message (doc 25 §2)."""
    parts = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", ()))
        parts.append(f"{loc}: {err['msg']}" if loc else str(err["msg"]))
    return "invalid overrides — " + "; ".join(parts)


@router.get("/{strategy}", response_model=Envelope)
def list_strategy_workflows(strategy: str) -> Envelope:
    """List which workflow configs this strategy declares."""
    try:
        workflows = list_workflow_configs(strategy)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return ok({"strategy": strategy, "workflows": workflows})


@router.post("/{workflow}", response_model=Envelope, status_code=202)
def submit_workflow(workflow: str, req: _WorkflowRequest) -> Envelope:
    """Enqueue a research workflow as a background job; returns {job_id, status}."""
    if workflow not in _WORKFLOWS:
        raise HTTPException(
            status_code=404,
            detail=f"unknown workflow {workflow!r}; choose from {sorted(_WORKFLOWS)}",
        )
    getter, run_ref = _WORKFLOWS[workflow]
    try:
        cfg = getter(req.strategy)
    except (ValueError, AttributeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    if req.overrides:
        # Re-validate at the boundary (審查缺陷 #11): bad type / unknown field /
        # illegal window fails 422 HERE, never as a silent 202 that explodes in the
        # job thread. ``model_copy(update=...)`` bypassed the whole validation gate.
        try:
            cfg = revalidate_with_overrides(cfg, req.overrides)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=_overrides_detail(exc)) from None

    module_path, fn_name = run_ref.rsplit(":", 1)
    run_fn = getattr(importlib.import_module(module_path), fn_name)
    job = submit(workflow, f"{workflow}:{req.strategy}", lambda: run_fn(cfg))
    return ok({"job_id": job.job_id, "status": job.status.value})
