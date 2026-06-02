"""run_is / run_and_judge — IS harness logic via an injected synthetic loader
(NOT cache-gated; the real-parquet path is the manual integration step)."""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from backtest_platform.research.is_harness import run_and_judge, run_is
from backtest_platform.research.run_config import RunConfig


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
        hypothesis="harness smoke", preset="v3", stocks=("AAA", "BBB"),
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
    assert rec["preset"] == "v3"
    assert rec["window"] == ["2019-11-01", "2020-01-14"]
    assert rec["gate_status"] in ("PASS", "FAIL", "INCOMPLETE")
    assert "cagr" in rec["metrics"]
    assert "GATE:" in rec["gate_summary"]


def test_run_is_empty_when_no_window_data() -> None:
    # window entirely before any data → no bars
    m = run_is(_cfg(is_start=date(2010, 1, 1), is_end=date(2010, 6, 1)), loader=_synthetic_loader)
    assert m["trades"] == 0
