"""Re-export shim (W5.2b) — moved to ``services.monitoring_ops.jobs.job_store``.

Job state store (8.H.6): append-only JSONL snapshots, latest-per-id wins.
"""
from backtest_platform.services.monitoring_ops.jobs.job_store import (
    DEFAULT_JOBS_PATH,
    list_jobs,
    read_job,
    write_job,
)

__all__ = ["DEFAULT_JOBS_PATH", "list_jobs", "read_job", "write_job"]
