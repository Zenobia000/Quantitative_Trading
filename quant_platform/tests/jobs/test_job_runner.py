"""jobs — synchronous run_job, threaded submit, append-only job store (8.H.6)."""
from __future__ import annotations

import time

from quant_platform.services.monitoring_ops.jobs import job_store, run_job, submit
from quant_platform.services.monitoring_ops.jobs.job_runner import make_job_id
from quant_platform.services.monitoring_ops.jobs.models import JobStatus


def _wait_terminal(job_id, path, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = job_store.read_job(job_id, path=path)
        if job and job.status in (JobStatus.DONE, JobStatus.FAILED):
            return job
        time.sleep(0.01)
    raise AssertionError("job did not reach a terminal state in time")


def test_run_job_done_persists_lifecycle(tmp_path) -> None:
    p = tmp_path / "jobs.jsonl"
    job = run_job("j1", "sweep", lambda: {"n": 3}, p)
    assert job.status is JobStatus.DONE
    assert job.result == {"n": 3}
    assert job.progress == 1.0
    # the full lifecycle trail is appended (queued, running, done)
    raw = p.read_text().strip().splitlines()
    assert len(raw) == 3
    assert job_store.read_job("j1", path=p).status is JobStatus.DONE


def test_run_job_failure_is_captured_not_raised(tmp_path) -> None:
    p = tmp_path / "jobs.jsonl"

    def boom():
        raise RuntimeError("kaboom")

    job = run_job("j2", "sweep", boom, p)
    assert job.status is JobStatus.FAILED
    assert "kaboom" in job.error


def test_submit_runs_in_background_to_completion(tmp_path) -> None:
    p = tmp_path / "jobs.jsonl"
    queued = submit("sweep", "key-1", lambda: {"ok": True}, p)
    assert queued.status is JobStatus.QUEUED
    assert queued.job_id == make_job_id("sweep", "key-1")
    final = _wait_terminal(queued.job_id, p)
    assert final.status is JobStatus.DONE
    assert final.result == {"ok": True}


def test_read_job_unknown_is_none(tmp_path) -> None:
    assert job_store.read_job("ghost", path=tmp_path / "jobs.jsonl") is None


def test_make_job_id_deterministic() -> None:
    assert make_job_id("sweep", "k") == make_job_id("sweep", "k")
    assert make_job_id("sweep", "k") != make_job_id("ingest", "k")
