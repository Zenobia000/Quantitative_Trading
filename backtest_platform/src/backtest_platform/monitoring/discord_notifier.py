"""Re-export shim (W5.2a) — moved to ``services.monitoring_ops.discord_notifier``.

Discord notifier (ADR-009): embeds, settings, and notify_* helpers.
"""
from backtest_platform.services.monitoring_ops.discord_notifier import (
    COLOR_BUY,
    COLOR_ERROR,
    COLOR_INFO,
    COLOR_SELL,
    COLOR_WARN,
    MAX_CONTENT_LEN,
    MAX_EMBED_DESC_LEN,
    DiscordEmbed,
    DiscordNotifier,
    DiscordSettings,
    notify_error,
    notify_info,
    notify_trade,
)

__all__ = [
    "COLOR_BUY",
    "COLOR_ERROR",
    "COLOR_INFO",
    "COLOR_SELL",
    "COLOR_WARN",
    "MAX_CONTENT_LEN",
    "MAX_EMBED_DESC_LEN",
    "DiscordEmbed",
    "DiscordNotifier",
    "DiscordSettings",
    "notify_error",
    "notify_info",
    "notify_trade",
]
