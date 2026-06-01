"""Discord notifier — send-only client for trading alerts.

Uses Discord REST API directly via httpx. No discord.py runtime, no event loop.
Designed to be cheap to import and safe to call from sync Prefect tasks, CLI
scripts, or pytest.

See ADR-009 for the broader monitoring architecture.
"""
from __future__ import annotations

from typing import Any, Literal

import httpx
from loguru import logger
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Color constants — Discord embeds take an int (decimal), conventionally written hex.
COLOR_BUY = 0x00C853
COLOR_SELL = 0xD32F2F
COLOR_INFO = 0x1976D2
COLOR_WARN = 0xFFA000
COLOR_ERROR = 0xB71C1C

# Discord hard limits
MAX_CONTENT_LEN = 2000
MAX_EMBED_DESC_LEN = 4096


class DiscordSettings(BaseSettings):
    """Env-driven config. All keys read from DISCORD_* env vars or .env file."""

    model_config = SettingsConfigDict(
        env_prefix="DISCORD_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = ""
    guild_id: str = ""
    channel_id: str = ""
    user_id: str = ""
    alert_target: Literal["channel", "dm"] = "channel"


class DiscordEmbed(BaseModel):
    """Subset of Discord embed object — only fields we use."""

    title: str | None = None
    description: str | None = None
    color: int | None = None
    fields: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: str | None = None  # ISO8601

    def add_field(self, name: str, value: str, inline: bool = False) -> DiscordEmbed:
        self.fields.append({"name": name, "value": value, "inline": inline})
        return self


class DiscordNotifier:
    """Send-only Discord client.

    One instance can be reused across many sends; DM channel id is cached after
    first resolve. Not thread-safe for the DM cache, but Discord create-DM is
    idempotent so the cost of a race is one extra API call.
    """

    BASE_URL = "https://discord.com/api/v10"

    def __init__(self, settings: DiscordSettings | None = None) -> None:
        self._settings = settings or DiscordSettings()
        if not self._settings.bot_token:
            raise ValueError(
                "DISCORD_BOT_TOKEN is empty. Set it in .env or pass DiscordSettings explicitly."
            )
        self._dm_channel_id: str | None = None

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bot {self._settings.bot_token}",
            "Content-Type": "application/json",
            "User-Agent": "QuantTradingBot (https://internal, 0.1.0)",
        }

    def _resolve_channel_id(self, client: httpx.Client) -> str:
        if self._settings.alert_target == "channel":
            if not self._settings.channel_id:
                raise ValueError(
                    "DISCORD_CHANNEL_ID is required when DISCORD_ALERT_TARGET=channel"
                )
            return self._settings.channel_id

        # DM mode — open a DM channel with the user, cached.
        if self._dm_channel_id is not None:
            return self._dm_channel_id
        if not self._settings.user_id:
            raise ValueError("DISCORD_USER_ID is required when DISCORD_ALERT_TARGET=dm")
        resp = client.post(
            f"{self.BASE_URL}/users/@me/channels",
            json={"recipient_id": self._settings.user_id},
            headers=self._headers,
        )
        resp.raise_for_status()
        self._dm_channel_id = str(resp.json()["id"])
        return self._dm_channel_id

    def send(
        self,
        content: str | None = None,
        embed: DiscordEmbed | None = None,
    ) -> None:
        """POST a message. Either `content` (plain text) or `embed` (rich card), or both."""
        if not content and not embed:
            raise ValueError("send() requires either content or embed")

        payload: dict[str, Any] = {}
        if content:
            payload["content"] = content[:MAX_CONTENT_LEN]
        if embed:
            if embed.description and len(embed.description) > MAX_EMBED_DESC_LEN:
                embed = embed.model_copy(
                    update={"description": embed.description[:MAX_EMBED_DESC_LEN]}
                )
            payload["embeds"] = [embed.model_dump(exclude_none=True)]

        with httpx.Client(timeout=10.0) as client:
            channel_id = self._resolve_channel_id(client)
            resp = client.post(
                f"{self.BASE_URL}/channels/{channel_id}/messages",
                json=payload,
                headers=self._headers,
            )
            if resp.status_code >= 400:
                logger.error(
                    "Discord send failed: {status} {body}",
                    status=resp.status_code,
                    body=resp.text[:500],
                )
                resp.raise_for_status()
            logger.debug(
                "Discord message sent to {target}", target=self._settings.alert_target
            )


# -----------------------------------------------------------------------------
# High-level helpers — these are what the rest of the codebase should call.
# Each creates its own notifier so call sites don't need to manage lifetime.
# -----------------------------------------------------------------------------


def notify_trade(
    action: str,
    symbol: str,
    price: float,
    qty: int,
    reason: str = "",
) -> None:
    """Trade signal alert. action ∈ {'BUY', 'SELL'} drives color."""
    color = COLOR_BUY if action.upper() == "BUY" else COLOR_SELL
    embed = (
        DiscordEmbed(title=f"{action.upper()} {symbol}", color=color)
        .add_field("Price", f"{price:,.2f}", inline=True)
        .add_field("Qty", f"{qty:,}", inline=True)
    )
    if reason:
        embed.add_field("Reason", reason)
    DiscordNotifier().send(embed=embed)


def notify_error(stage: str, error: str | Exception) -> None:
    """Error alert. Use during ETL, signal generation, or order execution failure."""
    embed = DiscordEmbed(
        title=f"[ERROR] {stage}",
        description=f"```\n{str(error)[:500]}\n```",
        color=COLOR_ERROR,
    )
    DiscordNotifier().send(embed=embed)


def notify_info(text: str) -> None:
    """Plain-text info alert. Cheapest path."""
    DiscordNotifier().send(content=text)
