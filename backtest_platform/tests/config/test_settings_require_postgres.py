"""config.settings.require_postgres — refuse the shipped default DB password.

審查缺陷 #19: ``POSTGRES_PASSWORD`` shipped as ``change_me_in_production`` with no
guard. ``require_postgres`` fails loudly when the placeholder survives to a real
connection attempt — validated at point-of-use only, never at import (CI without a
DB must stay green).
"""
from __future__ import annotations

import pytest

from backtest_platform.config.settings import (
    INSECURE_POSTGRES_PASSWORD,
    require_postgres,
)


def test_require_postgres_rejects_default_password(monkeypatch) -> None:
    monkeypatch.setenv("POSTGRES_PASSWORD", INSECURE_POSTGRES_PASSWORD)
    with pytest.raises(RuntimeError, match="POSTGRES_PASSWORD"):
        require_postgres()


def test_require_postgres_accepts_rotated_password(monkeypatch) -> None:
    monkeypatch.setenv("POSTGRES_PASSWORD", "s3cret-rotated")
    require_postgres()  # must not raise


def test_require_postgres_checks_explicit_password_argument() -> None:
    # The connection choke point passes the actual DSN password, not just env.
    with pytest.raises(RuntimeError):
        require_postgres(INSECURE_POSTGRES_PASSWORD)
    require_postgres("real-password")  # must not raise
