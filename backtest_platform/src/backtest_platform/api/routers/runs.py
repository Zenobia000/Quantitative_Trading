"""``/runs`` — the runs ledger over HTTP (list / get / compare / trigger).

The append-only JSONL ledger (``research.runs_store``) is the lineage record of
every IS run. This router reads it (paginated list, single lookup, cross-run
compare) and writes it (trigger a new run → judge → append). The ledger path and
the heavy run executor are injected dependencies (``deps``) so tests run against
a temp file with a stub executor.

Route order matters: the literal ``/compare`` is declared before the
``/{run_id}`` catch-all so "compare" is never swallowed as a run id.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import ValidationError

from backtest_platform.api.deps import RunExecutor, get_run_executor, get_runs_path
from backtest_platform.api.envelope import Envelope, ok, page_meta, pending
from backtest_platform.api.response_models import (
    CompareReportData,
    RunRecord,
    RunSummary,
    SweepEstimate,
)
from backtest_platform.api.schemas import RunCreateRequest
from backtest_platform.jobs import job_store, submit
from backtest_platform.research.compare import CompareReport, compare_runs
from backtest_platform.research.run_config import RunConfig
from backtest_platform.research.runs_store import append_run, read_runs

router = APIRouter(prefix="/runs", tags=["runs"])

#: Fields surfaced in the paginated list view (the full record is on the detail route).
_SUMMARY_KEYS = (
    "run_id",
    "preset",
    "gate_status",
    "hypothesis",
    "metrics",
    "is_start",
    "is_end",
)


def _summary(record: dict[str, Any]) -> dict[str, Any]:
    """Project a ledger record down to the list-view fields."""
    return {k: record.get(k) for k in _SUMMARY_KEYS}


def _dedupe_latest(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse the append-only ledger to one record per run_id, latest append
    winning, preserving first-appearance order (stable list ordering).

    A re-run appends the same run_id again (e.g. the momentum DOE → 7 lines for 5
    ids). The runs table is a registry view — one current row per run, not one row
    per append. The raw ledger is untouched (lineage stays intact for compare/cli);
    only the view projections dedupe. Duplicate rows also broke the FE table's
    React keys (e2e endpoint-audit F5).
    """
    by_id: dict[str, dict[str, Any]] = {}
    for r in records:
        by_id[str(r.get("run_id"))] = r  # later append overwrites → latest wins
    return list(by_id.values())


def _serialize_compare(rep: CompareReport) -> dict[str, Any]:
    """Flatten a frozen ``CompareReport`` into JSON-friendly primitives."""
    return {
        "baseline_id": rep.baseline_id,
        "metric_keys": list(rep.metric_keys),
        "sign_consistent": dict(rep.sign_consistent),
        "rankings": {k: list(v) for k, v in rep.rankings.items()},
        "comparisons": [
            {
                "run_id": c.run_id,
                "is_baseline": c.is_baseline,
                "metrics": dict(c.metrics),
                "delta": dict(c.delta),
                "rank": dict(c.rank),
                "gate_status": c.gate_status,
                "hypothesis": c.hypothesis,
            }
            for c in rep.comparisons
        ],
    }


@router.get("", response_model=Envelope[list[RunSummary]])
def list_runs(
    page: int = Query(1, ge=1, description="1-based page index"),
    limit: int = Query(50, ge=1, le=500, description="page size"),
    runs_path: Path = Depends(get_runs_path),
) -> Envelope:
    """Paginated list of run summaries, one current row per run_id (latest wins)."""
    records = _dedupe_latest(read_runs(runs_path))
    total = len(records)
    start = (page - 1) * limit
    items = [_summary(r) for r in records[start : start + limit]]
    return ok(items, meta=page_meta(total, page, limit))


@router.get("/compare", response_model=Envelope[CompareReportData])
def compare(
    baseline: str | None = Query(None, description="run_id to diff against"),
    run_ids: str | None = Query(
        None, description="comma list — compare only this subset (else the whole ledger)"
    ),
    runs_path: Path = Depends(get_runs_path),
) -> Envelope:
    """Cross-run comparison: per-metric delta vs baseline, ranks, sign consistency.

    ``run_ids`` restricts the comparison to a chosen subset (the frontend's
    multi-select → ``?run_ids=a,b,c``); absent, the whole ledger is compared. The
    subset is deduped to one current row per run_id and kept in requested order.
    """
    records = _dedupe_latest(read_runs(runs_path))
    if run_ids:
        wanted = [s for s in (x.strip() for x in run_ids.split(",")) if s]
        by_id = {str(r.get("run_id")): r for r in records}
        missing = [w for w in wanted if w not in by_id]
        if missing:
            raise HTTPException(status_code=404, detail=f"run_ids not found: {missing}")
        records = [by_id[w] for w in wanted]
    try:
        rep = compare_runs(records, baseline_id=baseline)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"baseline run not found: {exc}") from None
    return ok(_serialize_compare(rep))


