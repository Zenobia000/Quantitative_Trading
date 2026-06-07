"""Async job runner (8.H.6) — dependency-free in-process jobs with JSONL state.

The research loop must not block on a long sweep/ingest: ``POST`` a job, get a
``job_id`` back, poll ``/.../status``. This package provides the minimal job
abstraction (no Celery/Prefect): a job store (append-only JSONL state snapshots),
a synchronous ``run_job`` (deterministic, the unit-test path) and a thin
``submit`` that runs it in a daemon thread (the production async path).
"""
from backtest_platform.jobs.job_runner import run_job, submit
from backtest_platform.jobs.job_store import list_jobs, read_job, write_job
from backtest_platform.jobs.models import Job, JobStatus

__all__ = ["Job", "JobStatus", "run_job", "submit", "read_job", "write_job", "list_jobs"]
