"""Telemetry reader (8.H.8) — the read side of the paper/live DB telemetry.

Counterpart to :mod:`data.db_writer`: ``SELECT`` the daemon-produced telemetry
(equity snapshots, open positions) so the Monitor zone can project *real* data
instead of ``pending`` stubs. Read-only; reuses db_writer's ``DBConfig`` +
``_connection``. The default reader hits TimescaleDB; the API injects it so tests
substitute a fake, and endpoints fall back to a typed-empty envelope when no DB /
telemetry exists yet (graceful degradation — never fabricated data).
"""
from __future__ import annotations

from typing import Any

from backtest_platform.data.db_writer import DBConfig, _connection


class TelemetryReader:
    """Reads paper/live telemetry from TimescaleDB (read-only)."""

    def __init__(self, cfg: DBConfig | None = None) -> None:
        self._cfg = cfg or DBConfig.from_env()

    def equity_series(self, *, strategy_id: str | None = None, mode: str = "paper") -> list[dict[str, Any]]:
        """Equity curve points (time-ordered) for a mode (+ optional strategy)."""
        sql = ["SELECT snapshot_time, equity, drawdown FROM equity_snapshots WHERE mode = %s"]
        params: list[Any] = [mode]
        if strategy_id:
            sql.append("AND strategy_id = %s")
            params.append(strategy_id)
        sql.append("ORDER BY snapshot_time")
        with _connection(self._cfg) as conn, conn.cursor() as cur:
            cur.execute(" ".join(sql), params)
            rows = cur.fetchall()
        return [
            {
                "t": r[0].isoformat(),
                "equity": float(r[1]),
                "drawdown": float(r[2]) if r[2] is not None else None,
            }
            for r in rows
        ]

    def open_positions(self, *, strategy_id: str | None = None) -> list[dict[str, Any]]:
        """Currently-open positions (``closed_at IS NULL``)."""
        sql = [
            "SELECT stock_id, quantity, entry_price, stop_loss, opened_at, strategy_id "
            "FROM positions WHERE closed_at IS NULL"
        ]
        params: list[Any] = []
        if strategy_id:
            sql.append("AND strategy_id = %s")
            params.append(strategy_id)
        sql.append("ORDER BY opened_at")
        with _connection(self._cfg) as conn, conn.cursor() as cur:
            cur.execute(" ".join(sql), params)
            rows = cur.fetchall()
        return [
            {
                "stock_id": r[0],
                "quantity": int(r[1]),
                "entry_price": float(r[2]),
                "stop_loss": float(r[3]) if r[3] is not None else None,
                "opened_at": r[4].isoformat(),
                "strategy_id": r[5],
            }
            for r in rows
        ]

    def recent_signals(self, *, limit: int = 50, strategy_id: str | None = None) -> list[dict[str, Any]]:
        """Most-recent signals (newest first)."""
        sql = ["SELECT signal_time, strategy_id, stock_id, action, priority, submitted FROM signals"]
        params: list[Any] = []
        if strategy_id:
            sql.append("WHERE strategy_id = %s")
            params.append(strategy_id)
        sql.append("ORDER BY signal_time DESC LIMIT %s")
        params.append(limit)
        with _connection(self._cfg) as conn, conn.cursor() as cur:
            cur.execute(" ".join(sql), params)
            rows = cur.fetchall()
        return [
            {
                "signal_time": r[0].isoformat(),
                "strategy_id": r[1],
                "stock_id": r[2],
                "action": r[3],
                "priority": int(r[4]),
                "submitted": bool(r[5]),
            }
            for r in rows
        ]

    def recent_fills(self, *, limit: int = 50) -> list[dict[str, Any]]:
        """Most-recent order executions (newest first). The paper daemon records
        fills as ``orders`` rows (7.A.2), so this reads ``orders``."""
        sql = [
            "SELECT created_at, stock_id, side, quantity, limit_price, status FROM orders"
        ]
        sql.append("ORDER BY created_at DESC LIMIT %s")
        with _connection(self._cfg) as conn, conn.cursor() as cur:
            cur.execute(" ".join(sql), [limit])
            rows = cur.fetchall()
        return [
            {
                "created_at": r[0].isoformat(),
                "stock_id": r[1],
                "side": r[2],
                "quantity": int(r[3]),
                "price": float(r[4]) if r[4] is not None else None,
                "status": r[5],
            }
            for r in rows
        ]