#: Heuristic per-config IS-run cost for the pre-submit sweep estimate (minutes).
_EST_MINUTES_PER_CONFIG = 0.5


@router.get("/estimate", response_model=Envelope[SweepEstimate])
def estimate(request: Request) -> Envelope:
    """Pre-submit sweep estimate: ``n_configs`` (grid cardinality) + ``est_minutes``.

    Grid axes are passed as comma lists, e.g. ``?box_period=40,60,80&confirm_days=1,2``
    → 3×2 = 6 configs. ``n_configs`` equals ``len(sweep.expand_grid(...))`` for the same
    grid; we compute the cardinality directly (product of axis lengths) so no base
    config is required just to count. ``preset`` is ignored as an axis.
    """
    axes = {k: v.split(",") for k, v in request.query_params.items() if k != "preset" and v}
    n_configs = math.prod(len(vals) for vals in axes.values()) if axes else 1
    return ok(
        {
            "n_configs": n_configs,
            "est_minutes": round(n_configs * _EST_MINUTES_PER_CONFIG, 1),
            "axes": {k: len(v) for k, v in axes.items()},
        }
    )


@router.get("/{run_id}", response_model=Envelope[RunRecord])
def get_run(run_id: str, runs_path: Path = Depends(get_runs_path)) -> Envelope:
    """Full ledger record for one run (latest append wins); 404 if absent."""
    match: dict[str, Any] | None = None
    for record in read_runs(runs_path):
        if str(record.get("run_id")) == run_id:
            match = record  # keep scanning → latest append wins, consistent with list
    if match is None:
        raise HTTPException(status_code=404, detail=f"run {run_id!r} not found")
    return ok(match)


@router.post("", response_model=Envelope[RunRecord], status_code=201)
def create_run(
    req: RunCreateRequest,
    runs_path: Path = Depends(get_runs_path),
    executor: RunExecutor = Depends(get_run_executor),
) -> Envelope:
    """Trigger one IS run: build+validate a RunConfig, judge it, append to the ledger.

    A bad config (unknown preset, reversed window, ...) surfaces as 422 from the
    domain validator rather than a 500.
    """
    try:
        cfg = RunConfig(
            hypothesis=req.hypothesis,
            preset=req.preset,
            stocks=tuple(req.stocks),
            is_start=req.is_start,
            is_end=req.is_end,
            engine=req.engine,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    record = executor(cfg)
    append_run(record, runs_path)
    return ok(record)


@router.post("/async", response_model=Envelope, status_code=202)
def create_run_async(
    req: RunCreateRequest,
    runs_path: Path = Depends(get_runs_path),
    executor: RunExecutor = Depends(get_run_executor),
) -> Envelope:
    """Async variant of ``POST /runs`` (8.H.6): validate the config up-front (422
    stays synchronous), then enqueue judge-and-append as a job and return
    ``{job_id, status}`` (202 Accepted). The sync ``POST /runs`` is unchanged;
    poll :func:`run_log` for completion.
    """
    try:
        cfg = RunConfig(
            hypothesis=req.hypothesis,
            preset=req.preset,
            stocks=tuple(req.stocks),
            is_start=req.is_start,
            is_end=req.is_end,
            engine=req.engine,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    def _judge_and_append() -> dict[str, Any]:
        record = executor(cfg)
        append_run(record, runs_path)
        return record

    key = f"{req.preset}|{req.is_start}|{req.is_end}|{','.join(req.stocks)}"
    job = submit("run", key, _judge_and_append)
    return ok({"job_id": job.job_id, "status": job.status.value})


@router.get("/{job_id}/log", response_model=Envelope)
def run_log(job_id: str) -> Envelope:
    """Async-run job log (8.H.6): lifecycle (status/progress) + terminal
    result/error. A typed-empty ``pending`` envelope when the id is unknown
    (mirrors the sweep status route)."""
    job = job_store.read_job(job_id)
    if job is None:
        return pending({"job_id": job_id, "status": None, "progress": None})
    return ok(job.to_dict())
