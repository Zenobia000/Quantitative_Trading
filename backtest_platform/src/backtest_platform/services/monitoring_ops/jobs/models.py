"""Job model + lifecycle states (8.H.6)."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class JobStatus(str, Enum):
    """Job lifecycle: queued → running → (done | failed)."""

    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass(frozen=True)
class Job:
    """An immutable snapshot of a job's state (each transition is a new snapshot)."""

    job_id: str
    kind: str  # e.g. "sweep" | "ingest"
    status: JobStatus
    progress: float = 0.0  # 0.0..1.0
    result: Any | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Job":
        return cls(
            job_id=d["job_id"],
            kind=d["kind"],
            status=JobStatus(d["status"]),
            progress=d.get("progress", 0.0),
            result=d.get("result"),
            error=d.get("error"),
        )
