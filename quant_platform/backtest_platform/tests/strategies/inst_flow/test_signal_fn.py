"""inst_flow paper/live signal adapter (7.A.4) — ranking, sizing, chain schema."""
from __future__ import annotations

from datetime import date

import pandas as pd

from backtest_platform.services.strategy_runtime.inst_flow_signals import (
    compute_inst_flow_signals,
    make_inst_flow_signal_fn,
)
from backtest_platform.strategies.inst_flow.strategy import InstFlowConfig

# 3 stocks over 80 sessions. A is heavily net-bought, B mildly, C net-sold.
_DATES = pd.bdate_range("2024-01-01", periods=80)
_CFG = InstFlowConfig(lookback_days=20, signal_lag_days=0, top_fraction=2 / 3)


def _panel():
    close = pd.DataFrame(
        {"A": 100.0, "B": 50.0, "C": 25.0}, index=_DATES
    )
    volume = pd.DataFrame(
        {"A": 1_000.0, "B": 1_000.0, "C": 1_000.0}, index=_DATES
    )
    # net-buy intensity: A strong +, B small +, C negative
    flow = pd.DataFrame(
        {"A": 200.0, "B": 20.0, "C": -200.0}, index=_DATES
    )
    return close, flow, volume


def test_ranks_by_intensity_and_emits_chain_schema() -> None:
    close, flow, volume = _panel()
    sigs = compute_inst_flow_signals(
        close, flow, volume, _CFG, date(2024, 4, 1), equity=1_000_000.0
    )
    # C is net-sold (negative) → excluded; A ranks above B.
    assert [s["stock_id"] for s in sigs] == ["A", "B"]
    top = sigs[0]
    # exact chain schema (matches test_chain_integration / collaborators)
    assert top["side"] == "buy"
    assert top["action"] == "buy"
    assert top["priority"] == 2
    assert top["qty"] > 0
    assert top["stop_loss"] == round(top["price"] * 0.96, 4)  # 4% stop, inside EX-008
    assert top["reason"]["factor"] == "inst_flow_intensity"
    assert top["reason"]["rank"] == 1
    assert {"prev_close", "avg_volume_20d", "industry"} <= top.keys()


def test_per_name_cap_limits_order_notional() -> None:
    close, flow, volume = _panel()
    # tiny cap → qty bounded by cap/price, not equity/price
    sigs = compute_inst_flow_signals(
        close, flow, volume, _CFG, date(2024, 4, 1),
        equity=10_000_000.0, per_name_cap=10_000.0,
    )
    a = next(s for s in sigs if s["stock_id"] == "A")
    assert a["qty"] == 10_000 // 100  # cap 10k / price 100


def test_max_names_caps_breadth_for_risk_gate() -> None:
    close, flow, volume = _panel()
    sigs = compute_inst_flow_signals(
        close, flow, volume, _CFG, date(2024, 4, 1), equity=1_000_000.0, max_names=1
    )
    assert len(sigs) == 1 and sigs[0]["stock_id"] == "A"


def test_as_of_before_any_score_returns_empty() -> None:
    close, flow, volume = _panel()
    # lookback 20 not yet satisfied on day 1 → no score → no signals
    sigs = compute_inst_flow_signals(
        close, flow, volume, _CFG, date(2024, 1, 1), equity=1_000_000.0
    )
    assert sigs == []


def test_make_signal_fn_binds_panel_and_ignores_ctx() -> None:
    close, flow, volume = _panel()
    fn = make_inst_flow_signal_fn(
        close, flow, volume, _CFG, date(2024, 4, 1), equity=1_000_000.0
    )
    assert [s["stock_id"] for s in fn(object())] == ["A", "B"]
