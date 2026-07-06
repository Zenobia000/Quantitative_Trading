"""Monitoring & ops service (W5.2) — Discord notifier + alert rule engine + async jobs.

Groups the observability/operations concerns behind ``services.monitoring_ops``:
the alert rule engine and Discord notifier (ADR-009) plus the dependency-free
in-process async job runner (8.H.6).
"""
