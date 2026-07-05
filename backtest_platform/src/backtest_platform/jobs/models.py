"""Re-export shim (W5.2b) — moved to ``services.monitoring_ops.jobs.models``.

Job dataclasses (8.H.6): ``Job`` snapshot + ``JobStatus`` lifecycle enum.
"""
from backtest_platform.services.monitoring_ops.jobs.models import Job, JobStatus

__all__ = ["Job", "JobStatus"]
