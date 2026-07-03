"""``/home`` — cockpit BFF aggregation (ADR-021 §6.4).

The landing cockpit assembles a cross-zone snapshot in one call (latency-sensitive
first paint; aggregation logic is a backend concern). ``research-status`` and
``recent`` are real projections over the runs ledger (``data_source=DataSource.LEDGER``);
``fleet`` and ``system-health`` aggregate Monitor/System sources that have no live
producer yet, so they ship as typed-empty stubs (``data_source=DataSource.PENDING``).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends

from backtest_platform.api.deps import get_runs_path
from backtest_platform.api.envelope import DataSource, Envelope, ok
from backtest_platform.research.runs_store import read_runs

router = APIRouter(prefix="/home", tags=["home"])


@router.get("/research-status", response_model=Envelope)
def research_status(runs_path: Path = Depends(get_runs_path)) -> Envelope:
    """Active research snapshot projected over the ledger (real)."""
    records = read_runs(runs_path)
    latest = records[-1] if records else None
    return ok(
        {
            "total_runs": len(records),
            "latest_gate_status": (latest or {}).get("gate_status"),
            "is_gate_blocker": (latest or {}).get("gate_summary"),
            # trials/DSR/power-gauge 需 trials store（needs-work）→ null
            "trials": None,
            "dsr": None,
        },
        meta={"data_source": DataSource.LEDGER, "ttl": 300},
    )


@router.get("/recent", response_model=Envelope)
def recent(runs_path: Path = Depends(get_runs_path)) -> Envelope:
    """Most-recent activity (last runs) projected over the ledger (real)."""
    records = read_runs(runs_path)
    items: list[dict[str, Any]] = [
        {"type": "run", "run_id": r.get("run_id"), "preset": r.get("preset"), "gate_status": r.get("gate_status")}
        for r in records[-8:][::-1]
    ]
    return ok(items, meta={"data_source": DataSource.LEDGER, "ttl": 300})


@router.get("/fleet", response_model=Envelope)
def fleet() -> Envelope:
    return ok([], meta={"data_source": DataSource.PENDING, "ttl": 300})


@router.get("/system-health", response_model=Envelope)
def system_health() -> Envelope:
    return ok({}, meta={"data_source": DataSource.PENDING, "ttl": 300})
