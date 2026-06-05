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
