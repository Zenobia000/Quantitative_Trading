"""Per-strategy promotion audit store (8.H.7) — event-sourced, append-only.

Records a strategy's promotion stage transitions (draft → paper → live …) as an
append-only event log. Append-only *is* the immutable ``promotion_audit``: a
promotion to live can never be silently un-recorded, and who/when/why is always
recoverable. Dependency-free JSONL, same philosophy as ``runs_store``.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_PROMOTION_PATH = Path("reports") / "promotion_events.jsonl"


def _resolve(path: Path | str | None) -> Path:
    return Path(path) if path is not None else DEFAULT_PROMOTION_PATH


def record(
    strategy_id: str,
    stage: str,
    note: str = "",
    actor: str = "system",
    path: Path | str | None = None,
) -> dict[str, Any]:
    """Append one promotion event; returns the stored event."""
    p = _resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "strategy_id": strategy_id,
        "stage": stage,
        "note": note,
        "actor": actor,
        "at": datetime.now().isoformat(timespec="seconds"),
    }
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def audit(strategy_id: str, path: Path | str | None = None) -> list[dict[str, Any]]:
    """Full ordered promotion audit trail for a strategy (empty if none)."""
    p = _resolve(path)
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            ev = json.loads(line)
            if ev.get("strategy_id") == strategy_id:
                out.append(ev)
    return out


def current_stage(strategy_id: str, path: Path | str | None = None) -> str:
    """Latest promotion stage for a strategy ('draft' if never promoted)."""
    trail = audit(strategy_id, path)
    return trail[-1]["stage"] if trail else "draft"
