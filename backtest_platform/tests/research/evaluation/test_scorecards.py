"""research.evaluation.scorecards — the five scorecards + not_available honesty."""
from __future__ import annotations

import numpy as np
import pandas as pd

from backtest_platform.research.evaluation.profiles import get_profile
from backtest_platform.research.evaluation.scorecards import CATEGORIES, build_scorecards


def _returns(n=300, seed=1):
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(0.0005, 0.01, n))


_PANEL_METRICS = {"cagr": 0.16, "sharpe": 1.02, "slippage_sharpe": 0.84, "maxdd": 0.27,
                  "trades": 60, "bars": 300, "avg_holdings": 41.2, "avg_turnover": 0.83}


def test_returns_five_scorecards_in_order():
    sc = build_scorecards(_returns(), _PANEL_METRICS, [], get_profile("quick_triage"))
    assert [c["category"] for c in sc] == list(CATEGORIES)


def test_panel_win_rate_is_not_available():
    sc = build_scorecards(_returns(), _PANEL_METRICS, [], get_profile("quick_triage"))
    win = next(c for c in sc if c["category"] == "win_rate")
    assert win["status"] == "not_available"
    assert all(m["status"] == "not_available" for m in win["metrics"])


def test_profitability_alpha_beta_not_available_with_reason():
    sc = build_scorecards(_returns(), _PANEL_METRICS, [], get_profile("quick_triage"))
    prof = next(c for c in sc if c["category"] == "profitability")
    alpha = next(m for m in prof["metrics"] if m["id"] == "alpha")
    assert alpha["status"] == "not_available"
    assert alpha["value"] is None
    assert "benchmark" in alpha["reason"].lower()


def test_risk_var_cvar_not_available():
    sc = build_scorecards(_returns(), _PANEL_METRICS, [], get_profile("quick_triage"))
    risk = next(c for c in sc if c["category"] == "risk")
    ids = {m["id"]: m["status"] for m in risk["metrics"]}
    assert ids["var_95"] == "not_available"
    assert ids["cvar_95"] == "not_available"
    assert ids["max_drawdown"] == "pass"


def test_data_issue_forces_all_not_available():
    sc = build_scorecards(pd.Series(dtype=float), {"bars": 0}, [], get_profile("quick_triage"), data_issue=True)
    assert all(c["status"] == "not_available" for c in sc)
    assert len(sc) == 5


def test_oos_holdout_included_from_truth_extras():
    sc = build_scorecards(_returns(), _PANEL_METRICS, [], get_profile("deployment_strict"),
                          truth_extras={"oos_holdout_sharpe": 0.89})
    ra = next(c for c in sc if c["category"] == "risk_adjusted")
    oos = next(m for m in ra["metrics"] if m["id"] == "oos_holdout_sharpe")
    assert oos["value"] == 0.89
    assert oos["severity"] == "block_deploy"


def test_per_trade_ret_makes_win_rate_partial():
    trades = [{"ret": 0.05, "hold": 5}, {"ret": -0.02, "hold": 3}, {"ret": 0.03, "hold": 4}]
    sc = build_scorecards(_returns(), {**_PANEL_METRICS, "avg_turnover": None}, trades, get_profile("quick_triage"))
    win = next(c for c in sc if c["category"] == "win_rate")
    twr = next(m for m in win["metrics"] if m["id"] == "trade_win_rate")
    assert twr["value"] is not None
    assert 0.0 <= twr["value"] <= 1.0


def test_cost_sensitivity_uses_sharpe_vs_slippage():
    sc = build_scorecards(_returns(), _PANEL_METRICS, [], get_profile("quick_triage"))
    liq = next(c for c in sc if c["category"] == "liquidity")
    cost = next(m for m in liq["metrics"] if m["id"] == "cost_sensitivity")
    assert cost["value"] is not None
    assert abs(cost["value"] - (1.02 - 0.84)) < 1e-9
