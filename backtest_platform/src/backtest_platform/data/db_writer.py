"""Idempotent upsert of ETL bundles into TimescaleDB.

Uses raw psycopg2 with ``ON CONFLICT (stock_id, trade_date) DO UPDATE`` because:
  * pandas ``to_sql`` has no native upsert
  * SQLAlchemy 2.x upsert is verbose and adds compile-time overhead
  * TimescaleDB hypertables play well with vanilla INSERTs

Running the same ETL twice produces the same DB state — required for
back-fill and re-runs after upstream schema changes.
"""
from __future__ import annotations

from typing import Any

import pandas as pd
from loguru import logger

# W5.2c: the connection kernel (DBConfig / _connection / _serialize_cell) moved to
# data.db_kernel; the runs writer (upsert_runs + _RUNS_* column specs) moved to
# data.runs_writer so research can reach it without routing through db_writer.
# Re-exported here (see ``__all__``) so existing `from data.db_writer import
# DBConfig/_connection/upsert_runs/_RUNS_COLS` consumers and tests stay untouched.
# The bundle + telemetry (signals/equity/fills) writers below reuse the
# re-exported kernel symbols.
from backtest_platform.data.db_kernel import DBConfig, _connection, _serialize_cell
from backtest_platform.data.runs_writer import (
    _RUNS_COLS,
    _RUNS_IMMUTABLE_COLS,
    _RUNS_JSON_COLS,
    upsert_runs,
)
from backtest_platform.data.schemas import ETLBundle

# Re-exported kernel/runs symbols kept in the public surface for backward compat.
__all__ = [
    "_RUNS_COLS",
    "_RUNS_IMMUTABLE_COLS",
    "_RUNS_JSON_COLS",
    "DBConfig",
    "_connection",
    "_serialize_cell",
    "upsert_bundle",
    "upsert_equity_snapshots",
    "upsert_fills",
    "upsert_runs",
    "upsert_signals",
]

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
