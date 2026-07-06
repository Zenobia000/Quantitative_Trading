"""research.runners — the three built-in strategies behind the unified contract.

Two things matter here:
1. Each strategy resolves via ``get_strategy(name)`` and returns a gate-ready
   ``StrategyRun`` from the same per-stock loader (the platform-agnostic seam).
2. Routing four-layer through the runner did NOT change its numbers — the runner
   output must match the legacy ``is_harness.run_is`` path bit-for-bit (the
   de-specialization is behaviour-preserving).
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

# ensure the built-ins are registered (import side effect)
import quant_platform.services.research_validation.runners  # noqa: F401
from quant_platform.packages.application.is_harness import run_is
from quant_platform.packages.domain.run_config import RunConfig
from quant_platform.services.research_validation.strategies.inst_flow.strategy import InstFlowConfig
from quant_platform.services.research_validation.strategies.momentum.strategy import MomentumConfig
from quant_platform.services.research_validation.strategies.protocol import StrategyRun, get_strategy

_START, _END = date(2019, 11, 1), date(2020, 1, 14)


def _loader(sid: str) -> pd.DataFrame:
    """Per-stock merged frame; trend slope varies by symbol so cross-sectional
    strategies have something to rank (A strongest … E weakest)."""
    n = 260
    slope = {"A": 1.6, "B": 1.2, "C": 0.8, "D": 0.4, "E": 0.1}.get(sid, 1.0)
    dates = pd.date_range("2019-05-01", periods=n, freq="D")
    close = 50 + slope * np.arange(n) * 0.3 + np.sin(np.arange(n) / 4.0) * 1.5
    return pd.DataFrame({
        "trade_date": dates, "stock_id": sid,
        "open": close - 0.3, "high": close * 1.03, "low": close * 0.97,
        "close": close, "volume": 5000,
        "foreign_buy": 120, "trust_buy": 60, "dealer_buy": 10,
        "top_broker_buy": 90, "key_broker_buy": 50, "gov_broker_buy": 5, "geo_broker_buy": 5,
        "day_trade_volume": 500, "margin_offset_volume": 100,
    })


def test_four_layer_runner_matches_legacy_run_is():
    """De-specialization regression: runner path == is_harness path, same numbers."""
    stocks = ("AAA", "BBB")
    cfg = RunConfig(
        hypothesis="runner==harness", strategy="four_layer", params={}, stocks=stocks,
        is_start=_START, is_end=_END,
    )
    legacy = run_is(cfg, loader=_loader)
    four_layer = get_strategy("four_layer")
    run = four_layer.run(
        list(stocks), _START, _END, four_layer.config_model(), _loader
    )
    assert isinstance(run, StrategyRun)
    assert run.metrics["bars"] == legacy["bars"]
    assert run.metrics["cagr"] == pytest.approx(legacy["cagr"])
    assert run.metrics["sharpe"] == pytest.approx(legacy["sharpe"])
    assert run.metrics["trades"] == legacy["trades"]


def test_momentum_runner_runs_via_registry():
    # lookback_days=60 so the ~180 pre-window bars in _loader suffice for a signal
    run = get_strategy("momentum").run(
        ["A", "B", "C", "D", "E"], _START, _END,
        MomentumConfig(lookback_days=60, top_fraction=0.4), _loader,
    )
    assert isinstance(run, StrategyRun)
    for k in ("cagr", "sharpe", "slippage_sharpe", "maxdd", "n_rebalances"):
        assert k in run.metrics
    assert run.metrics["bars"] > 0


def test_inst_flow_runner_runs_via_registry():
    run = get_strategy("inst_flow").run(
        ["A", "B", "C", "D", "E"], _START, _END, InstFlowConfig(top_fraction=0.4), _loader
    )
    assert isinstance(run, StrategyRun)
    for k in ("cagr", "sharpe", "slippage_sharpe", "maxdd"):
        assert k in run.metrics


def test_empty_universe_returns_empty_run():
    run = get_strategy("momentum").run([], _START, _END, MomentumConfig(), _loader)
    assert run.metrics["bars"] == 0
    assert run.returns.empty
