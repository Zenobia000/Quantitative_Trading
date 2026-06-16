"""POST /research/workflows/{workflow} — async research workflow jobs (sub-project ①.5)."""
from __future__ import annotations

import importlib

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backtest_platform.api.envelope import Envelope, ok
from backtest_platform.jobs import submit
from backtest_platform.research.workflows.loader import (
    get_doe_config, get_go_gates_config,
    get_truth_gate_config, get_paper_replay_config,
    list_workflow_configs,
)

router = APIRouter(prefix="/research/workflows", tags=["research-workflows"])

_WORKFLOW_GETTERS = {
    "doe":          get_doe_config,
    "go_gates":     get_go_gates_config,
    "truth_gate":   get_truth_gate_config,
    "paper_replay": get_paper_replay_config,
}

_WORKFLOW_RUNNERS = {
    "doe":          ("backtest_platform.research.workflows.doe",          "run_doe"),
    "go_gates":     ("backtest_platform.research.workflows.go_gates",     "run_go_gates"),
    "truth_gate":   ("backtest_platform.research.workflows.truth_gate",   "run_truth_gate"),
    "paper_replay": ("backtest_platform.research.workflows.paper_replay", "run_paper_replay_workflow"),
}


class _WorkflowRequest(BaseModel):
    strategy:  str
    overrides: dict = {}


@router.get("/{strategy}", response_model=Envelope)
def list_strategy_workflows(strategy: str) -> Envelope:
    """List which workflow configs are declared by this strategy."""
    try:
        workflows = list_workflow_configs(strategy)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ok({"strategy": strategy, "workflows": workflows})


@router.post("/{workflow}", response_model=Envelope, status_code=202)
def submit_workflow(workflow: str, req: _WorkflowRequest) -> Envelope:
    """Enqueue a research workflow as a background job; returns {job_id, status}."""
    if workflow not in _WORKFLOW_GETTERS:
        raise HTTPException(
            status_code=404,
            detail=f"unknown workflow {workflow!r}; choose from {sorted(_WORKFLOW_GETTERS)}",
        )
    getter_fn = _WORKFLOW_GETTERS[workflow]
    try:
        cfg = getter_fn(req.strategy)
    except (ValueError, AttributeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if req.overrides:
        cfg = cfg.model_copy(update=req.overrides)

    mod_path, fn_name = _WORKFLOW_RUNNERS[workflow]
    run_fn = getattr(importlib.import_module(mod_path), fn_name)

    key = f"{workflow}:{req.strategy}"
    job = submit(workflow, key, lambda: run_fn(cfg))
    return ok({"job_id": job.job_id, "status": job.status.value})
