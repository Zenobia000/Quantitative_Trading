"""TDD spec for the strategy-agnostic PaperBroker (WBS 7.A.1 / 7.A.2).

Rules pinned from:
  - dev_docs/23_deployment_topology.md §3.3 (paper-trading fill flow,
    ``python -m ...paper_broker`` entrypoint)
  - dev_docs/24_risk_management_spec.md §EX-004
    (Heat = Σ qty·|entry − stop| / equity)
  - config.strategy_config.StrategyConfig (cost model: fee_rate × fee_discount
    on both sides, tax_stock_rate on the sell side only).

These tests are deliberately synthetic / injection-based: no DB, no network,
no FinLab/Shioaji client. Marks/mark-to-market prices are passed in directly.
"""
from __future__ import annotations

import math

import pytest

from quant_platform.services.execution_gateway.paper_broker import (
    Fill,
    InsufficientPositionError,
    OrderSide,
    PaperBroker,
)
from quant_platform.services.research_validation.strategies.four_layer_resonance.config import StrategyConfig

# A zero-cost config makes cash arithmetic exact and lets us isolate
# position/equity logic from fee math in the structural tests.
ZERO_COST = StrategyConfig(
    fee_rate=0.0, fee_discount=1.0, tax_stock_rate=0.0, slip_rate=0.0
)


# --------------------------------------------------------------------------- #
# Construction / invariants
# --------------------------------------------------------------------------- #
def test_initial_state() -> None:
    br = PaperBroker(initial_cash=1_000_000.0, config=ZERO_COST)
    assert br.cash == 1_000_000.0
    assert br.positions == {}
    assert br.trade_log == []
    # No positions => equity is just cash.
    assert br.equity() == 1_000_000.0


def test_initial_cash_must_be_positive() -> None:
    with pytest.raises(ValueError):
        PaperBroker(initial_cash=0.0, config=ZERO_COST)
    with pytest.raises(ValueError):
        PaperBroker(initial_cash=-1.0, config=ZERO_COST)


# --------------------------------------------------------------------------- #
# Buy: positions + cash (zero cost)
# --------------------------------------------------------------------------- #
def test_buy_updates_position_and_cash_zero_cost() -> None:
    br = PaperBroker(initial_cash=1_000_000.0, config=ZERO_COST)
    fill = br.submit_order("2330", OrderSide.BUY, qty=1_000, price=500.0)

    assert isinstance(fill, Fill)
    assert fill.stock_id == "2330"
    assert fill.side is OrderSide.BUY
    assert fill.qty == 1_000
    assert fill.price == 500.0
    assert fill.fee == 0.0
    assert fill.tax == 0.0

    # cash = 1_000_000 - 1_000*500 = 500_000
    assert br.cash == 500_000.0
    pos = br.positions["2330"]
    assert pos.qty == 1_000
    assert pos.cost_basis == 500.0  # avg cost per share


def test_buy_accepts_string_side() -> None:
    """submit_order must tolerate plain 'buy'/'sell' strings (CLI-friendly)."""
    br = PaperBroker(initial_cash=1_000_000.0, config=ZERO_COST)
    br.submit_order("2330", "buy", qty=100, price=500.0)
    assert br.positions["2330"].qty == 100


def test_averaging_up_recomputes_cost_basis() -> None:
    br = PaperBroker(initial_cash=2_000_000.0, config=ZERO_COST)
    br.submit_order("2330", OrderSide.BUY, qty=1_000, price=500.0)
    br.submit_order("2330", OrderSide.BUY, qty=1_000, price=600.0)
    pos = br.positions["2330"]
    assert pos.qty == 2_000
    # weighted avg = (1000*500 + 1000*600) / 2000 = 550
    assert pos.cost_basis == 550.0


