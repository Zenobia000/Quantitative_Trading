"""``/research/validate`` — IS→WFA→OOS validation views (M3.7, owner: S3).

Split out of ``research.py`` in the M3 parallelization seam. ``gate-state`` is
backed by ``promotion_service`` (persisted, audited validation transitions);
``health`` projects a run's metrics onto the v2.md §4.3.1 green/yellow/red table
(6.1.3); ``wfa`` is filled by S7 (WFA viz, 6.2.2) and ``redline`` (PBO/DSR matrix)
remains typed-empty until its persistence lands.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends

from backtest_platform.api.deps import get_runs_path
from backtest_platform.api.envelope import Envelope, ok, pending
from backtest_platform.research import promotion_service
from backtest_platform.research.runs_store import read_runs
from backtest_platform.validation.health_indicators import health_check

router = APIRouter(prefix="/research/validate", tags=["research"])


@router.get("/{run_id}/gate-state", response_model=Envelope)
def gate_state(run_id: str) -> Envelope:
    """Current validation status + stage + transition history for a run."""
    return ok(promotion_service.gate_state(run_id))


@router.get("/{run_id}/health", response_model=Envelope)
def validate_health(run_id: str, runs_path: Path = Depends(get_runs_path)) -> Envelope:
    """13-indicator green/yellow/red health table (v2.md §4.3.1) for a run.

    Projects the run's stored metrics onto the §4.3.1 bands. A run absent from the
    ledger (or carrying no metrics) yields a health report of all ``na``.
    """
    metrics: dict = {}
    for rec in read_runs(runs_path):
        if str(rec.get("run_id")) == run_id:
            metrics = rec.get("metrics") or {}
            break
    return ok(health_check(metrics).to_dict())


@router.get("/{run_id}/wfa", response_model=Envelope)
def validate_wfa(run_id: str) -> Envelope:
    return pending({"folds": [], "scatter": []})


@router.get("/{run_id}/redline", response_model=Envelope)
def validate_redline(run_id: str) -> Envelope:
    return pending({"pbo": None, "dsr_matrix": []})
