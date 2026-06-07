"""Job runner (8.H.6) — synchronous ``run_job`` + threaded ``submit``.

``run_job`` executes a callable, persisting queued→running→(done|failed)
snapshots to the job store; it is synchronous and deterministic (the unit-test
path, and fine for short jobs). ``submit`` returns immediately with a queued job
and runs ``run_job`` in a daemon thread (the production async path) so the API
can answer ``POST`` with a ``job_id`` without blocking.

A deterministic ``job_id`` is derived from (kind, key) so re-submitting the same
logical job is identifiable without a wall-clock id.
"""
from __future__ import annotations

import hashlib
import threading
from collections.abc import Callable
from typing import Any

from backtest_platform.jobs.job_store import write_job
from backtest_platform.jobs.models import Job, JobStatus


def make_job_id(kind: str, key: str) -> str:
    """Deterministic job id from kind + a caller-supplied key."""
    return hashlib.sha1(f"{kind}|{key}".encode()).hexdigest()[:12]


def run_job(
    job_id: str,
    kind: str,
    fn: Callable[[], Any],
    path=None,
) -> Job:
    """Run ``fn`` synchronously, persisting each lifecycle transition.

    Returns the terminal job (DONE with ``result``, or FAILED with ``error``).
    Exceptions in ``fn`` are captured into the FAILED snapshot — the runner never
    raises, so a caller polling status always sees a terminal state.
    """
    write_job(Job(job_id, kind, JobStatus.QUEUED), path)
    write_job(Job(job_id, kind, JobStatus.RUNNING, progress=0.0), path)
    try:
        result = fn()
        job = Job(job_id, kind, JobStatus.DONE, progress=1.0, result=result)
    except Exception as exc:  # noqa: BLE001 — captured into job state, not swallowed
        job = Job(job_id, kind, JobStatus.FAILED, error=str(exc))
    return write_job(job, path)


def submit(
    kind: str,
    key: str,
    fn: Callable[[], Any],
    path=None,
) -> Job:
    """Enqueue ``fn`` and run it in a daemon thread; return the QUEUED job now.

    The caller gets a ``job_id`` immediately and polls the store for completion.
    """
    job_id = make_job_id(kind, key)
    queued = write_job(Job(job_id, kind, JobStatus.QUEUED), path)
    threading.Thread(
        target=run_job, args=(job_id, kind, fn, path), daemon=True
    ).start()
    return queued
