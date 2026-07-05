"""Append-only evaluation ledger (JSONL) — rebuild Goal 3.

Every ``EvaluationResult`` the orchestrator produces is appended here, INCLUDING
failed / weak / negative / data-issue strategies (global acceptance #5 — a research
asset is never discarded). Same dependency-free, diffable, event-log philosophy as
``research.runs_store`` / ``promotion_store``: current state for one evaluation id is
the LATEST record carrying that id (a re-run appends, never overwrites).
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

DEFAULT_EVALUATIONS_PATH = Path("reports") / "evaluations.jsonl"


def append_evaluation(record: Mapping[str, Any], path: Path | str = DEFAULT_EVALUATIONS_PATH) -> None:
    """Append one evaluation result as a JSON line (creates parent dirs)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def read_evaluations(path: Path | str = DEFAULT_EVALUATIONS_PATH) -> list[dict[str, Any]]:
    """All evaluation records in append order (empty list if none)."""
    p = Path(path)
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def get_evaluation(
    evaluation_id: str, path: Path | str = DEFAULT_EVALUATIONS_PATH
) -> dict[str, Any] | None:
    """The latest record for ``evaluation_id`` (a re-run folds to its last append)."""
    match: dict[str, Any] | None = None
    for rec in read_evaluations(path):
        if rec.get("evaluation_id") == evaluation_id:
            match = rec
    return match
