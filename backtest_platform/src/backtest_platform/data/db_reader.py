"""Telemetry reader (8.H.8) — the read side of the paper/live DB telemetry.

Counterpart to :mod:`data.db_writer`: ``SELECT`` the daemon-produced telemetry
(equity snapshots, open positions) so the Monitor zone can project *real* data
instead of ``pending`` stubs. Read-only; reuses db_writer's ``DBConfig`` +
``_connection``. The default reader hits TimescaleDB; the API injects it so tests
substitute a fake, and endpoints fall back to a typed-empty envelope when no DB /
telemetry exists yet (graceful degradation — never fabricated data).
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

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

    def fleet_summary(self, *, mode: str = "paper") -> list[dict[str, Any]]:
        """Latest equity snapshot per strategy = the live fleet board (8.H.8).

        ``DISTINCT ON (strategy_id) … ORDER BY strategy_id, snapshot_time DESC``
        gives each strategy's most-recent row — the running fleet, telemetry-driven
        (no strategy registry import needed)."""
        sql = (
            "SELECT DISTINCT ON (strategy_id) strategy_id, equity, cash, open_positions, "
            "portfolio_heat, snapshot_time FROM equity_snapshots WHERE mode = %s "
            "ORDER BY strategy_id, snapshot_time DESC"
        )
        with _connection(self._cfg) as conn, conn.cursor() as cur:
            cur.execute(sql, [mode])
            rows = cur.fetchall()
        return [
            {
                "strategy_id": r[0],
                "equity": float(r[1]),
                "cash": float(r[2]),
                "open_positions": int(r[3]),
                "portfolio_heat": float(r[4]) if r[4] is not None else None,
                "last_update": r[5].isoformat(),
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


# =========================================================================== #
# Broker-state restore — rehydrate a PaperBroker's book across daily restarts. #
#
# The after-close scheduler starts a fresh ``PaperBroker`` per CLI process, so
# without this the portfolio risk gates (EX-002 single-name / EX-004 heat /
# EX-007 max holdings) run from an empty book every session — the cross-day
# twin of a known review defect, and dishonest Paper-Watch OOS. This reads the
# daemon's own telemetry back into a seedable state.
#
# Data-source choice (schema-driven — the honest source per column):
#   * cash      — latest ``equity_snapshots.cash`` for the strategy (mode=paper).
#                 That column is written straight from the broker's
#                 ``portfolio_snapshot()['cash']`` at each session close, so it is
#                 the exact, per-strategy cash — the most honest source available.
#   * positions — folded from the persisted *fills* (``orders`` rows, the fill
#                 log the sink writes), NOT the ``positions`` table: the paper/live
#                 flow never writes ``positions`` (only tests call
#                 ``upsert_positions``), and ``equity_snapshots.open_positions`` is
#                 a count only — too coarse for EX-002 / EX-004 which need per-name
#                 qty + cost basis. Folding the fill log mirrors PaperBroker's own
#                 weighted-average book-keeping, so the reconstruction is exact.
#
# LIMITATION (documented, not hidden): ``orders`` has no strategy_id column, so
# fills are folded portfolio-wide. Today only ``inst_flow`` is wired for paper
# (``after_close.build_session_runner`` rejects any other), so portfolio == the
# strategy and the reconstruction is exact. Wiring a second paper strategy first
# needs a strategy discriminator on ``orders`` (a write-side migration).
# =========================================================================== #
@dataclass(frozen=True, slots=True)
class PositionState:
    """A restored holding: net quantity + weighted-average cost basis (per share)."""

    qty: int
    cost_basis: float


@dataclass(frozen=True, slots=True)
class BrokerState:
    """A restorable broker book — the seed for :meth:`PaperBroker.from_seed`."""

    cash: float
    positions: dict[str, PositionState] = field(default_factory=dict)


#: DB side vocabulary (``_SIDE_DB`` writes 'Buy'/'Sell') → normalized buy/sell.
_BUY_SIDES = frozenset({"buy", "add"})
_SELL_SIDES = frozenset({"sell", "reduce", "exit", "stoploss", "takeprofit"})


def reconstruct_positions(
    fills: Iterable[Mapping[str, Any]],
) -> dict[str, PositionState]:
    """Fold chronologically-ordered fills into net open holdings.

    Mirrors ``PaperBroker._apply_buy`` / ``_apply_sell``: a buy weighted-averages
    the cost basis on price only; a sell reduces quantity and leaves the basis
    unchanged, dropping the name once flat. ``fills`` must be oldest-first. Each
    fill is a mapping with ``stock_id`` / ``side`` (case-insensitive, 'Buy'/'Sell'
    from the DB) / ``quantity`` / ``price``.
    """
    book: dict[str, PositionState] = {}
    for fill in fills:
        sid = str(fill["stock_id"])
        side = str(fill["side"]).strip().lower()
        qty = int(fill["quantity"])
        price = float(fill["price"])
        held = book.get(sid)
        if side in _BUY_SIDES:
            book[sid] = _fold_buy(held, qty, price)
        elif side in _SELL_SIDES:
            new = _fold_sell(held, qty)
            if new is None:
                book.pop(sid, None)
            else:
                book[sid] = new
        else:  # never guess — an unknown side must surface, not be swallowed
            raise ValueError(f"unknown fill side {fill['side']!r} for {sid}")
    return book


def _fold_buy(held: PositionState | None, qty: int, price: float) -> PositionState:
    if held is None:
        return PositionState(qty=qty, cost_basis=price)
    new_qty = held.qty + qty
    new_basis = (held.cost_basis * held.qty + price * qty) / new_qty
    return PositionState(qty=new_qty, cost_basis=new_basis)


def _fold_sell(held: PositionState | None, qty: int) -> PositionState | None:
    remaining = (held.qty if held else 0) - qty
    if remaining <= 0:
        return None  # fully closed (or oversold in the log) → drop the name
    assert held is not None
    return PositionState(qty=remaining, cost_basis=held.cost_basis)


_LATEST_CASH_SQL = (
    "SELECT cash FROM equity_snapshots WHERE strategy_id = %s AND mode = %s "
    "ORDER BY snapshot_time DESC LIMIT 1"
)
_PAPER_FILLS_SQL = (
    "SELECT stock_id, side, quantity, limit_price FROM orders "
    "WHERE broker = %s AND status = 'filled' ORDER BY created_at ASC"
)


def load_broker_state(
    strategy: str,
    *,
    mode: str = "paper",
    broker: str = "paper",
    cfg: DBConfig | None = None,
) -> BrokerState | None:
    """Reconstruct ``strategy``'s last-persisted broker book from telemetry.

    Returns a :class:`BrokerState` (cash + folded holdings) to seed a
    ``PaperBroker`` on the next session, or ``None`` when no equity snapshot
    exists yet (first session — nothing to restore). A DB failure **propagates**:
    a restore path must never silently hand back an empty book, which would make
    the Paper-Watch OOS dishonest (fail loud > fake-empty).
    """
    cfg = cfg or DBConfig.from_env()
    with _connection(cfg) as conn, conn.cursor() as cur:
        cur.execute(_LATEST_CASH_SQL, [strategy, mode])
        cash_row = cur.fetchone()
        if cash_row is None:
            return None  # first session for this strategy — nothing persisted yet
        cur.execute(_PAPER_FILLS_SQL, [broker])
        fill_rows = cur.fetchall()

    fills = [
        {"stock_id": r[0], "side": r[1], "quantity": r[2], "price": r[3]}
        for r in fill_rows
        if r[3] is not None  # a filled paper order always carries its fill price
    ]
    positions = reconstruct_positions(fills)
    logger.info(
        "load_broker_state {}: restored cash={} with {} open positions",
        strategy, float(cash_row[0]), len(positions),
    )
    return BrokerState(cash=float(cash_row[0]), positions=positions)
