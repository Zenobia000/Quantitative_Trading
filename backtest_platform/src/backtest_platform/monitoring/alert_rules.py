"""Re-export shim (W5.2a) — moved to ``services.monitoring_ops.alert_rules``.

Alert rule engine (ADR-009 / spec 20 §4): rule spec, silent-hours gating, router.
"""
from backtest_platform.services.monitoring_ops.alert_rules import (
    DEDUPE_WINDOW,
    RULES,
    SILENT_END,
    SILENT_START,
    Alert,
    AlertLevel,
    AlertRouter,
    Clock,
    Metrics,
    Rule,
    rules_spec,
    silent_hours,
)

__all__ = [
    "DEDUPE_WINDOW",
    "RULES",
    "SILENT_END",
    "SILENT_START",
    "Alert",
    "AlertLevel",
    "AlertRouter",
    "Clock",
    "Metrics",
    "Rule",
    "rules_spec",
    "silent_hours",
]
