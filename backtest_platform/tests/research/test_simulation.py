"""Pure what-if simulation (``research.simulation``) — Goal 8.

Every case is hand-computable so the recompute math is auditable, and each honest
degradation path (panel no per-trade pnl, no baseline cost, no equity) is pinned.
The last test asserts the original equity/trades inputs are never mutated (the
research sandbox is strictly read-only).
"""
from __future__ import annotations

import pytest

from backtest_platform.research import simulation as sim

# A 3-point equity curve → per-bar returns [0.1, 0.1]; the arithmetic makes every
# downstream metric hand-checkable.
_EQUITY = [1.0, 1.1, 1.21]
# Four-layer-type trades (carry per-trade ``ret``) → stop-loss / take-profit feasible.
_TRADES = [
    {"ret": -0.20, "hold": 3, "entry_structure": 1},
    {"ret": 0.30, "hold": 5, "entry_structure": 2},
    {"ret": 0.05, "hold": 2, "entry_structure": 1},
]


# --------------------------------------------------------------------------- #
# helpers                                                                      #
# --------------------------------------------------------------------------- #
def test_reconstruct_returns_from_equity():
    assert sim.reconstruct_returns(_EQUITY) == pytest.approx([0.1, 0.1])


def test_has_per_trade_returns_detects_panel_vs_four_layer():
    assert sim.has_per_trade_returns(_TRADES) is True
    assert sim.has_per_trade_returns([]) is False
    # panel rebalance count carries no ``ret`` key.
    assert sim.has_per_trade_returns([{"date": "2020-01-01", "n": 5}]) is False


def test_base_round_trip_cost_extraction():
    assert sim.base_round_trip_cost({"cost_round_rate": 0.00671}) == pytest.approx(0.00671)
    # four-layer: 2·fee + tax + 2·slip.
    fl = {"fee_rate": 0.001425, "tax_stock_rate": 0.003, "slip_rate": 0.001}
    assert sim.base_round_trip_cost(fl) == pytest.approx(2 * 0.001425 + 0.003 + 2 * 0.001)
    assert sim.base_round_trip_cost({}) is None
    assert sim.base_round_trip_cost(None) is None


# --------------------------------------------------------------------------- #
# cost multiplier — hand-computed recompute                                    #
# --------------------------------------------------------------------------- #
def test_cost_multiplier_recompute_matches_hand_calc():
    # extra_cost = (2.0-1.0)·0.001·4 = 0.004 ; drag = 0.004/2 = 0.002
    # after returns = [0.098, 0.098] → total_return = 1.098² - 1 = 0.205604
    out = sim.simulate(
        _EQUITY, [], cost_multiplier=2.0, n_trades=4, turnover_units=4.0, round_trip_cost=0.001
    )
    p = out["portfolio_metrics"]
    assert p["available"] is True
    assert p["before"]["total_return"] == pytest.approx(0.21)
    assert p["after"]["total_return"] == pytest.approx(1.098 * 1.098 - 1.0)
    assert p["deltas"]["total_return"] == pytest.approx((1.098 * 1.098 - 1.0) - 0.21)
    # cost touches every rebalance/trade → affected = the cost-event count.
    assert out["affected_trades_count"] == 4
    cm = next(x for x in out["per_param"] if x["param"] == "cost_multiplier")
    assert cm["status"] == "applied" and cm["applied"] is True


def test_slippage_bps_is_additive_no_baseline_needed():
    # slip_cost = 50·1e-4·4 = 0.02 ; drag = 0.01 → after returns [0.09, 0.09]
    out = sim.simulate(
        _EQUITY, [], slippage_bps=50.0, n_trades=4, turnover_units=4.0, round_trip_cost=None
    )
    p = out["portfolio_metrics"]
    assert p["after"]["total_return"] == pytest.approx(1.09 * 1.09 - 1.0)
    assert out["affected_trades_count"] == 4


def test_capacity_scale_scales_exposure():
    # capacity 2x -> after returns [0.2, 0.2] -> total_return = 1.2^2 - 1 = 0.44
    out = sim.simulate(_EQUITY, [], capacity_scale=2.0, n_trades=4, turnover_units=4.0)
    p = out["portfolio_metrics"]
    assert p["after"]["total_return"] == pytest.approx(1.2 * 1.2 - 1.0)
    assert out["affected_trades_count"] == 4


