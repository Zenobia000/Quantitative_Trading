"""Append-only run ledger (JSONL).

The minimal runs table for v0.1 — collects what used to be散裝 reports/perf__/
summary__ orphan files into one append-only, lineage-bearing ledger. No DB yet
(TimescaleDB runs table is v0.2/M3); JSONL keeps it dependency-free and diffable.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

DEFAULT_RUNS_PATH = Path("reports") / "runs.jsonl"


def append_run(record: Mapping, path: Path | str = DEFAULT_RUNS_PATH) -> None:
    """Append one run record as a JSON line (creates parent dirs)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def read_runs(path: Path | str = DEFAULT_RUNS_PATH) -> list[dict]:
    """Read all run records (empty list if the ledger does not exist yet)."""
    p = Path(path)
    if not p.exists():
        return []
    out: list[dict] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out
