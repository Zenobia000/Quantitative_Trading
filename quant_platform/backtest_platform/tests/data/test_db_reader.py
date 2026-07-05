"""TDD spec for the broker-state restore reader (paper-position rehydration).

The after-close scheduler starts a fresh ``PaperBroker`` per CLI process, so
cross-day portfolio state (the input to the EX-002 / EX-004 / EX-007 portfolio
risk gates) was previously lost — every session's gates ran from an empty book,
making the Paper-Watch OOS telemetry dishonest. ``load_broker_state`` closes that
gap by reconstructing the last-persisted book from the daemon's own telemetry.

Data-source contract pinned here (schema-driven, see docstring in db_reader):
  * **cash** — the latest ``equity_snapshots.cash`` for the strategy (mode=paper).
    That column is written straight from ``broker.portfolio_snapshot()['cash']``,
    so it is the exact, per-strategy, most-honest cash at last session close.
  * **positions** — folded from the persisted ``fills`` (the single execution
    store, ADR-038) chronologically, mirroring ``PaperBroker`` averaging, scoped
    to the strategy via ``fills.strategy_id``; ``equity_snapshots.open_positions``
    is a count only, too coarse for the per-name portfolio risk gates.

DB access is patched (no live DB); a real-DB round-trip lives behind
``POSTGRES_INTEGRATION`` (skipped by default), mirroring test_db_writer.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from backtest_platform.data.db_reader import (
    BrokerState,
    PositionState,
    load_broker_state,
    reconstruct_positions,
)


# --------------------------------------------------------------------------- #
# reconstruct_positions — pure fill-folding (mirrors PaperBroker averaging)     #
# --------------------------------------------------------------------------- #
def test_reconstruct_single_buy() -> None:
    pos = reconstruct_positions([
        {"stock_id": "2330", "side": "Buy", "quantity": 1000, "price": 100.0},
    ])
    assert pos == {"2330": PositionState(qty=1000, cost_basis=100.0)}


def test_reconstruct_averages_up_cost_basis() -> None:
    pos = reconstruct_positions([
        {"stock_id": "2330", "side": "Buy", "quantity": 1000, "price": 100.0},
        {"stock_id": "2330", "side": "Buy", "quantity": 1000, "price": 110.0},
    ])
    # weighted average of price only: (100*1000 + 110*1000) / 2000 = 105
    assert pos["2330"].qty == 2000
    assert pos["2330"].cost_basis == pytest.approx(105.0)


def test_reconstruct_partial_sell_keeps_basis_drops_when_flat() -> None:
    pos = reconstruct_positions([
        {"stock_id": "2330", "side": "Buy", "quantity": 1000, "price": 100.0},
        {"stock_id": "2330", "side": "Sell", "quantity": 400, "price": 120.0},
        {"stock_id": "2317", "side": "buy", "quantity": 500, "price": 50.0},
        {"stock_id": "2317", "side": "sell", "quantity": 500, "price": 60.0},
    ])
    # 2330: 600 left at unchanged basis; 2317 fully closed → dropped
    assert pos == {"2330": PositionState(qty=600, cost_basis=100.0)}


def test_reconstruct_empty_is_empty() -> None:
    assert reconstruct_positions([]) == {}


# --------------------------------------------------------------------------- #
# open_positions / recent_fills — read the fills store (ADR-038; positions and   #
# orders tables are gone). GET /monitor/positions was permanently empty because  #
# the positions table was never written in prod — folding fills fixes that.      #
# --------------------------------------------------------------------------- #
def _reader_with_rows(rows):
    from backtest_platform.data.db_reader import TelemetryReader

    cur = MagicMock()
    cur.fetchall.return_value = rows
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    return TelemetryReader(cfg=MagicMock()), cur, conn


def test_open_positions_folds_fills_into_position_rows() -> None:
    from datetime import datetime, timezone

    opened = datetime(2026, 1, 2, 1, tzinfo=timezone.utc)
    reader, cur, conn = _reader_with_rows([
        # (strategy_id, stock_id, side, fill_quantity, fill_price, fill_time)
        ("inst_flow", "2330", "Buy", 1000, 100.0, opened),
        ("inst_flow", "2330", "Buy", 1000, 110.0, datetime(2026, 1, 3, 1, tzinfo=timezone.utc)),
        ("inst_flow", "2317", "Buy", 500, 50.0, datetime(2026, 1, 4, 1, tzinfo=timezone.utc)),
        ("inst_flow", "2317", "Sell", 500, 60.0, datetime(2026, 1, 5, 1, tzinfo=timezone.utc)),
    ])
    with patch("backtest_platform.services.monitoring_ops.telemetry_reader._connection") as ctx:
        ctx.return_value.__enter__.return_value = conn
        rows = reader.open_positions()

    # 2317 fully closed → dropped; 2330 nets 2000 @ weighted 105, opened_at = first buy
    assert rows == [{
        "stock_id": "2330", "quantity": 2000, "entry_price": 105.0,
        "stop_loss": None, "opened_at": opened.isoformat(), "strategy_id": "inst_flow",
    }]
    sql = cur.execute.call_args.args[0]
    assert "FROM fills" in sql and "positions" not in sql.lower()


def test_open_positions_scopes_by_strategy_when_given() -> None:
    reader, cur, conn = _reader_with_rows([])
    with patch("backtest_platform.services.monitoring_ops.telemetry_reader._connection") as ctx:
        ctx.return_value.__enter__.return_value = conn
        reader.open_positions(strategy_id="inst_flow")
    sql, params = cur.execute.call_args.args
    assert "strategy_id = %s" in sql
    assert "inst_flow" in params


def test_recent_fills_maps_fills_to_fillrow_shape() -> None:
    from datetime import datetime, timezone

    ft = datetime(2026, 1, 2, 1, tzinfo=timezone.utc)
    reader, cur, conn = _reader_with_rows([
        # (fill_time, stock_id, side, fill_quantity, fill_price)
        (ft, "2330", "Buy", 1000, 542.0),
    ])
    with patch("backtest_platform.services.monitoring_ops.telemetry_reader._connection") as ctx:
        ctx.return_value.__enter__.return_value = conn
        rows = reader.recent_fills(limit=10)

    # fills has no status column → constant 'filled' keeps the FE FillRow shape
    assert rows == [{
        "created_at": ft.isoformat(), "stock_id": "2330", "side": "Buy",
        "quantity": 1000, "price": 542.0, "status": "filled",
    }]
    sql = cur.execute.call_args.args[0]
    assert "FROM fills" in sql and "orders" not in sql.lower()


# --------------------------------------------------------------------------- #
# load_broker_state — DB orchestration (patched connection)                     #
# --------------------------------------------------------------------------- #
def _fake_conn(*, equity_row, fill_rows):
    """A MagicMock conn whose cursor returns equity_row (fetchone) then fills."""
    cur = MagicMock()
    cur.fetchone.return_value = equity_row
    cur.fetchall.return_value = fill_rows
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    return conn, cur


def test_load_broker_state_seeds_cash_and_positions() -> None:
    """(a) with telemetry → BrokerState carries the persisted cash + folded book."""
    conn, _ = _fake_conn(
        equity_row=(850_000.0,),  # equity_snapshots.cash
        fill_rows=[
            ("2330", "Buy", 1000, 100.0),
            ("2330", "Buy", 1000, 110.0),
            ("2317", "Buy", 500, 50.0),
        ],
    )
    with patch("backtest_platform.services.monitoring_ops.telemetry_reader._connection") as ctx:
        ctx.return_value.__enter__.return_value = conn
        state = load_broker_state("inst_flow")

    assert isinstance(state, BrokerState)
    assert state.cash == pytest.approx(850_000.0)
    assert state.positions["2330"] == PositionState(qty=2000, cost_basis=105.0)
    assert state.positions["2317"] == PositionState(qty=500, cost_basis=50.0)


def test_load_broker_state_first_day_returns_none() -> None:
    """(b) no equity snapshot for the strategy → None (first session, nothing to restore)."""
    conn, _ = _fake_conn(equity_row=None, fill_rows=[])
    with patch("backtest_platform.services.monitoring_ops.telemetry_reader._connection") as ctx:
        ctx.return_value.__enter__.return_value = conn
        state = load_broker_state("inst_flow")
    assert state is None


def test_load_broker_state_raises_on_db_error_never_silent_empty() -> None:
    """(c) a DB failure must propagate — never a silent empty book (dishonest OOS)."""
    with patch("backtest_platform.services.monitoring_ops.telemetry_reader._connection") as ctx:
        ctx.side_effect = RuntimeError("connection refused")
        with pytest.raises(RuntimeError, match="connection refused"):
            load_broker_state("inst_flow")


def test_load_broker_state_cash_only_when_no_fills() -> None:
    """A snapshot with no fills → cash restored, empty positions (not None)."""
    conn, _ = _fake_conn(equity_row=(1_000_000.0,), fill_rows=[])
    with patch("backtest_platform.services.monitoring_ops.telemetry_reader._connection") as ctx:
        ctx.return_value.__enter__.return_value = conn
        state = load_broker_state("inst_flow")
    assert state is not None
    assert state.cash == pytest.approx(1_000_000.0)
    assert state.positions == {}


def test_load_broker_state_queries_are_scoped() -> None:
    """The equity query filters by strategy + paper mode; fills scope by broker
    AND strategy_id (ADR-038 — fills now carries a strategy discriminator)."""
    conn, cur = _fake_conn(equity_row=(1.0,), fill_rows=[])
    with patch("backtest_platform.services.monitoring_ops.telemetry_reader._connection") as ctx:
        ctx.return_value.__enter__.return_value = conn
        load_broker_state("inst_flow")

    calls = [c.args for c in cur.execute.call_args_list]
    equity_sql, equity_params = calls[0]
    assert "equity_snapshots" in equity_sql
    assert "mode" in equity_sql and "strategy_id" in equity_sql
    assert "inst_flow" in equity_params and "paper" in equity_params
    fills_sql, fills_params = calls[1]
    assert "fills" in fills_sql and "strategy_id" in fills_sql
    assert "orders" not in fills_sql  # ADR-038 dropped the orders table
    assert "paper" in fills_params and "inst_flow" in fills_params


# --------------------------------------------------------------------------- #
# integration — real TimescaleDB round-trip (skipped unless env says it's up)   #
# --------------------------------------------------------------------------- #
@pytest.mark.integration
def test_load_broker_state_real_db() -> None:
    """Round-trip against a live DB: write fills+equity, restore them. Skipped by default."""
    if not os.environ.get("POSTGRES_INTEGRATION"):
        pytest.skip("set POSTGRES_INTEGRATION=1 to run against a live DB")

    from datetime import datetime, timezone

    from backtest_platform.data import db_writer as dbw

    strat = "restore_it_test"
    now = datetime.now(timezone.utc)
    dbw.upsert_fills([
        {"stock_id": "TEST", "side": "buy", "qty": 1000, "price": 100.0,
         "strategy_id": strat, "filled_at": now},
    ])
    dbw.upsert_equity_snapshots([
        {
            "snapshot_time": now, "strategy_id": strat, "mode": "paper",
            "run_id": "restore-it", "equity": 1_100_000.0, "cash": 1_000_000.0,
            "positions_value": 100_000.0, "open_positions": 1, "portfolio_heat": 0.0,
        }
    ])
    state = load_broker_state(strat)
    assert state is not None
    assert state.cash == pytest.approx(1_000_000.0)


# ---------------------------------------------------------------------------
# A2 — runs_board: latest runs (lifecycle + 審判庭 verdict) for the run board
# ---------------------------------------------------------------------------
def test_runs_board_maps_rows() -> None:
    from datetime import date, datetime, timezone

    from backtest_platform.data.db_reader import TelemetryReader

    created = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)
    cur = MagicMock()
    cur.fetchall.return_value = [
        (
            "a1b2c3d4e5f6", "inst_flow", "sim", ["2330", "2317"],
            date(2026, 1, 5), date(2026, 4, 10), "done",
            "PASS", "IS gate: 4/4", {"sharpe": 1.1}, created,
        ),
        (
            "ffffffffffff", "inst_flow", "sim", ["2454"],
            date(2026, 1, 5), date(2026, 4, 10), "running",
            None, None, None, created,
        ),
    ]
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur

    with patch("backtest_platform.services.monitoring_ops.telemetry_reader._connection") as ctx:
        ctx.return_value.__enter__.return_value = conn
        rows = TelemetryReader(cfg=MagicMock()).runs_board(limit=10)

    sql = cur.execute.call_args.args[0]
    assert "FROM runs" in sql and "ORDER BY created_at DESC" in sql
    assert cur.execute.call_args.args[1] == [10]
    assert rows[0] == {
        "run_id": "a1b2c3d4e5f6", "strategy": "inst_flow", "engine": "sim",
        "stocks": ["2330", "2317"], "is_start": "2026-01-05", "is_end": "2026-04-10",
        "status": "done", "gate_status": "PASS", "gate_summary": "IS gate: 4/4",
        "metrics": {"sharpe": 1.1}, "created_at": created.isoformat(),
    }
    # in-flight run: nullable verdict/metrics stay None (frontend renders —)
    assert rows[1]["status"] == "running"
    assert rows[1]["gate_status"] is None and rows[1]["metrics"] is None


def test_runs_board_empty_returns_empty_list() -> None:
    from backtest_platform.data.db_reader import TelemetryReader

    cur = MagicMock()
    cur.fetchall.return_value = []
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    with patch("backtest_platform.services.monitoring_ops.telemetry_reader._connection") as ctx:
        ctx.return_value.__enter__.return_value = conn
        assert TelemetryReader(cfg=MagicMock()).runs_board() == []
