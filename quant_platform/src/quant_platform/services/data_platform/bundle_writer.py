"""Idempotent upsert of ETL bundles into TimescaleDB — data-platform service.

Uses raw psycopg2 with ``ON CONFLICT (stock_id, trade_date) DO UPDATE`` because:
  * pandas ``to_sql`` has no native upsert
  * SQLAlchemy 2.x upsert is verbose and adds compile-time overhead
  * TimescaleDB hypertables play well with vanilla INSERTs

Running the same ETL twice produces the same DB state — required for
back-fill and re-runs after upstream schema changes.

Extracted from ``data.db_writer`` in W5.2d and parked under
``services.data_platform`` so the bundle writer lives with the rest of the
data-platform service cluster. It builds on the connection kernel in
``data.db_kernel``; ``data.db_writer`` re-exports these symbols so existing
``from data.db_writer import upsert_bundle`` consumers stay untouched.
"""
from __future__ import annotations

import pandas as pd
from loguru import logger

from quant_platform.packages.infrastructure.db_kernel import DBConfig, _connection
from quant_platform.services.data_platform.schemas import ETLBundle

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
