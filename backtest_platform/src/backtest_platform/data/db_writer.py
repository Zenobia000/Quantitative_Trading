"""Idempotent upsert of ETL bundles into TimescaleDB.

Uses raw psycopg2 with ``ON CONFLICT (stock_id, trade_date) DO UPDATE`` because:
  * pandas ``to_sql`` has no native upsert
  * SQLAlchemy 2.x upsert is verbose and adds compile-time overhead
  * TimescaleDB hypertables play well with vanilla INSERTs

Running the same ETL twice produces the same DB state — required for
back-fill and re-runs after upstream schema changes.
"""
from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import pandas as pd
from loguru import logger

from backtest_platform.config.settings import get_settings, require_postgres
from backtest_platform.data.schemas import ETLBundle


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
    password: str = "change_me_in_production"

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


# ---------------------------------------------------------------------------
# runs main table upsert — 8.G.1 (Run single-source-of-truth)
# ---------------------------------------------------------------------------
# Column order mirrors init.sql `runs` DDL. run_id is the deterministic 12-char
# RunConfig hash (PK); created_at defaults in the DB. JSONB columns carry the
# run's lineage/result payloads.
_RUNS_COLS = (
    "run_id",
    "hypothesis",
    "strategy",
    "engine",
    "stocks",
    "is_start",
    "is_end",
    "git_sha",
    "bundle_ref",
    "cost_assumptions",
    "params",
    "metrics",
    "gate_status",
    "gate_summary",
    "status",
    "trials_count",
)
# Immutable on conflict — identity + creation stamp never change on a re-run.
_RUNS_IMMUTABLE_COLS = ("run_id", "created_at")
# JSONB columns — serialized to json text (PostgreSQL text→jsonb assignment cast).
_RUNS_JSON_COLS = ("stocks", "cost_assumptions", "params", "metrics")


def upsert_runs(rows: list[dict[str, Any]], cfg: DBConfig | None = None) -> int:
    """Upsert run records into the `runs` main table (ON CONFLICT run_id DO UPDATE).

    A re-run of the same RunConfig (same deterministic run_id) updates the
    mutable result columns (status / metrics / trials_count / ...) while keeping
    run_id and created_at intact. JSONB columns accept dict/list and are
    json-serialized here. Empty list returns 0 without opening a connection.
    """
    if not rows:
        return 0

    cfg = cfg or DBConfig.from_env()
    from psycopg2.extras import execute_values  # type: ignore[import-not-found]

    update_cols = [c for c in _RUNS_COLS if c not in _RUNS_IMMUTABLE_COLS]
    set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
    sql = (
        f"INSERT INTO runs ({', '.join(_RUNS_COLS)}) VALUES %s "
        f"ON CONFLICT (run_id) DO UPDATE SET {set_clause}"
    )

    tuples = [
        tuple(_serialize_cell(col, row.get(col), _RUNS_JSON_COLS) for col in _RUNS_COLS)
        for row in rows
    ]

    with _connection(cfg) as conn, conn.cursor() as cur:
        execute_values(cur, sql, tuples, page_size=500)
    logger.info("upsert_runs wrote {} rows", len(rows))
    return len(rows)


# ---------------------------------------------------------------------------
# paper/live trade log writers — signals / fills / equity (7.A.2, ADR-038)
#
# These tables exist in init.sql; the writers persist a paper (or live) run's
# output. `signals` is an append-only event log (DB auto-gens the id, so a
# plain INSERT is correct); `equity_snapshots` upserts on its time/strategy/run
# PK. A fill has its OWN table (`fills`) — it is the single execution store
# (ADR-038); there is no separate `orders` table until a real broker order
# lifecycle lands at M5.
# ---------------------------------------------------------------------------
def _execute_write(
    table: str,
    cols: tuple[str, ...],
    rows: list[dict[str, Any]],
    *,
    conflict_cols: tuple[str, ...] | None = None,
    json_cols: tuple[str, ...] = (),
    cfg: DBConfig | None = None,
) -> int:
    """Shared row-dict writer: INSERT (optionally ON CONFLICT … DO UPDATE).

    Missing keys default to SQL NULL; ``json_cols`` are json-serialized for JSONB
    assignment. Empty ``rows`` returns 0 without opening a connection.
    """
    if not rows:
        return 0

    cfg = cfg or DBConfig.from_env()
    from psycopg2.extras import execute_values  # type: ignore[import-not-found]

    sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES %s"
    if conflict_cols:
        update_cols = [c for c in cols if c not in conflict_cols]
        set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
        sql += f" ON CONFLICT ({', '.join(conflict_cols)}) DO UPDATE SET {set_clause}"

    tuples = [
        tuple(_serialize_cell(c, row.get(c), json_cols) for c in cols) for row in rows
    ]
    with _connection(cfg) as conn, conn.cursor() as cur:
        execute_values(cur, sql, tuples, page_size=500)
    logger.info("wrote {} rows to {}", len(rows), table)
    return len(rows)


