"""Central runtime settings — one typed place for env-driven config (ADR-027 Stage 2).

Before this, credentials / DB connection / paths were read via scattered
``os.environ.get(...)`` across ``data/``, ``api/``, ``engines/`` (each with its own
default string). This consolidates them into one ``Settings`` model (the same
``pydantic_settings`` convention as ``monitoring.DiscordSettings``) so every knob
is discoverable + typed + ``.env``-aware.

``get_settings()`` returns a FRESH instance each call (not cached) so tests that
``monkeypatch.setenv`` and runtime that sets env mid-process both see current
values — matching the old per-call ``os.environ.get`` behaviour.

Reads only real environment variables (NOT a ``.env`` file) — preserving the
exact behaviour of the ``os.environ.get`` calls it replaces (the ``.env`` is
loaded by docker-compose / the shell in deployment, never by the app). This is a
deliberate difference from ``monitoring.DiscordSettings`` (which does read
``.env``); matching ``os.environ`` keeps token-presence tests deterministic.

NOT here on purpose: ``UNIVERSE_FINMIND`` / ``STRATEGY_PRESET`` — those are an
intentional env *side-channel* the CLI uses to pass state into the zipline
``run_algorithm`` subprocess, not user-facing settings.
"""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Env-driven runtime settings (read from real environment variables)."""

    model_config = SettingsConfigDict(extra="ignore")

    # --- data-source credentials (None = not configured; validated at point of use) ---
    finmind_token: str | None = None
    finlab_api_token: str | None = None

    # --- TimescaleDB / Postgres telemetry store ---
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "quant_trading"
    postgres_user: str = "quant"
    postgres_password: str = "change_me_in_production"

    # --- paths ---
    # None → the caller's own default (e.g. research.runs_store.DEFAULT_RUNS_PATH).
    backtest_runs_path: Path | None = None


def get_settings() -> Settings:
    """Fresh ``Settings`` read from the current environment (+ ``.env``)."""
    return Settings()
