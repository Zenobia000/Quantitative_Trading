"""Central runtime settings — one typed place for env-driven config (ADR-027 Stage 2).

Before this, credentials / DB connection / paths were read via scattered
``os.environ.get(...)`` across ``data/``, ``api/``, ``orchestration/`` (each with its own
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

#: Legacy placeholder password. Never valid for a real connection —
#: ``require_postgres`` refuses it (審查缺陷 #19).
INSECURE_POSTGRES_PASSWORD = "change_me_in_production"


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
    postgres_password: str = "quant_local_dev_password"

    # --- paths ---
    # None → the caller's own default (e.g. research.runs_store.DEFAULT_RUNS_PATH).
    backtest_runs_path: Path | None = None


def get_settings() -> Settings:
    """Fresh ``Settings`` read from the current environment (+ ``.env``)."""
    return Settings()


def require_postgres(password: str | None = None) -> None:
    """Refuse to connect to Postgres with the shipped placeholder password (審查缺陷 #19).

    ``password`` defaults to the env-configured ``postgres_password``; the DB
    connection choke point passes the actual DSN password. Raises ``RuntimeError``
    with a fix hint when it is still ``change_me_in_production``.

    Called at point-of-use (the ``data.db_writer._connection`` choke point), NEVER at
    import — so CI / offline runs that never open a DB connection stay green while any
    real connection attempt with an un-rotated password fails loudly.
    """
    if password is None:
        password = get_settings().postgres_password
    if password == INSECURE_POSTGRES_PASSWORD:
        raise RuntimeError(
            "refusing to connect: POSTGRES_PASSWORD is still the shipped default "
            f"{INSECURE_POSTGRES_PASSWORD!r}. Set a real POSTGRES_PASSWORD "
            "(env / .env / secret manager) before opening a telemetry DB connection."
        )
