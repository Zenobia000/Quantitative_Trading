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
  * **positions** — folded from the persisted fills (``orders`` rows, the fill
    log) chronologically, mirroring ``PaperBroker`` averaging, because the
    ``positions`` table is never written by the paper/live flow (only tests call
    ``upsert_positions``) and ``equity_snapshots.open_positions`` is a count only.

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
    with patch("backtest_platform.data.db_reader._connection") as ctx:
        ctx.return_value.__enter__.return_value = conn
        state = load_broker_state("inst_flow")

    assert isinstance(state, BrokerState)
    assert state.cash == pytest.approx(850_000.0)
    assert state.positions["2330"] == PositionState(qty=2000, cost_basis=105.0)
    assert state.positions["2317"] == PositionState(qty=500, cost_basis=50.0)


def test_load_broker_state_first_day_returns_none() -> None:
    """(b) no equity snapshot for the strategy → None (first session, nothing to restore)."""
    conn, _ = _fake_conn(equity_row=None, fill_rows=[])
    with patch("backtest_platform.data.db_reader._connection") as ctx:
        ctx.return_value.__enter__.return_value = conn
        state = load_broker_state("inst_flow")
    assert state is None


def test_load_broker_state_raises_on_db_error_never_silent_empty() -> None:
    """(c) a DB failure must propagate — never a silent empty book (dishonest OOS)."""
    with patch("backtest_platform.data.db_reader._connection") as ctx:
        ctx.side_effect = RuntimeError("connection refused")
        with pytest.raises(RuntimeError, match="connection refused"):
            load_broker_state("inst_flow")


def test_load_broker_state_cash_only_when_no_fills() -> None:
    """A snapshot with no fills → cash restored, empty positions (not None)."""
    conn, _ = _fake_conn(equity_row=(1_000_000.0,), fill_rows=[])
    with patch("backtest_platform.data.db_reader._connection") as ctx:
        ctx.return_value.__enter__.return_value = conn
        state = load_broker_state("inst_flow")
    assert state is not None
    assert state.cash == pytest.approx(1_000_000.0)
    assert state.positions == {}


def test_load_broker_state_queries_are_scoped() -> None:
    """The equity query filters by strategy + paper mode; fills filter paper fills."""
    conn, cur = _fake_conn(equity_row=(1.0,), fill_rows=[])
    with patch("backtest_platform.data.db_reader._connection") as ctx:
        ctx.return_value.__enter__.return_value = conn
        load_broker_state("inst_flow")

    calls = [c.args for c in cur.execute.call_args_list]
    equity_sql, equity_params = calls[0]
    assert "equity_snapshots" in equity_sql
    assert "mode" in equity_sql and "strategy_id" in equity_sql
    assert "inst_flow" in equity_params and "paper" in equity_params
    fills_sql, fills_params = calls[1]
    assert "orders" in fills_sql and "filled" in fills_sql.lower()
    assert "paper" in fills_params


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
        {"stock_id": "TEST", "side": "buy", "qty": 1000, "price": 100.0, "filled_at": now},
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