_SIGNALS_COLS = (
    "signal_time", "strategy_id", "run_id", "stock_id", "action",
    "priority", "reason_json", "submitted", "submitted_at",
)
_EQUITY_COLS = (
    "snapshot_time", "strategy_id", "mode", "run_id", "equity", "cash",
    "positions_value", "open_positions", "portfolio_heat", "drawdown",
    "daily_return", "cumulative_return",
)
_EQUITY_PK = ("snapshot_time", "strategy_id", "run_id")


def upsert_signals(rows: list[dict[str, Any]], cfg: DBConfig | None = None) -> int:
    """Append signal events to `signals` (signal_id auto-gen; reason_json is JSONB)."""
    return _execute_write("signals", _SIGNALS_COLS, rows, json_cols=("reason_json",), cfg=cfg)


def upsert_equity_snapshots(rows: list[dict[str, Any]], cfg: DBConfig | None = None) -> int:
    """Upsert equity snapshots on PK(snapshot_time, strategy_id, run_id)."""
    return _execute_write("equity_snapshots", _EQUITY_COLS, rows, conflict_cols=_EQUITY_PK, cfg=cfg)


# fills = the single execution store (ADR-038). order_id is NOT NULL and stays as
# a client-minted (uuid4) logical event id linking a fill to the order intent that
# produced it — there is no separate `orders` table until a real broker order
# lifecycle lands at M5. strategy_id (NOT NULL) carries per-sleeve P&L attribution.
_FILLS_COLS = (
    "fill_time", "order_id", "signal_id", "strategy_id", "stock_id", "side",
    "fill_price", "fill_quantity", "commission", "tax", "slippage_bps",
    "broker", "broker_trade_id",
)


def upsert_fills(rows: list[dict[str, Any]], cfg: DBConfig | None = None) -> int:
    """Persist broker fills into `fills` — the single execution store (ADR-038).

    A fill IS the execution record: one append-only INSERT into `fills`, no
    separate `orders` table (orders returns at M5 with a live broker's order
    lifecycle). ``order_id`` is minted client-side (uuid4) when absent and kept
    as a logical event id linking the fill to the order intent that produced it
    (the column is NOT NULL). Fill dict keys: stock_id / side / qty / price /
    filled_at / strategy_id (+ optional commission / tax / slippage_bps /
    signal_id / broker_trade_id / order_id; broker defaults to 'paper')."""
    if not rows:
        return 0

    import uuid

    fills = [
        {
            "fill_time": f.get("filled_at"),
            "order_id": f.get("order_id") or str(uuid.uuid4()),
            "signal_id": f.get("signal_id"),
            "strategy_id": f.get("strategy_id"),
            "stock_id": f.get("stock_id"),
            "side": f.get("side"),
            "fill_price": f.get("price"),
            "fill_quantity": f.get("qty"),
            "commission": f.get("commission"),
            "tax": f.get("tax"),
            "slippage_bps": f.get("slippage_bps"),
            "broker": f.get("broker", "paper"),
            "broker_trade_id": f.get("broker_trade_id"),
        }
        for f in rows
    ]
    return _execute_write("fills", _FILLS_COLS, fills, cfg=cfg)
