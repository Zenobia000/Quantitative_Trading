"""Per-run validation state store (8.H.7) — event-sourced, append-only.

Persists a run's journey through the IS→WFA→OOS gate (``validation.gate_machine``)
as an append-only event log. Append-only *is* the immutable audit: every status
transition is a new line, never an in-place edit, so the full validation history
of a run survives and cannot be silently rewritten (anti-overfit accountability).
Dependency-free JSONL, same philosophy as ``runs_store``.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_VALIDATION_PATH = Path("reports") / "validation_events.jsonl"


def _resolve(path: Path | str | None) -> Path:
    return Path(path) if path is not None else DEFAULT_VALIDATION_PATH


def record(
    run_id: str,
    validation_status: str,
    stage: str,
    note: str = "",
    path: Path | str | None = None,
) -> dict[str, Any]:
    """Append one validation transition event; returns the stored event."""
    p = _resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "run_id": run_id,
        "validation_status": validation_status,
        "stage": stage,
        "note": note,
        "at": datetime.now().isoformat(timespec="seconds"),
    }
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def history(run_id: str, path: Path | str | None = None) -> list[dict[str, Any]]:
    """Full ordered transition history for a run (empty if none)."""
    p = _resolve(path)
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            ev = json.loads(line)
            if ev.get("run_id") == run_id:
                out.append(ev)
    return out


def current(run_id: str, path: Path | str | None = None) -> dict[str, Any] | None:
    """Latest validation state for a run ({validation_status, stage}); None if none."""
    hist = history(run_id, path)
    if not hist:
        return None
    last = hist[-1]
    return {"validation_status": last["validation_status"], "stage": last["stage"]}
