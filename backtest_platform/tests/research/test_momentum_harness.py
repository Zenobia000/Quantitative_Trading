"""momentum_harness — IS run → gate-ready metrics, via an injected synthetic loader."""
from __future__ import annotations

import numpy as np
import pandas as pd

from backtest_platform.research.momentum_harness import price_panel, run_momentum_is
from backtest_platform.strategies.momentum.strategy import MomentumConfig
from backtest_platform.validation.gate_state import MOMENTUM_GATE, evaluate_gate

_SLOPES = {"UP1": 0.0020, "UP2": 0.0018, "UP3": 0.0016, "DN1": -0.0010, "DN2": -0.0012}


def _loader(sid: str) -> pd.DataFrame:
    dates = pd.bdate_range("2018-01-01", periods=500)
    close = 100 * (1 + _SLOPES.get(sid, 0.0)) ** np.arange(500)
    return pd.DataFrame({"trade_date": dates, "stock_id": sid, "close": close})


def test_price_panel_skips_unloadable():
    def loader(sid):
        if sid == "BAD":
            raise FileNotFoundError(sid)
        return _loader(sid)

    panel = price_panel(["UP1", "BAD", "DN1"], loader=loader)
    assert list(panel.columns) == ["UP1", "DN1"]


def test_run_momentum_is_returns_gate_ready_metrics():
    m = run_momentum_is(list(_SLOPES), "2019-06-01", "2019-12-31",
                        cfg=MomentumConfig(top_fraction=0.4), loader=_loader)
    for key in ("cagr", "sharpe", "slippage_sharpe", "avg_holdings", "n_rebalances", "bars"):
        assert key in m, f"missing {key}"
    assert m["bars"] > 0
    # the metrics dict is judgeable by the momentum gate (no missing-metric INCOMPLETE)
    result = evaluate_gate(m, MOMENTUM_GATE)
    assert result.status.value in ("PASS", "FAIL")  # complete, not INCOMPLETE


def test_run_momentum_is_empty_universe():
    m = run_momentum_is([], "2019-06-01", "2019-12-31", loader=_loader)
    assert m["trades"] == 0 and m["bars"] == 0


def test_slippage_sharpe_not_above_raw():
    m = run_momentum_is(list(_SLOPES), "2019-06-01", "2019-12-31",
                        cfg=MomentumConfig(top_fraction=0.4), loader=_loader)
    # extra slippage can only cost return → slippage Sharpe <= raw Sharpe
    assert m["slippage_sharpe"] <= m["sharpe"] + 1e-9
