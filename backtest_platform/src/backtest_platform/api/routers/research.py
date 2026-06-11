"""``/research`` — research-zone projections over the runs ledger.

The ledger (``research.runs_store``) is the single source of truth; this router
derives *strategy*-level views from it without any new persistence. A "strategy"
is keyed by ``preset`` (v2 / v3 / …) — every run carries one, so grouping the
append-only ledger by preset yields a roster with best-KPI, validation status and
run counts.

Stateful research features were split into sibling routers in the M3
parallelization seam (so each work-stream owns a disjoint file):
``research_validate`` / ``research_promote`` (S3), ``research_registry`` (S5,
saved-views + trials), ``research_sweep`` (S2). This module keeps only the
stateless read projections (strategy roster + config-driven universe filters).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Query

from backtest_platform.api.deps import get_runs_path
from backtest_platform.api.envelope import Envelope, ok, page_meta
from backtest_platform.api.response_models import StrategyRow, UniverseFiltersData
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
        statuses = {_validation_status(r.get("gate_status")) for r in recs}
        # 確定性優先序（避免 order-dependent）：任一 run is_pass → 策略 is_pass；否則 is_fail；否則 draft
        validation_status = next((s for s in ("is_pass", "is_fail", "draft") if s in statuses), "draft")
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


@router.get("/strategies", response_model=Envelope[list[StrategyRow]], tags=["research"])
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


# ---- universe filter spec (real, config-driven) -------------------------
@router.get("/universe-filters", response_model=Envelope[UniverseFiltersData])
def universe_filters() -> Envelope:
    """Supported universe filters from ``UniverseConfig.default()`` (real config).

    Markets / capital / liquidity / price thresholds + exclusion reasons are
    config-driven and returned as-is. ``industries`` is data-derived (needs the
    loaded universe metadata) — empty until the bundle is ingested.
    """
    from backtest_platform.data.universe import UniverseConfig

    cfg = UniverseConfig.default()
    return ok(
        {
            "markets": ["TWSE", "TPEX"],
            "min_market_cap": cfg.min_market_cap,
            "min_avg_volume_lots": cfg.min_avg_volume_lots,
            "min_avg_amount": cfg.min_avg_amount,
            "price_range": [cfg.min_price, cfg.max_price],
            "min_listed_days": cfg.min_listed_days,
            "exclude_governance_grades": list(cfg.exclude_governance_grades),
            "exclude_reasons": [
                "etf", "warrant", "convertible_bond", "attention_stock", "full_delivery",
                "wrong_market", "market_cap_too_low", "volume_too_low", "amount_too_low",
                "price_below_floor", "price_above_cap", "newly_listed", "bad_governance", "ex_dividend_quiet",
            ],
            "industries": [],  # data-derived（待 bundle ingest）
        },
        meta={"ttl": 600},
    )
