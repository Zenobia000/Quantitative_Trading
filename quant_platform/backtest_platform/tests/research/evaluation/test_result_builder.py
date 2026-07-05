"""research.evaluation.result_builder — verdict mapping, checks, gaps (pure)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from backtest_platform.research.evaluation.models import RunBundle
from backtest_platform.research.evaluation.profiles import get_profile
from backtest_platform.research.evaluation.result_builder import assemble_result


def _returns(n=300, seed=3):
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(0.0006, 0.01, n))


def _bundle(**overrides):
    base = dict(
        metrics={"cagr": 0.16, "sharpe": 1.02, "slippage_sharpe": 0.84, "maxdd": 0.27,
                 "trades": 60, "bars": 300, "avg_holdings": 41.2, "avg_turnover": 0.83},
        returns=_returns(), trades=[], params={"lookback_days": 60}, symbols=["A", "B"],
        window={"is_start": "2015-01-01", "oos_start": "2021-01-01", "is_end": "2024-12-31"},
        n_trials=16, survivorship_clean=True, bundle_ref="data/x",
    )
    base.update(overrides)
    return RunBundle(**base)


def _assemble(bundle, profile="deployment_strict"):
    return assemble_result(get_profile(profile), bundle, strategy="momentum",
                           run_id="abc123", evaluation_id="eval_x", created_at="2026-07-03T00:00:00+08:00")


def test_paper_watch_maps_to_weak_eligible():
    b = _bundle(truth_verdict="PAPER_WATCH", position_size=0.0,
                extras={"dsr": 0.908, "wfa_oos_positive_frac": 1.0, "oos_holdout_sharpe": 0.89, "slippage_sharpe": 0.85})
    r = _assemble(b)
    assert r["verdict"]["label"] == "Weak"
    assert r["verdict"]["truth_verdict"] == "PAPER_WATCH"
    assert r["verdict"]["live_oos_recommendation"] == "eligible"
    assert r["verdict"]["recommendation"]["action"] == "eligible_for_live_oos"
    assert r["sizing"]["position_size"] == 0.0


def test_rejected_maps_to_negative_blocked():
    b = _bundle(truth_verdict="REJECTED", extras={"dsr": 0.5, "slippage_sharpe": -0.1})
    r = _assemble(b)
    assert r["verdict"]["label"] == "Negative"
    assert r["verdict"]["live_oos_recommendation"] == "blocked"


def test_real_maps_to_strong():
    b = _bundle(truth_verdict="REAL", position_size=0.12,
                extras={"dsr": 0.97, "wfa_oos_positive_frac": 1.0, "oos_holdout_sharpe": 1.1, "slippage_sharpe": 1.0})
    r = _assemble(b)
    assert r["verdict"]["label"] == "Strong"
    assert r["verdict"]["live_oos_recommendation"] == "eligible"


def test_data_issue_bundle():
    b = _bundle(returns=pd.Series(dtype=float), metrics={"bars": 0, "trades": 0})
    r = _assemble(b, profile="quick_triage")
    assert r["verdict"]["label"] == "Data Issue"
    assert r["verdict"]["live_oos_recommendation"] == "blocked"
    assert all(sc["status"] == "not_available" for sc in r["scorecards"])


def test_triage_no_truth_verdict_uses_scorecard_health():
    b = _bundle(truth_verdict=None, extras={})
    r = _assemble(b, profile="quick_triage")
    assert r["verdict"]["truth_verdict"] is None
    assert r["verdict"]["label"] in ("Promising", "Weak", "Negative")
    assert r["verdict"]["live_oos_recommendation"] == "not_recommended"


def test_checks_from_profile_gates():
    b = _bundle(truth_verdict="PAPER_WATCH",
                extras={"dsr": 0.908, "wfa_oos_positive_frac": 1.0, "oos_holdout_sharpe": 0.89, "slippage_sharpe": 0.85})
    r = _assemble(b)
    metrics_checked = {c["metric"] for c in r["checks"]}
    assert "survivorship_clean" in metrics_checked
    assert "dsr" in metrics_checked
    # the block_deploy DSR gate fails at 0.908 < 0.95
    dsr_deploy = next(c for c in r["checks"] if c["metric"] == "dsr" and c["threshold"] == 0.95)
    assert dsr_deploy["status"] == "fail"


def test_pbo_gate_not_applicable_for_single_config():
    b = _bundle(truth_verdict="PAPER_WATCH", extras={"dsr": 0.908, "slippage_sharpe": 0.85})
    r = _assemble(b)
    pbo = next((c for c in r["checks"] if c["metric"] == "pbo"), None)
    assert pbo is not None
    assert pbo["status"] == "not_applicable"  # selected_from_grid guard, run_mode single_config


def test_lineage_and_git_sha_gap():
    r = _assemble(_bundle(truth_verdict="PAPER_WATCH", extras={"dsr": 0.9, "slippage_sharpe": 0.8}))
    assert r["lineage"]["config_hash"] == "abc123"
    assert r["lineage"]["git_sha"] is None
    assert r["lineage"]["git_sha_status"] == "not_available"
    gap_fields = {g["field"] for g in r["data_gaps"]}
    assert "lineage.git_sha" in gap_fields


def test_headline_metrics_shape():
    r = _assemble(_bundle(truth_verdict="PAPER_WATCH", extras={"dsr": 0.9, "oos_holdout_sharpe": 0.89, "slippage_sharpe": 0.85}))
    h = r["headline_metrics"]
    for k in ("cagr", "sharpe", "sortino", "calmar", "max_drawdown", "volatility",
              "oos_holdout_sharpe", "dsr", "n_trials", "trades"):
        assert k in h
    assert h["n_trials"] == 16
