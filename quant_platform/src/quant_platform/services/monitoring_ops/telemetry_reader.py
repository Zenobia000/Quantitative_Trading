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

from quant_platform.packages.infrastructure.db_kernel import DBConfig, _connection


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

    def runs_board(self, *, limit: int = 50) -> list[dict[str, Any]]:
        """Latest research runs for the run board (A2): lifecycle status
        (running|done|failed, mirrored by run_persist / batch) + 審判庭 verdict.
        Nullable verdict/metrics stay None for in-flight runs — the frontend
        renders them as —, never fabricated."""
        sql = (
            "SELECT run_id, strategy, engine, stocks, is_start, is_end, status, "
            "gate_status, gate_summary, metrics, created_at FROM runs "
            "ORDER BY created_at DESC LIMIT %s"
        )
        with _connection(self._cfg) as conn, conn.cursor() as cur:
            cur.execute(sql, [limit])
            rows = cur.fetchall()
        return [
            {
                "run_id": r[0],
                "strategy": r[1],
                "engine": r[2],
                "stocks": r[3],
                "is_start": r[4].isoformat() if r[4] is not None else None,
                "is_end": r[5].isoformat() if r[5] is not None else None,
                "status": r[6],
                "gate_status": r[7],
                "gate_summary": r[8],
                "metrics": r[9],
                "created_at": r[10].isoformat() if r[10] is not None else None,
            }
            for r in rows
        ]

    def open_positions(self, *, strategy_id: str | None = None) -> list[dict[str, Any]]:
        """Currently-open positions, folded from the `fills` execution store (ADR-038).

        The `positions` table was dropped: the paper/live flow never wrote it, so
        this endpoint (GET /monitor/positions) was permanently empty. It is now a
        chronological fold over `fills` per (strategy_id, stock_id) — the same
        weighted-average book-keeping :func:`reconstruct_positions` performs — so
        the page shows the real book. Response row shape (FE ``PositionRow``):
        stock_id/quantity/entry_price/stop_loss(None — no per-name stop in the
        fill log)/opened_at/strategy_id.
        """
        sql = [
            "SELECT strategy_id, stock_id, side, fill_quantity, fill_price, fill_time "
            "FROM fills"
        ]
        params: list[Any] = []
        if strategy_id:
            sql.append("WHERE strategy_id = %s")
            params.append(strategy_id)
        sql.append("ORDER BY fill_time ASC")
        with _connection(self._cfg) as conn, conn.cursor() as cur:
            cur.execute(" ".join(sql), params)
            rows = cur.fetchall()
        return _fold_open_positions(rows)

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
        """Most-recent executions (newest first) from the `fills` store (ADR-038).

        `fills` is the single execution store; it has no ``status`` column (a
        persisted fill is by definition filled), so the reader emits a constant
        ``'filled'`` to keep the Monitor ``/fills`` row shape (FE ``FillRow``:
        created_at/stock_id/side/quantity/price/status) unchanged."""
        sql = (
            "SELECT fill_time, stock_id, side, fill_quantity, fill_price FROM fills "
            "ORDER BY fill_time DESC LIMIT %s"
        )
        with _connection(self._cfg) as conn, conn.cursor() as cur:
            cur.execute(sql, [limit])
            rows = cur.fetchall()
        return [
            {
                "created_at": r[0].isoformat(),
                "stock_id": r[1],
                "side": r[2],
                "quantity": int(r[3]),
                "price": float(r[4]) if r[4] is not None else None,
                "status": "filled",
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
#   * positions — folded from the persisted ``fills`` (the single execution store,
#                 ADR-038), NOT a ``positions`` table (dropped): the paper/live flow
#                 never wrote ``positions``, and ``equity_snapshots.open_positions``
#                 is a count only — too coarse for EX-002 / EX-004 which need
#                 per-name qty + cost basis. Folding the fill log mirrors
#                 PaperBroker's own weighted-average book-keeping, so the
#                 reconstruction is exact.
#
# ``fills`` now carries a ``strategy_id`` column (ADR-038), so the fold is scoped
# to the requested strategy — the old portfolio-wide-only limitation (``orders``
# had no strategy discriminator) is resolved, unblocking a second paper strategy.
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


def _fold_open_positions(
    fill_rows: Iterable[tuple[Any, ...]],
) -> list[dict[str, Any]]:
    """Fold chronological fill rows into currently-open positions for the Monitor
    ``/positions`` page (ADR-038 — folds ``fills``, not the dropped ``positions``).

    ``fill_rows`` are ``(strategy_id, stock_id, side, fill_quantity, fill_price,
    fill_time)`` tuples, oldest-first. The book is keyed per (strategy_id, stock_id)
    and folded with the same averaging as :func:`reconstruct_positions` (buy →
    weighted-average cost, sell → reduce qty at unchanged basis, drop when flat).
    ``opened_at`` tracks when the *current* open lot began — set when the name goes
    from flat to open, reset when it goes flat again. ``stop_loss`` is None: the
    fill log carries no per-name stop. Rows are returned oldest-open-first.
    """
    book: dict[tuple[str, str], PositionState] = {}
    opened_at: dict[tuple[str, str], Any] = {}
    for strat, stock, side, qty, price, ftime in fill_rows:
        key = (str(strat), str(stock))
        norm = str(side).strip().lower()
        held = book.get(key)
        if norm in _BUY_SIDES:
            if held is None:  # flat → open: this fill starts the current lot
                opened_at[key] = ftime
            book[key] = _fold_buy(held, int(qty), float(price))
        elif norm in _SELL_SIDES:
            new = _fold_sell(held, int(qty))
            if new is None:
                book.pop(key, None)
                opened_at.pop(key, None)
            else:
                book[key] = new
        else:  # never guess — an unknown side must surface, not be swallowed
            raise ValueError(f"unknown fill side {side!r} for {stock}")
    rows = [
        {
            "stock_id": stock,
            "quantity": pos.qty,
            "entry_price": pos.cost_basis,
            "stop_loss": None,
            "opened_at": opened_at[(strat, stock)].isoformat(),
            "strategy_id": strat,
        }
        for (strat, stock), pos in book.items()
    ]
    return sorted(rows, key=lambda r: r["opened_at"])


_LATEST_CASH_SQL = (
    "SELECT cash FROM equity_snapshots WHERE strategy_id = %s AND mode = %s "
    "ORDER BY snapshot_time DESC LIMIT 1"
)
# Positions restore folds the `fills` execution store (ADR-038), scoped to the
# strategy now that fills carries strategy_id (replaces the old orders-by-broker
# query which had no strategy discriminator).
_PAPER_FILLS_SQL = (
    "SELECT stock_id, side, fill_quantity, fill_price FROM fills "
    "WHERE broker = %s AND strategy_id = %s ORDER BY fill_time ASC"
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
        cur.execute(_PAPER_FILLS_SQL, [broker, strategy])
        fill_rows = cur.fetchall()

    fills = [
        {"stock_id": r[0], "side": r[1], "quantity": r[2], "price": r[3]}
        for r in fill_rows
        if r[3] is not None  # fills.fill_price is NOT NULL, but guard defensively
    ]
    positions = reconstruct_positions(fills)
    logger.info(
        "load_broker_state {}: restored cash={} with {} open positions",
        strategy, float(cash_row[0]), len(positions),
    )
    return BrokerState(cash=float(cash_row[0]), positions=positions)