# --------------------------------------------------------------------------- #
# Sell: reduce position, free cash, realized P&L
# --------------------------------------------------------------------------- #
def test_sell_reduces_position_and_adds_cash() -> None:
    br = PaperBroker(initial_cash=1_000_000.0, config=ZERO_COST)
    br.submit_order("2330", OrderSide.BUY, qty=1_000, price=500.0)
    br.submit_order("2330", OrderSide.SELL, qty=400, price=550.0)

    pos = br.positions["2330"]
    assert pos.qty == 600
    # cost basis unchanged on a partial sell
    assert pos.cost_basis == 500.0
    # cash = 500_000 (after buy) + 400*550 = 720_000
    assert br.cash == 720_000.0


def test_full_sell_clears_position() -> None:
    br = PaperBroker(initial_cash=1_000_000.0, config=ZERO_COST)
    br.submit_order("2330", OrderSide.BUY, qty=1_000, price=500.0)
    br.submit_order("2330", OrderSide.SELL, qty=1_000, price=550.0)
    assert "2330" not in br.positions
    assert br.cash == 1_050_000.0  # 500k + 550k


def test_sell_without_position_raises() -> None:
    br = PaperBroker(initial_cash=1_000_000.0, config=ZERO_COST)
    with pytest.raises(InsufficientPositionError):
        br.submit_order("2330", OrderSide.SELL, qty=100, price=500.0)


def test_oversell_more_than_held_raises_no_naked_short() -> None:
    br = PaperBroker(initial_cash=1_000_000.0, config=ZERO_COST)
    br.submit_order("2330", OrderSide.BUY, qty=500, price=500.0)
    with pytest.raises(InsufficientPositionError):
        br.submit_order("2330", OrderSide.SELL, qty=600, price=500.0)
    # state untouched after a rejected order
    assert br.positions["2330"].qty == 500
    assert br.cash == 750_000.0


# --------------------------------------------------------------------------- #
# Input validation
# --------------------------------------------------------------------------- #
def test_non_positive_qty_rejected() -> None:
    br = PaperBroker(initial_cash=1_000_000.0, config=ZERO_COST)
    with pytest.raises(ValueError):
        br.submit_order("2330", OrderSide.BUY, qty=0, price=500.0)
    with pytest.raises(ValueError):
        br.submit_order("2330", OrderSide.BUY, qty=-10, price=500.0)


def test_non_positive_price_rejected() -> None:
    br = PaperBroker(initial_cash=1_000_000.0, config=ZERO_COST)
    with pytest.raises(ValueError):
        br.submit_order("2330", OrderSide.BUY, qty=100, price=0.0)


def test_insufficient_cash_rejected() -> None:
    br = PaperBroker(initial_cash=1_000.0, config=ZERO_COST)
    with pytest.raises(ValueError):
        br.submit_order("2330", OrderSide.BUY, qty=1_000, price=500.0)


# --------------------------------------------------------------------------- #
# Fees / tax (default StrategyConfig cost model)
# --------------------------------------------------------------------------- #
def test_buy_fee_deducted_from_cash() -> None:
    cfg = StrategyConfig()  # fee_rate .001425, discount .6, tax .003
    br = PaperBroker(initial_cash=1_000_000.0, config=cfg)
    notional = 1_000 * 500.0
    fill = br.submit_order("2330", OrderSide.BUY, qty=1_000, price=500.0)

    expected_fee = notional * cfg.fee_rate * cfg.fee_discount
    assert math.isclose(fill.fee, expected_fee, rel_tol=1e-12)
    # buy side: no securities-transaction tax
    assert fill.tax == 0.0
    # cash = initial - notional - fee
    assert math.isclose(br.cash, 1_000_000.0 - notional - expected_fee, rel_tol=1e-12)


