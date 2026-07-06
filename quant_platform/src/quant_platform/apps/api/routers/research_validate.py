"""``/research/validate`` — IS→WFA→OOS validation views (M3.7, owner: S3).

Split out of ``research.py`` in the M3 parallelization seam. ``gate-state`` is
backed by ``promotion_service`` (persisted, audited validation transitions);
``health`` projects a run's metrics onto the v2.md §4.3.1 green/yellow/red table
(6.1.3); ``wfa`` is filled by S7 (WFA viz, 6.2.2) and ``redline`` (PBO/DSR matrix)
remains typed-empty until its persistence lands.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends

from quant_platform.apps.api.deps import get_runs_path
from quant_platform.apps.api.envelope import DataSource, Envelope, ok, pending
from quant_platform.services.governance_release import promotion_service
from quant_platform.packages.adapters.runs_store import read_runs
from quant_platform.services.research_validation.validation.health_indicators import health_check
from quant_platform.services.research_validation.validation.wfa import walk_forward_splits

router = APIRouter(prefix="/research/validate", tags=["research"])

# v2.md §4.4.1 canonical WFA config: IS 252d + OOS 63d, rolling 63d.
_WFA_IS_DAYS = 252
_WFA_OOS_DAYS = 63
# §4.4.1 通過標準 (surfaced as metadata so the FE shows the bar next to the folds).
_WFA_CRITERIA = {
    "oos_sharpe_vs_is": "OOS Sharpe > IS Sharpe × 0.6",
    "oos_positive_window_pct": "OOS 報酬>0 的 windows 比例 > 60%",
    "oos_maxdd_vs_is": "OOS 平均 MaxDD < IS 平均 MaxDD × 1.5",
}


def _run_window(run_id: str, runs_path: Path) -> tuple[date, date] | None:
    """The [is_start, is_end] span recorded for a run, or None if absent."""
    for rec in read_runs(runs_path):
        if str(rec.get("run_id")) == run_id:
            win = rec.get("window") or [rec.get("is_start"), rec.get("is_end")]
            if win and win[0] and win[1]:
                return date.fromisoformat(str(win[0])), date.fromisoformat(str(win[1]))
    return None


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
def validate_wfa(run_id: str, runs_path: Path = Depends(get_runs_path)) -> Envelope:
    """Walk-forward folds for a run (v2.md §4.4.1: IS 252d + OOS 63d, rolling 63d).

    Fold date-windows are computed data-free from the run's span via
    ``walk_forward_splits``. The IS-vs-OOS performance ``scatter`` needs a backtest
    per fold (parquet) and stays empty until that runs — so a real ``folds`` list
    ships now while ``scatter`` is honestly marked pending.
    """
    window = _run_window(run_id, runs_path)
    if window is None:
        return pending({"folds": [], "scatter": [], "criteria": _WFA_CRITERIA})
    start, end = window
    folds = walk_forward_splits(start, end, is_days=_WFA_IS_DAYS, oos_days=_WFA_OOS_DAYS)
    fold_rows = [
        {
            "fold": i,
            "is_start": f.is_start.isoformat(),
            "is_end": f.is_end.isoformat(),
            "oos_start": f.oos_start.isoformat(),
            "oos_end": f.oos_end.isoformat(),
        }
        for i, f in enumerate(folds)
    ]
    # folds = real (data-free); scatter (per-fold IS/OOS perf) is parquet-gated.
    # PARTIAL = live-with-gaps: the FE renders the real folds and marks scatter pending.
    return ok(
        {"folds": fold_rows, "scatter": [], "criteria": _WFA_CRITERIA},
        meta={"data_source": DataSource.PARTIAL, "scatter": "pending"},
    )


@router.get("/{run_id}/redline", response_model=Envelope)
def validate_redline(run_id: str) -> Envelope:
    return pending({"pbo": None, "dsr_matrix": []})
