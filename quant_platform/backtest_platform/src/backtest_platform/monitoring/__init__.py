"""Re-export shim (W5.2a) — moved to ``services.monitoring_ops``.

Monitoring & alerting (ADR-009): Discord notifier + alert rule engine.
"""
from __future__ import annotations

from backtest_platform.services.monitoring_ops.alert_rules import (
    Alert,
    AlertLevel,
    AlertRouter,
    Rule,
    silent_hours,
)
from backtest_platform.services.monitoring_ops.discord_notifier import (
    DiscordEmbed,
    DiscordNotifier,
    DiscordSettings,
    notify_error,
    notify_info,
    notify_trade,
)

__all__ = [
    "Alert",
    "AlertLevel",
    "AlertRouter",
    "DiscordEmbed",
    "DiscordNotifier",
    "DiscordSettings",
    "Rule",
    "notify_error",
    "notify_info",
    "notify_trade",
    "silent_hours",
]
