"""Saved-views store (8.H.4) — persisted Runs-Table filter/column presets.

A "saved view" is a named bundle of the research Runs-Table UI state (columns +
filters, mirroring the frontend TanStack Query URL state). Append-only JSONL,
same dependency-free philosophy as ``runs_store``. ``view_id`` is a deterministic
content hash so re-saving the same view is idempotent (no wall-clock id).
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

DEFAULT_SAVED_VIEWS_PATH = Path("reports") / "saved_views.jsonl"


def _view_id(name: str, query: Mapping[str, Any]) -> str:
    key = name + "|" + json.dumps(query, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha1(key.encode()).hexdigest()[:12]


def _resolve(path: Path | str | None) -> Path:
    return Path(path) if path is not None else DEFAULT_SAVED_VIEWS_PATH


def list_views(path: Path | str | None = None) -> list[dict[str, Any]]:
    """All saved views (latest write per id wins; empty list if none yet)."""
    p = _resolve(path)
    if not p.exists():
        return []
    by_id: dict[str, dict[str, Any]] = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rec = json.loads(line)
            by_id[rec["id"]] = rec
    return list(by_id.values())


def create_view(
    name: str, query: Mapping[str, Any], path: Path | str | None = None
) -> dict[str, Any]:
    """Append a saved view; returns the stored record ({id, name, query})."""
    p = _resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    record = {"id": _view_id(name, query), "name": name, "query": dict(query)}
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    return record
