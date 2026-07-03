"""Monitoring & alerting (ADR-009): Discord notifier + alert rule engine."""
from __future__ import annotations

from backtest_platform.monitoring.alert_rules import (
    Alert,
    AlertLevel,
    AlertRouter,
    Rule,
    silent_hours,
)
from backtest_platform.monitoring.discord_notifier import (
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