def test_sell_charges_fee_and_tax() -> None:
    cfg = StrategyConfig()
    br = PaperBroker(initial_cash=1_000_000.0, config=cfg)
    br.submit_order("2330", OrderSide.BUY, qty=1_000, price=500.0)
    cash_after_buy = br.cash

    notional = 1_000 * 550.0
    fill = br.submit_order("2330", OrderSide.SELL, qty=1_000, price=550.0)

    expected_fee = notional * cfg.fee_rate * cfg.fee_discount
    expected_tax = notional * cfg.tax_stock_rate
    assert math.isclose(fill.fee, expected_fee, rel_tol=1e-12)
    assert math.isclose(fill.tax, expected_tax, rel_tol=1e-12)
    # proceeds = notional - fee - tax
    assert math.isclose(
        br.cash, cash_after_buy + notional - expected_fee - expected_tax, rel_tol=1e-12
    )


# --------------------------------------------------------------------------- #
# Equity: mark-to-market with latest prices
# --------------------------------------------------------------------------- #
def test_equity_marks_to_market() -> None:
    br = PaperBroker(initial_cash=1_000_000.0, config=ZERO_COST)
    br.submit_order("2330", OrderSide.BUY, qty=1_000, price=500.0)
    # cash now 500_000, holding 1000 @ cost 500
    # mark at 600 => position MV = 600_000, equity = 1_100_000
    assert br.equity(marks={"2330": 600.0}) == 1_100_000.0
    # mark at 400 => MV = 400_000, equity = 900_000
    assert br.equity(marks={"2330": 400.0}) == 900_000.0


def test_equity_falls_back_to_last_fill_price() -> None:
    """When no mark is supplied, the latest fill price is used."""
    br = PaperBroker(initial_cash=1_000_000.0, config=ZERO_COST)
    br.submit_order("2330", OrderSide.BUY, qty=1_000, price=500.0)
    # no marks => uses last fill price 500 => MV 500_000 => equity 1_000_000
    assert br.equity() == 1_000_000.0


def test_equity_missing_mark_for_one_symbol_uses_its_last_price() -> None:
    br = PaperBroker(initial_cash=2_000_000.0, config=ZERO_COST)
    br.submit_order("2330", OrderSide.BUY, qty=1_000, price=500.0)
    br.submit_order("2317", OrderSide.BUY, qty=1_000, price=100.0)
    # mark only 2330; 2317 falls back to its last fill price 100
    eq = br.equity(marks={"2330": 700.0})
    # cash = 2_000_000 - 500_000 - 100_000 = 1_400_000
    # MV = 1000*700 + 1000*100 = 800_000
    assert eq == 2_200_000.0


# --------------------------------------------------------------------------- #
# Trade log
# --------------------------------------------------------------------------- #
def test_trade_log_records_every_fill_in_order() -> None:
    br = PaperBroker(initial_cash=1_000_000.0, config=ZERO_COST)
    br.submit_order("2330", OrderSide.BUY, qty=100, price=500.0)
    br.submit_order("2317", OrderSide.BUY, qty=200, price=100.0)
    br.submit_order("2330", OrderSide.SELL, qty=50, price=520.0)

    log = br.trade_log
    assert len(log) == 3
    assert [f.stock_id for f in log] == ["2330", "2317", "2330"]
    assert [f.side for f in log] == [OrderSide.BUY, OrderSide.BUY, OrderSide.SELL]
    # log is a copy: mutating it must not corrupt internal state
    log.clear()
    assert len(br.trade_log) == 3


def test_rejected_order_not_logged() -> None:
    br = PaperBroker(initial_cash=1_000_000.0, config=ZERO_COST)
    with pytest.raises(InsufficientPositionError):
        br.submit_order("2330", OrderSide.SELL, qty=100, price=500.0)
    assert br.trade_log == []


def test_fill_is_immutable() -> None:
    br = PaperBroker(initial_cash=1_000_000.0, config=ZERO_COST)
    fill = br.submit_order("2330", OrderSide.BUY, qty=100, price=500.0)
    with pytest.raises(Exception):
        fill.qty = 999  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# portfolio_snapshot() for monitoring / risk
