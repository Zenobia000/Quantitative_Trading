"""Tests for the live market reader + forward-paper wiring (③).

All FinLab access goes through an injected ``getter`` — no live calls.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from quant_platform.services.execution_gateway.paper_broker import PaperBroker
from quant_platform.services.strategy_runtime import live_session as mr
from quant_platform.services.strategy_runtime.paper_daemon import run_paper_replay
from quant_platform.services.research_validation.strategies.inst_flow.strategy import InstFlowConfig

_INST = "institutional_investors_trading_summary"
AS_OF = date(2024, 12, 31)


def _wide(per_symbol: dict[str, float], idx) -> pd.DataFrame:
    return pd.DataFrame({s: v for s, v in per_symbol.items()}, index=idx)


def _stub_getter(periods: int = 120):
    idx = pd.bdate_range(end=AS_OF, periods=periods)
    cols = ["A", "B", "C", "D"]
    close = pd.DataFrame(100.0, index=idx, columns=cols)
    volume = pd.DataFrame(2_000_000.0, index=idx, columns=cols)
    # positive, descending foreign net-buy so ranking is well-defined
    foreign1 = pd.DataFrame({"A": 5000.0, "B": 4000.0, "C": 3000.0, "D": 2000.0}, index=idx)
    foreign2 = pd.DataFrame({"A": 100.0, "B": 100.0, "C": 100.0, "D": 100.0}, index=idx)
    frames = {
        "etl:adj_close": close,
        "price:成交股數": volume,
        f"{_INST}:外陸資買賣超股數(不含外資自營商)": foreign1,
        f"{_INST}:外資自營商買賣超股數": foreign2,
    }
    return lambda key: frames[key]


def test_read_live_panel_slices_universe_and_window():
    close, flow, _volume = mr.read_live_panel(
        ["A", "B", "X"], AS_OF, lookback_days=200, getter=_stub_getter()
    )
    assert list(close.columns) == ["A", "B"]  # only requested + present
    assert close.index.max() <= pd.Timestamp(AS_OF)  # no look-ahead
    assert close.index.min() >= pd.Timestamp(AS_OF) - pd.Timedelta(days=200)
    # flow = foreign net-buy summed (外陸資 5000 + 外資自營商 100 = 5100 for A)
    assert float(flow["A"].iloc[-1]) == 5100.0


def test_live_config_for_date_runs_chain_green():
    broker = PaperBroker(initial_cash=10_000_000.0)
    logged: list[str] = []
    cfg = InstFlowConfig(rebalance="quarterly", lookback_days=60, flow_source="foreign")
    config_for_date = mr.live_config_for_date(
        ["A", "B", "C", "D"], cfg, broker,
        run_id="fwd_test", strategy_id="inst_flow",
        getter=_stub_getter(), equity=10_000_000.0,
        sink=lambda ctx: (logged.append("ok"), "mem-logged")[1],  # in-memory sink, no DB
    )
    summary = run_paper_replay([AS_OF], config_for_date)
    assert summary.n_steps == 1
    assert summary.ok  # ETL→signals→risk→orders→log all green
    assert logged == ["ok"]  # sink ran
    assert broker.trade_log  # at least one fill placed


def test_make_position_signal_fn_emits_gate_safe_signals():
    prices = pd.Series({"A": 100.0, "B": 250.0})
    avg_volume = pd.Series({"A": 5_000_000.0, "B": 5_000_000.0})
    signal_fn = mr.make_position_signal_fn(
        ["A", "B"], prices, avg_volume, equity=1_000_000.0
    )
    signals = signal_fn(None)
    assert len(signals) == 2
    a = next(s for s in signals if s["stock_id"] == "A")
    assert a["side"] == "buy" and a["qty"] > 0
    assert a["stop_loss"] < a["price"]  # gate-safe stop below entry
    assert a["avg_volume_20d"] == 5_000_000.0


def test_make_position_signal_fn_empty_holdings():
    assert mr.make_position_signal_fn([], pd.Series(dtype=float), pd.Series(dtype=float), equity=1e6)(None) == []
