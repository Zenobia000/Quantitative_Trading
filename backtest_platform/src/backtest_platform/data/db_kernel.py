"""DB connection kernel — the shared psycopg2 plumbing for every writer/reader.

Extracted from ``data.db_writer`` in W5.2c so the connection primitives live in
one dependency-light module that the bundle/runs/telemetry writers all build on.

Layering rule (import-linter contract 1): this kernel may import ONLY
``config.settings`` (require_postgres/get_settings) plus stdlib/third-party. It
must never import a service package or ``db_writer`` — doing so would create a
cycle (db_writer → db_kernel → …) and could drag services into the research
import chain that lazy-imports the runs writer.
"""
from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from backtest_platform.config.settings import get_settings, require_postgres


def _serialize_cell(col: str, value: Any, json_cols: tuple[str, ...]) -> Any:
    """JSONB columns → json text (``ensure_ascii=False`` so CJK stays readable);
    every other column passes through unchanged. Single source for the row-tuple
    serialization shared by ``upsert_runs`` and ``_execute_write``."""
    if col in json_cols and value is not None:
        return json.dumps(value, ensure_ascii=False, default=str)
    return value


@dataclass(frozen=True, slots=True)
class DBConfig:
    host: str = "localhost"
    port: int = 5432
    database: str = "quant_trading"
    user: str = "quant"
    password: str = "quant_local_dev_password"

    @classmethod
    def from_env(cls) -> DBConfig:
        s = get_settings()
        return cls(
            host=s.postgres_host,
            port=s.postgres_port,
            database=s.postgres_db,
            user=s.postgres_user,
            password=s.postgres_password,
        )

    def dsn(self) -> str:
        return (
            f"host={self.host} port={self.port} dbname={self.database} "
            f"user={self.user} password={self.password}"
        )


@contextmanager
def _connection(cfg: DBConfig) -> Iterator[Any]:
    """Lazy psycopg2 import keeps the module loadable in test envs without the driver.

    The single DB choke point for both writer and reader: guard the placeholder
    password here (審查缺陷 #19) so it fires at connection time only — never at import,
    keeping DB-less CI green — before any socket is opened.
    """
    require_postgres(cfg.password)
    import psycopg2  # type: ignore[import-not-found]

    conn = psycopg2.connect(cfg.dsn())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