# --------------------------------------------------------------------------- #
def test_portfolio_snapshot_shape() -> None:
    br = PaperBroker(initial_cash=1_000_000.0, config=ZERO_COST)
    br.submit_order("2330", OrderSide.BUY, qty=1_000, price=500.0)
    snap = br.portfolio_snapshot(marks={"2330": 500.0})

    assert set(snap.keys()) >= {"positions", "cash", "equity", "heat"}
    assert snap["cash"] == 500_000.0
    assert snap["equity"] == 1_000_000.0
    # positions reported as a plain dict for serialization
    assert snap["positions"]["2330"]["qty"] == 1_000
    assert snap["positions"]["2330"]["cost_basis"] == 500.0


def test_snapshot_heat_zero_when_no_stops_known() -> None:
    """Strategy-agnostic default: no stop levels => heat contribution 0."""
    br = PaperBroker(initial_cash=1_000_000.0, config=ZERO_COST)
    br.submit_order("2330", OrderSide.BUY, qty=1_000, price=500.0)
    snap = br.portfolio_snapshot(marks={"2330": 500.0})
    assert snap["heat"] == 0.0


def test_snapshot_heat_uses_ex004_formula() -> None:
    """Heat = Σ qty·|entry − stop| / equity (dev_docs/24 §EX-004)."""
    br = PaperBroker(initial_cash=1_000_000.0, config=ZERO_COST)
    br.submit_order("2330", OrderSide.BUY, qty=1_000, price=500.0)
    # entry 500, stop 480 => risk per share 20 => 1000*20 = 20_000
    snap = br.portfolio_snapshot(
        marks={"2330": 500.0}, stop_prices={"2330": 480.0}
    )
    # equity = 1_000_000 (cash 500k + MV 500k)
    assert math.isclose(snap["heat"], 20_000.0 / 1_000_000.0, rel_tol=1e-12)


def test_snapshot_empty_portfolio() -> None:
    br = PaperBroker(initial_cash=1_000_000.0, config=ZERO_COST)
    snap = br.portfolio_snapshot()
    assert snap["positions"] == {}
    assert snap["cash"] == 1_000_000.0
    assert snap["equity"] == 1_000_000.0
    assert snap["heat"] == 0.0


# --------------------------------------------------------------------------- #
# from_seed() — rehydrate a broker from persisted cash + positions (restore)
# --------------------------------------------------------------------------- #
def test_from_seed_restores_cash_and_positions() -> None:
    """A seeded broker carries the restored cash + holdings, with cost basis as the
    mark fallback so equity marks-to-cost without any explicit prices."""
    br = PaperBroker.from_seed(
        cash=850_000.0, positions={"2330": (1_000, 500.0), "2317": (2_000, 50.0)},
        config=ZERO_COST,
    )
    assert br.cash == 850_000.0
    assert br.positions["2330"].qty == 1_000
    assert br.positions["2330"].cost_basis == 500.0
    assert br.positions["2317"].qty == 2_000
    # equity with no marks falls back to cost basis: 850k + 1000*500 + 2000*50
    assert br.equity() == pytest.approx(850_000.0 + 500_000.0 + 100_000.0)


def test_from_seed_does_not_log_seeded_positions_as_fills() -> None:
    """Seeded holdings are pre-existing, not this-session fills → empty trade log."""
    br = PaperBroker.from_seed(cash=1_000_000.0, positions={"2330": (1_000, 500.0)})
    assert br.trade_log == []


def test_from_seed_positions_are_real_and_sellable() -> None:
    """A restored position is a real holding (not a read-only view): it can be sold."""
    br = PaperBroker.from_seed(
        cash=100_000.0, positions={"2330": (1_000, 500.0)}, config=ZERO_COST,
    )
    fill = br.submit_order("2330", OrderSide.SELL, qty=400, price=520.0)
    assert fill.qty == 400
    assert br.positions["2330"].qty == 600
    assert br.cash == pytest.approx(100_000.0 + 400 * 520.0)


def test_from_seed_empty_positions_is_plain_broker() -> None:
    br = PaperBroker.from_seed(cash=1_000_000.0, positions={})
    assert br.cash == 1_000_000.0
    assert br.positions == {}
