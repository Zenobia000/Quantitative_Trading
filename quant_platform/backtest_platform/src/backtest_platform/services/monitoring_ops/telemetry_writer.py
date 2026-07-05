"""paper/live trade-log writers — signals / fills / equity (7.A.2, ADR-038).

These tables exist in init.sql; the writers persist a paper (or live) run's
output. ``signals`` is an append-only event log (DB auto-gens the id, so a plain
INSERT is correct); ``equity_snapshots`` upserts on its time/strategy/run PK. A
fill has its OWN table (``fills``) — it is the single execution store (ADR-038);
there is no separate ``orders`` table until a real broker order lifecycle lands
at M5.

Extracted from ``data.db_writer`` in W5.2e and parked under
``services.monitoring_ops`` alongside the rest of the observability/ops cluster
(alert engine, notifier, jobs). It builds on the connection kernel in
``data.db_kernel``; ``data.db_writer`` re-exports these symbols so existing
``from data.db_writer import upsert_signals/upsert_fills/upsert_equity_snapshots``
consumers stay untouched.
"""
from __future__ import annotations

from typing import Any

from loguru import logger

from backtest_platform.data.db_kernel import DBConfig, _connection, _serialize_cell


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
