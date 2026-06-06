"""``/research`` — research-zone projections over the runs ledger.

The ledger (``research.runs_store``) is the single source of truth; this router
derives *strategy*-level views from it without any new persistence. A "strategy"
is keyed by ``preset`` (v2 / v3 / …) — every run carries one, so grouping the
append-only ledger by preset yields a roster with best-KPI, validation status and
run counts. Stateful research features (saved-views, validate/promote state
machines, sweep jobs) need new persistence and are intentionally NOT wired here.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Query

from backtest_platform.api.deps import get_runs_path
from backtest_platform.api.envelope import Envelope, ok, page_meta
from backtest_platform.research.runs_store import read_runs

router = APIRouter(prefix="/research", tags=["research"])


def _validation_status(gate_status: str | None) -> str:
    """Map a run's gate_status to a coarse strategy validation_status."""
    if gate_status in ("PASS", "IS_PASS"):
        return "is_pass"
    if gate_status in ("FAIL", "IS_FAIL"):
        return "is_fail"
    return "draft"


def _best_kpi(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Pick the metrics dict of the run with the highest Sharpe (None-safe)."""
    best: dict[str, Any] | None = None
    best_sharpe = float("-inf")
    for r in records:
        m = r.get("metrics") or {}
        s = m.get("sharpe")
        if isinstance(s, (int, float)) and s > best_sharpe:
            best_sharpe = s
            best = m
    return best or {}


def _project_strategies(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group ledger records by preset into a strategy roster."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        preset = r.get("preset") or "—"
        groups.setdefault(preset, []).append(r)

    out: list[dict[str, Any]] = []
    for preset, recs in sorted(groups.items()):
        statuses = [_validation_status(r.get("gate_status")) for r in recs]
        validation_status = "is_pass" if "is_pass" in statuses else statuses[0] if statuses else "draft"
        out.append(
            {
                "strategy_id": preset,
                "version": preset,
                "best_kpi": _best_kpi(recs),
                "validation_status": validation_status,
                "stage": "draft",  # 晉升狀態機尚未持久化（needs-work）
                "runs_count": len(recs),
            }
        )
    return out


def _pending(data: Any, ttl: int = 300) -> Envelope:
    """Typed-empty envelope for research features needing new persistence/logic."""
    return ok(data, meta={"data_source": "pending", "ttl": ttl})


@router.get("/strategies", response_model=Envelope, tags=["research"])
def list_strategies(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    runs_path: Path = Depends(get_runs_path),
) -> Envelope:
    """Strategy roster projected over the runs ledger (grouped by preset)."""
    strategies = _project_strategies(read_runs(runs_path))
    total = len(strategies)
    start = (page - 1) * limit
    window = strategies[start : start + limit]
    return ok(window, meta=page_meta(total, page, limit))


@router.get("/strategies/{strategy_id}/versions", response_model=Envelope)
def strategy_versions(strategy_id: str, runs_path: Path = Depends(get_runs_path)) -> Envelope:
    """Version timeline for a strategy — runs of this preset, newest first (real projection)."""
    recs = [r for r in read_runs(runs_path) if (r.get("preset") or "—") == strategy_id]
    versions = [
        {
            "version": r.get("preset"),
            "run_id": r.get("run_id"),
            "hypothesis": r.get("hypothesis"),
            "gate_status": r.get("gate_status"),
            "is_start": r.get("is_start"),
            "is_end": r.get("is_end"),
        }
        for r in recs[::-1]
    ]
    return ok(versions, meta={"ttl": 300})


# ---- research features needing new persistence/logic (typed stubs) ------
@router.get("/universe-filters", response_model=Envelope)
def universe_filters() -> Envelope:
    return _pending({"industries": [], "cap_buckets": [], "liquidity": []})


@router.get("/saved-views", response_model=Envelope)
def saved_views() -> Envelope:
    return _pending([])


@router.post("/saved-views", response_model=Envelope)
def saved_views_create() -> Envelope:
    return _pending({"id": "stub"})


@router.post("/trials/increment", response_model=Envelope)
def trials_increment() -> Envelope:
    return _pending({"cumulative_trials": None})


# Validate gate state machine (M3.6, needs persistence)
@router.get("/validate/{run_id}/gate-state", response_model=Envelope)
def gate_state(run_id: str) -> Envelope:
    return _pending({"run_id": run_id, "validation_status": None, "stage": None})


@router.get("/validate/{run_id}/wfa", response_model=Envelope)
def validate_wfa(run_id: str) -> Envelope:
    return _pending({"folds": [], "scatter": []})


@router.get("/validate/{run_id}/redline", response_model=Envelope)
def validate_redline(run_id: str) -> Envelope:
    return _pending({"pbo": None, "dsr_matrix": []})


# Promote state machine (M3.6, needs persistence)
@router.get("/promote/{strategy_id}", response_model=Envelope)
def promote_state(strategy_id: str) -> Envelope:
    return _pending({"strategy_id": strategy_id, "stage": "draft", "history": [], "gates": []})


@router.get("/promote/{strategy_id}/audit", response_model=Envelope)
def promote_audit(strategy_id: str) -> Envelope:
    return _pending([])
