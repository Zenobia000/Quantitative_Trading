"""Run-tags store (8.H.4) — orthogonal labels on runs (append-only JSONL).

Tags are orthogonal to preset/strategy (e.g. "candidate", "archived",
"smallcap-probe"). ``tag_run`` records the *latest* tag set per run_id; the
projection in :func:`tags_for` returns the most recent write. Dependency-free
JSONL, same philosophy as ``runs_store``.
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

DEFAULT_RUN_TAGS_PATH = Path("reports") / "run_tags.jsonl"


def _resolve(path: Path | str | None) -> Path:
    return Path(path) if path is not None else DEFAULT_RUN_TAGS_PATH


def tag_run(
    run_id: str, tags: Sequence[str], path: Path | str | None = None
) -> dict[str, object]:
    """Record (replace) the tag set for a run; returns {run_id, tags}."""
    p = _resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    record = {"run_id": run_id, "tags": list(dict.fromkeys(tags))}  # dedupe, keep order
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def tags_for(run_id: str, path: Path | str | None = None) -> list[str]:
    """Latest tag set for a run_id (empty list if never tagged)."""
    p = _resolve(path)
    if not p.exists():
        return []
    latest: list[str] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rec = json.loads(line)
            if rec.get("run_id") == run_id:
                latest = rec.get("tags", [])
    return latest