# --------------------------------------------------------------------------- #
# stop-loss / take-profit — trade-population clamp                             #
# --------------------------------------------------------------------------- #
def test_stop_loss_take_profit_clamp_and_affected_count():
    # SL 0.10 clamps trade1 (-0.20→-0.10); TP 0.25 clamps trade2 (0.30→0.25) → 2 moved.
    out = sim.simulate(
        [], _TRADES, stop_loss_pct=0.10, take_profit_pct=0.25
    )
    t = out["trade_metrics"]
    assert t["available"] is True
    # before: 0.8·1.3·1.05 - 1 = 0.092 ; after: 0.9·1.25·1.05 - 1 = 0.18125
    assert t["before"]["total_trade_return"] == pytest.approx(0.8 * 1.3 * 1.05 - 1.0)
    assert t["after"]["total_trade_return"] == pytest.approx(0.9 * 1.25 * 1.05 - 1.0)
    assert t["before"]["win_rate"] == pytest.approx(2 / 3)
    assert out["affected_trades_count"] == 2
    # a branch suggestion is emitted (config delta description, not applied).
    bs = out["branch_suggestion"]
    assert bs is not None and bs["actionable"] is False
    keys = {d["key"] for d in bs["config_delta"]}
    assert {"stop_loss_pct", "take_profit_pct"} <= keys


def test_stop_loss_only_clamps_losers_not_winners():
    out = sim.simulate([], _TRADES, stop_loss_pct=0.10)
    # only trade1 (-0.20) is beyond the stop → 1 affected.
    assert out["affected_trades_count"] == 1


# --------------------------------------------------------------------------- #
# honest degradation paths (rule #6)                                          #
# --------------------------------------------------------------------------- #
def test_panel_stop_loss_is_not_available_with_reason():
    # panel run: equity present, but trades carry no per-trade ret.
    out = sim.simulate(_EQUITY, [], stop_loss_pct=0.10, n_trades=6, turnover_units=3.0)
    assert out["trade_metrics"]["available"] is False
    sl = next(x for x in out["per_param"] if x["param"] == "stop_loss_pct")
    assert sl["status"] == "not_available"
    assert "per-trade" in sl["reason"]
    assert any(g["field"] == "stop_loss_pct" for g in out["data_gaps"])
    # portfolio space still works (equity present) — degradation is scoped.
    assert out["portfolio_metrics"]["available"] is True


def test_cost_multiplier_not_available_without_baseline_cost():
    out = sim.simulate(
        _EQUITY, [], cost_multiplier=1.5, n_trades=4, turnover_units=4.0, round_trip_cost=None
    )
    cm = next(x for x in out["per_param"] if x["param"] == "cost_multiplier")
    assert cm["status"] == "not_available" and cm["applied"] is False
    # after == before (no baseline → no cost applied), no false movement.
    p = out["portfolio_metrics"]
    assert p["after"]["total_return"] == pytest.approx(p["before"]["total_return"])
    assert out["affected_trades_count"] == 0


def test_no_equity_makes_portfolio_space_not_available():
    out = sim.simulate([], _TRADES, cost_multiplier=1.5, round_trip_cost=0.001)
    assert out["portfolio_metrics"]["available"] is False
    assert "equity" in out["portfolio_metrics"]["reason"]
    # trade space still works (per-trade trades present).
    assert out["trade_metrics"]["available"] is True


def test_no_op_request_emits_no_branch_suggestion():
    out = sim.simulate(_EQUITY, _TRADES)  # all defaults → nothing applied
    assert out["branch_suggestion"] is None
    assert out["affected_trades_count"] == 0
    assert all(x["status"] == "noop" for x in out["per_param"])


# --------------------------------------------------------------------------- #
# immutability — the sandbox never mutates its inputs                          #
# --------------------------------------------------------------------------- #
def test_original_series_are_not_mutated():
    equity = list(_EQUITY)
    trades = [dict(t) for t in _TRADES]
    equity_snapshot = list(equity)
    trades_snapshot = [dict(t) for t in trades]

    sim.simulate(
        equity, trades, cost_multiplier=2.0, slippage_bps=10.0,
        stop_loss_pct=0.10, take_profit_pct=0.25, capacity_scale=1.5,
        n_trades=3, turnover_units=3.0, round_trip_cost=0.001,
    )

    assert equity == equity_snapshot
    assert trades == trades_snapshot
