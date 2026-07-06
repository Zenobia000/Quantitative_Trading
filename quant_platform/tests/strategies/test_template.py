"""strategies._template — the copyable authoring template is a working strategy.

If this passes, an author who copies ``strategies/_template/`` and only swaps the
``backtest_*`` body gets a strategy the platform can call exactly like the others.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

# import side effect registers the built-ins (incl. "template")
import quant_platform.services.research_validation.runners  # noqa: F401
from quant_platform.services.research_validation.strategies._template.strategy import (
    TemplateConfig,
    backtest_template,
)
from quant_platform.services.research_validation.strategies.protocol import StrategyRun, get_strategy

_START, _END = date(2019, 6, 1), date(2019, 12, 31)


def _loader(sid: str) -> pd.DataFrame:
    n = 300
    dates = pd.date_range("2019-01-01", periods=n, freq="D")
    close = 100 * (1.001) ** np.arange(n)  # gentle uptrend
    return pd.DataFrame({
        "trade_date": dates, "stock_id": sid,
        "open": close, "high": close * 1.01, "low": close * 0.99,
        "close": close, "volume": 5000,
        "foreign_buy": 100, "trust_buy": 50, "dealer_buy": 10,
        "top_broker_buy": 80, "key_broker_buy": 40, "gov_broker_buy": 5, "geo_broker_buy": 5,
        "day_trade_volume": 500, "margin_offset_volume": 100,
    })


def test_template_is_registered_and_runs_via_registry():
    run = get_strategy("template").run(
        ["A", "B", "C"], _START, _END, TemplateConfig(), _loader
    )
    assert isinstance(run, StrategyRun)
    assert run.metrics["bars"] > 0
    # buy-and-hold of an up-trending universe → positive cumulative return
    assert (1 + run.returns).prod() - 1 > 0


def test_template_pure_backtest_empty_window():
    prices = pd.DataFrame({"A": [100.0, 101.0]}, index=pd.date_range("2019-01-01", periods=2))
    res = backtest_template(prices, TemplateConfig(), "2010-01-01", "2010-06-30")
    assert res.daily_returns.empty
    assert res.n_rebalances == 0
