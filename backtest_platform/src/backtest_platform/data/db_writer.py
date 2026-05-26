"""Idempotent upsert of ETL bundles into TimescaleDB.

Uses raw psycopg2 with ``ON CONFLICT (stock_id, trade_date) DO UPDATE`` because:
  * pandas ``to_sql`` has no native upsert
  * SQLAlchemy 2.x upsert is verbose and adds compile-time overhead
  * TimescaleDB hypertables play well with vanilla INSERTs

Running the same ETL twice produces the same DB state — required for
back-fill and re-runs after upstream schema changes.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

import pandas as pd
from loguru import logger

from backtest_platform.data.schemas import ETLBundle


@dataclass(frozen=True, slots=True)
class DBConfig:
    host: str = "localhost"
    port: int = 5432
    database: str = "quant_trading"
    user: str = "quant"
    password: str = "change_me_in_production"

    @classmethod
    def from_env(cls) -> DBConfig:
        return cls(
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            database=os.environ.get("POSTGRES_DB", "quant_trading"),
            user=os.environ.get("POSTGRES_USER", "quant"),
            password=os.environ.get("POSTGRES_PASSWORD", "change_me_in_production"),
        )

    def dsn(self) -> str:
        return (
            f"host={self.host} port={self.port} dbname={self.database} "
            f"user={self.user} password={self.password}"
        )


@contextmanager
def _connection(cfg: DBConfig) -> Iterator[Any]:
    """Lazy psycopg2 import keeps the module loadable in test envs without the driver."""
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


_DAILY_BARS_COLS = (
    "stock_id",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "adj_factor",
)
_INSTITUTIONAL_COLS = ("stock_id", "trade_date", "foreign_buy", "trust_buy", "dealer_buy")
_BROKER_CHIPS_COLS = (
    "stock_id",
    "trade_date",
    "top_broker_buy",
    "key_broker_buy",
    "gov_broker_buy",
    "geo_broker_buy",
    "day_trade_volume",
    "margin_offset_volume",
)


def upsert_bundle(bundle: ETLBundle, cfg: DBConfig | None = None) -> dict[str, int]:
    """Upsert daily_bars / institutional_flows / broker_chips. Returns row counts."""
    cfg = cfg or DBConfig.from_env()
    counts: dict[str, int] = {}
    with _connection(cfg) as conn, conn.cursor() as cur:
        counts["daily_bars"] = _upsert_frame(
            cur, "daily_bars", _DAILY_BARS_COLS, bundle.daily_bars
        )
        counts["institutional_flows"] = _upsert_frame(
            cur, "institutional_flows", _INSTITUTIONAL_COLS, bundle.institutional
        )
        counts["broker_chips"] = _upsert_frame(
            cur, "broker_chips", _BROKER_CHIPS_COLS, bundle.broker_chips
        )
    logger.info("upsert complete stock={} counts={}", bundle.stock_id, counts)
    return counts


def _upsert_frame(cur, table: str, cols: tuple[str, ...], df: pd.DataFrame) -> int:
    """Build ON CONFLICT upsert SQL and execute_values batch insert."""
    if df.empty:
        return 0

    from psycopg2.extras import execute_values  # type: ignore[import-not-found]

    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"frame for {table} missing columns: {missing}")

    update_cols = [c for c in cols if c not in ("stock_id", "trade_date")]
    set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
    sql = (
        f"INSERT INTO {table} ({', '.join(cols)}) VALUES %s "
        f"ON CONFLICT (stock_id, trade_date) DO UPDATE SET {set_clause}"
    )
    # tuples in column order
    rows = [tuple(row[c] for c in cols) for row in df.to_dict("records")]
    execute_values(cur, sql, rows, page_size=500)
    return len(rows)
