"""Unit tests for the Discord notifier.

Network is fully mocked via httpx.MockTransport — these tests are hermetic.
"""
from __future__ import annotations

from typing import Any

import httpx
import pytest

from quant_platform.services.monitoring_ops.discord_notifier import (
    COLOR_BUY,
    COLOR_SELL,
    MAX_CONTENT_LEN,
    DiscordEmbed,
    DiscordNotifier,
    DiscordSettings,
)


def _settings(**overrides: Any) -> DiscordSettings:
    base: dict[str, Any] = {
        "bot_token": "test_token_123",
        "guild_id": "guild_x",
        "channel_id": "channel_x",
        "user_id": "user_x",
        "alert_target": "channel",
    }
    base.update(overrides)
    return DiscordSettings(**base)


class _RecordingHandler:
    """Captures every request and lets the test assert on it afterward."""

    def __init__(self, dm_channel_id: str = "dm_channel_99") -> None:
        self.requests: list[httpx.Request] = []
        self.payloads: list[Any] = []
        self._dm_channel_id = dm_channel_id

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        body = request.read()
        self.payloads.append(httpx.Response(200, content=body).json() if body else None)

        if request.url.path.endswith("/users/@me/channels"):
            return httpx.Response(200, json={"id": self._dm_channel_id})
        if "/messages" in request.url.path:
            return httpx.Response(200, json={"id": "msg_1"})
        return httpx.Response(404, json={"error": "unexpected route"})


@pytest.fixture
def patched_client(monkeypatch: pytest.MonkeyPatch) -> _RecordingHandler:
    """Replace httpx.Client globally so DiscordNotifier hits MockTransport."""
    handler = _RecordingHandler()
    transport = httpx.MockTransport(handler)
    real_client = httpx.Client

    def factory(*args: Any, **kwargs: Any) -> httpx.Client:
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    monkeypatch.setattr("quant_platform.services.monitoring_ops.discord_notifier.httpx.Client", factory)
    return handler


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_missing_token_raises() -> None:
    with pytest.raises(ValueError, match="DISCORD_BOT_TOKEN"):
        DiscordNotifier(_settings(bot_token=""))


def test_channel_mode_without_channel_id_raises(patched_client: _RecordingHandler) -> None:
    notifier = DiscordNotifier(_settings(channel_id="", alert_target="channel"))
    with pytest.raises(ValueError, match="DISCORD_CHANNEL_ID"):
        notifier.send(content="x")


def test_dm_mode_without_user_id_raises(patched_client: _RecordingHandler) -> None:
    notifier = DiscordNotifier(_settings(user_id="", alert_target="dm"))
    with pytest.raises(ValueError, match="DISCORD_USER_ID"):
        notifier.send(content="x")


def test_send_without_content_or_embed_raises() -> None:
    notifier = DiscordNotifier(_settings())
    with pytest.raises(ValueError, match="content or embed"):
        notifier.send()


# ---------------------------------------------------------------------------
# Channel mode
# ---------------------------------------------------------------------------


def test_send_content_to_channel(patched_client: _RecordingHandler) -> None:
    DiscordNotifier(_settings()).send(content="hello")

    assert len(patched_client.requests) == 1
    req = patched_client.requests[0]
    assert req.url.path.endswith("/channels/channel_x/messages")
    assert req.headers["Authorization"] == "Bot test_token_123"
    assert patched_client.payloads[0] == {"content": "hello"}


def test_content_truncated_at_2000(patched_client: _RecordingHandler) -> None:
    overlong = "a" * (MAX_CONTENT_LEN + 500)
    DiscordNotifier(_settings()).send(content=overlong)
    assert len(patched_client.payloads[0]["content"]) == MAX_CONTENT_LEN


def test_send_embed(patched_client: _RecordingHandler) -> None:
    embed = DiscordEmbed(title="t", description="d", color=COLOR_BUY).add_field(
        "k", "v", inline=True
    )
    DiscordNotifier(_settings()).send(embed=embed)

    payload = patched_client.payloads[0]
    assert "embeds" in payload
    sent = payload["embeds"][0]
    assert sent["title"] == "t"
    assert sent["color"] == COLOR_BUY
    assert sent["fields"] == [{"name": "k", "value": "v", "inline": True}]


# ---------------------------------------------------------------------------
# DM mode
# ---------------------------------------------------------------------------


def test_dm_mode_opens_dm_then_sends(patched_client: _RecordingHandler) -> None:
    DiscordNotifier(_settings(alert_target="dm")).send(content="dm hi")

    assert len(patched_client.requests) == 2
    assert patched_client.requests[0].url.path.endswith("/users/@me/channels")
    assert patched_client.payloads[0] == {"recipient_id": "user_x"}
    assert patched_client.requests[1].url.path.endswith(
        "/channels/dm_channel_99/messages"
    )


def test_dm_channel_id_is_cached(patched_client: _RecordingHandler) -> None:
    notifier = DiscordNotifier(_settings(alert_target="dm"))
    notifier.send(content="first")
    notifier.send(content="second")

    # 1 DM-open + 2 sends, not 2 DM-opens
    dm_opens = [r for r in patched_client.requests if r.url.path.endswith("/users/@me/channels")]
    assert len(dm_opens) == 1


# ---------------------------------------------------------------------------
# High-level helpers
# ---------------------------------------------------------------------------


def test_notify_trade_buy_uses_green(
    patched_client: _RecordingHandler, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Helpers construct DiscordNotifier() with no args → uses DiscordSettings()
    # which reads env. Patch DiscordSettings to inject test config.
    monkeypatch.setattr(
        "quant_platform.services.monitoring_ops.discord_notifier.DiscordSettings",
        lambda: _settings(),
    )

    from quant_platform.services.monitoring_ops.discord_notifier import notify_trade

    notify_trade("BUY", "2330", 600.5, 1000, reason="MA cross")
    sent = patched_client.payloads[0]["embeds"][0]
    assert sent["color"] == COLOR_BUY
    assert sent["title"] == "BUY 2330"
    names = [f["name"] for f in sent["fields"]]
    assert names == ["Price", "Qty", "Reason"]


def test_notify_trade_sell_uses_red(
    patched_client: _RecordingHandler, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "quant_platform.services.monitoring_ops.discord_notifier.DiscordSettings",
        lambda: _settings(),
    )
    from quant_platform.services.monitoring_ops.discord_notifier import notify_trade

    notify_trade("SELL", "2454", 1200, 500)
    assert patched_client.payloads[0]["embeds"][0]["color"] == COLOR_SELL


# ---------------------------------------------------------------------------
# Error propagation
# ---------------------------------------------------------------------------


def test_4xx_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"message": "Missing Permissions"})

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client
    monkeypatch.setattr(
        "quant_platform.services.monitoring_ops.discord_notifier.httpx.Client",
        lambda *a, **kw: real_client(*a, transport=transport, **kw),
    )

    with pytest.raises(httpx.HTTPStatusError):
        DiscordNotifier(_settings()).send(content="x")
