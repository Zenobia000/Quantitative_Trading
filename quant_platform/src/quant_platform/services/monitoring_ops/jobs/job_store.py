"""Job state store (8.H.6) — append-only JSONL snapshots, latest-per-id wins.

Each ``write_job`` appends a state snapshot; ``read_job`` returns the latest for a
job_id. Append-only keeps the full lifecycle trail (queued→running→done) without
in-place mutation, mirroring ``runs_store``.
"""
from __future__ import annotations

import json
from pathlib import Path

from quant_platform.services.monitoring_ops.jobs.models import Job

DEFAULT_JOBS_PATH = Path("reports") / "jobs.jsonl"


def _resolve(path: Path | str | None) -> Path:
    return Path(path) if path is not None else DEFAULT_JOBS_PATH


def write_job(job: Job, path: Path | str | None = None) -> Job:
    """Append a job state snapshot."""
    p = _resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(job.to_dict(), ensure_ascii=False, default=str) + "\n")
    return job


def read_job(job_id: str, path: Path | str | None = None) -> Job | None:
    """Latest snapshot for a job_id, or None if unknown."""
    p = _resolve(path)
    if not p.exists():
        return None
    latest: Job | None = None
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            d = json.loads(line)
            if d.get("job_id") == job_id:
                latest = Job.from_dict(d)
    return latest


def list_jobs(path: Path | str | None = None) -> list[Job]:
    """Latest snapshot of every known job."""
    p = _resolve(path)
    if not p.exists():
        return []
    by_id: dict[str, Job] = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            d = json.loads(line)
            by_id[d["job_id"]] = Job.from_dict(d)
    return list(by_id.values())
