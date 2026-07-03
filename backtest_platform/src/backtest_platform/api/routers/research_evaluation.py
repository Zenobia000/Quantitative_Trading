"""``/research/profiles`` + ``/research/evaluations`` — the evaluation read surface.

Serves the four built-in :class:`EvaluationProfile` recipes (the profile picker),
one persisted ``EvaluationResult`` (the Report Viewer's headline/scorecards/verdict),
and its report-pack manifest. All read-only projections over the append-only
evaluation ledger (``data_source = ledger``); the run itself is driven by the CLI
(``research evaluate``), keeping the API dependency-light (rebuild Goal 3 / ADR-039).
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from backtest_platform.api.deps import get_evaluations_path
from backtest_platform.api.envelope import DataSource, Envelope, ok
from backtest_platform.research.evaluation.profiles import get_profile, list_profiles
from backtest_platform.research.evaluation.store import get_evaluation

router = APIRouter(prefix="/research", tags=["research-evaluation"])

_RESEARCH_TTL = 300


@router.get("/profiles", response_model=Envelope)
def list_evaluation_profiles() -> Envelope:
    """The built-in evaluation profiles (triage → deployment order)."""
    return ok([p.model_dump() for p in list_profiles()], meta={"ttl": _RESEARCH_TTL})


@router.get("/profiles/{name}", response_model=Envelope)
def get_evaluation_profile(name: str) -> Envelope:
    """One evaluation profile by name."""
    try:
        profile = get_profile(name)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail={"resource": "profile", "id": name, "message": f"unknown evaluation profile {name!r}"},
        ) from None
    return ok(profile.model_dump(), meta={"ttl": _RESEARCH_TTL})


@router.get("/evaluations/{evaluation_id}", response_model=Envelope)
def get_evaluation_result(
    evaluation_id: str, path: Path = Depends(get_evaluations_path)
) -> Envelope:
    """One persisted ``EvaluationResult`` (verdict + scorecards + checks + lineage)."""
    result = get_evaluation(evaluation_id, path)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={"resource": "evaluation", "id": evaluation_id,
                    "message": f"no evaluation {evaluation_id!r}"},
        )
    return ok(result, meta={"data_source": DataSource.LEDGER, "ttl": _RESEARCH_TTL})


@router.get("/evaluations/{evaluation_id}/report", response_model=Envelope)
def get_evaluation_report(
    evaluation_id: str, path: Path = Depends(get_evaluations_path)
) -> Envelope:
    """The ``ReportPackManifest`` for an evaluation (files + lineage on disk)."""
    result = get_evaluation(evaluation_id, path)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={"resource": "evaluation", "id": evaluation_id,
                    "message": f"no evaluation {evaluation_id!r}"},
        )
    ref = result.get("report_pack_ref")
    manifest_path = Path(ref) if ref else None
    if manifest_path is None or not manifest_path.exists():
        raise HTTPException(
            status_code=404,
            detail={"resource": "report_pack", "id": evaluation_id,
                    "message": "report pack manifest not found on disk"},
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return ok(manifest, meta={"data_source": DataSource.LEDGER, "ttl": _RESEARCH_TTL})
