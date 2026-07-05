"""Re-export shim (W5.2b) — moved to ``services.monitoring_ops.jobs.job_runner``.

Job runner (8.H.6): synchronous ``run_job`` + threaded ``submit``.
"""
from backtest_platform.services.monitoring_ops.jobs.job_runner import (
    make_job_id,
    run_job,
    submit,
)

__all__ = ["make_job_id", "run_job", "submit"]
