"""run_is / run_and_judge — IS harness logic via an injected synthetic loader
(NOT cache-gated; the real-parquet path is the manual integration step)."""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from backtest_platform.research.is_harness import (
    equity_drawdown,
    run_and_judge,
    run_and_judge_persist,
    run_and_judge_with_returns,
    run_is,
    run_is_returns,
    run_is_trades,
)
from backtest_platform.research.run_config import RunConfig
from backtest_platform.research.run_series_store import read_series


def _synthetic_loader(sid: str) -> pd.DataFrame:
    """A rising-trend frame with positive institutional/chip flow → produces entries."""
    n = 260
    dates = pd.date_range("2019-05-01", periods=n, freq="D")
    close = np.linspace(50, 135, n) + np.sin(np.arange(n) / 4.0) * 1.5
    return pd.DataFrame({
        "trade_date": dates, "stock_id": sid,
        "open": close - 0.3, "high": close * 1.03, "low": close * 0.97,
        "close": close, "volume": 5000,
        "foreign_buy": 120, "trust_buy": 60, "dealer_buy": 10,
        "top_broker_buy": 90, "key_broker_buy": 50, "gov_broker_buy": 5, "geo_broker_buy": 5,
        "day_trade_volume": 500, "margin_offset_volume": 100,
    })


def _cfg(**kw):
    base = dict(
        hypothesis="harness smoke", strategy="four_layer", params={},
        stocks=("AAA", "BBB"),
        is_start=date(2019, 11, 1), is_end=date(2020, 1, 14),
    )
    base.update(kw)
    return RunConfig(**base)


def test_run_is_returns_all_metric_keys() -> None:
    m = run_is(_cfg(), loader=_synthetic_loader)
    for k in ("cagr", "sharpe", "slippage_sharpe", "struct1_pct", "churn_pct",
              "avg_hold", "trades", "maxdd", "bars"):
        assert k in m, f"missing metric {k}"
    assert m["bars"] > 0


def test_run_and_judge_produces_ledger_record() -> None:
    cfg = _cfg(hypothesis="does v3 relax help?")
    rec = run_and_judge(cfg, loader=_synthetic_loader)
    assert rec["run_id"] == cfg.run_id
    assert rec["hypothesis"] == "does v3 relax help?"
    assert rec["strategy"] == "four_layer"
    assert rec["window"] == ["2019-11-01", "2020-01-14"]
    assert rec["gate_status"] in ("PASS", "FAIL", "INCOMPLETE")
    assert "cagr" in rec["metrics"]
    assert "GATE:" in rec["gate_summary"]


def test_run_is_empty_when_no_window_data() -> None:
    # window entirely before any data → no bars
    m = run_is(_cfg(is_start=date(2010, 1, 1), is_end=date(2010, 6, 1)), loader=_synthetic_loader)
    assert m["trades"] == 0


def test_run_is_returns_series_aligns_with_metrics() -> None:
    cfg = _cfg()
    returns = run_is_returns(cfg, loader=_synthetic_loader)
    metrics = run_is(cfg, loader=_synthetic_loader)
    assert isinstance(returns, pd.Series)
    assert len(returns) > 0
    # the returns series is exactly the one the metrics are derived from
    assert len(returns) == metrics["bars"]


def test_run_is_returns_empty_when_no_window_data() -> None:
    returns = run_is_returns(
        _cfg(is_start=date(2010, 1, 1), is_end=date(2010, 6, 1)), loader=_synthetic_loader
    )
    assert isinstance(returns, pd.Series)
    assert returns.empty


def test_run_and_judge_with_returns_single_pass() -> None:
    cfg = _cfg(hypothesis="one pass")
    rec, returns = run_and_judge_with_returns(cfg, loader=_synthetic_loader)
    # record identical in shape to run_and_judge
    plain = run_and_judge(cfg, loader=_synthetic_loader)
    assert rec["run_id"] == plain["run_id"] == cfg.run_id
    assert rec["gate_status"] == plain["gate_status"]
    # returns aligns with the record's bar count
    assert isinstance(returns, pd.Series)
    assert len(returns) == rec["metrics"]["bars"]


# ---- S4: trades + equity/drawdown + persist sidecar ---------------------

def test_run_is_trades_shape() -> None:
    trades = run_is_trades(_cfg(), loader=_synthetic_loader)
    assert isinstance(trades, list)
    # closed-trade count must match the metric the gate reads
    assert len(trades) == run_is(_cfg(), loader=_synthetic_loader)["closed"]
    if trades:
        assert {"ret", "hold", "entry_structure"} <= set(trades[0])


def test_equity_drawdown_from_returns() -> None:
    returns = run_is_returns(_cfg(), loader=_synthetic_loader)
    equity, drawdown = equity_drawdown(returns)
    assert len(equity) == len(drawdown) == len(returns)
    assert all(d <= 1e-9 for d in drawdown)  # drawdown is <= 0
    assert all(isinstance(x, float) for x in equity)


def test_equity_drawdown_empty() -> None:
    assert equity_drawdown(pd.Series(dtype=float)) == ([], [])


def test_run_and_judge_persist_writes_sidecar(tmp_path) -> None:
    cfg = _cfg(hypothesis="persist series")
    rec = run_and_judge_persist(cfg, loader=_synthetic_loader, series_dir=tmp_path)
    # record is the same shape as run_and_judge (heavy series go to the sidecar)
    assert rec["run_id"] == cfg.run_id
    assert "equity" not in rec  # ledger line stays lean
    series = read_series(cfg.run_id, series_dir=tmp_path)
    assert series is not None
    assert len(series["equity"]) == rec["metrics"]["bars"]
    assert isinstance(series["trades"], list)
