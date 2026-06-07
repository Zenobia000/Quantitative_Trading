"""full_validation_report — end-to-end validation stack over a returns series."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest_platform.validation.full_report import full_validation_report


def _series(mean: float, std: float, n: int = 1260, seed: int = 42) -> pd.Series:
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(mean, std, n))


def test_strong_series_is_deployable():
    rep = full_validation_report(_series(0.001, 0.008), n_iter=200)
    assert rep["metrics"]["sharpe"] > 1.0
    assert rep["metrics"]["cagr"] > 0.18
    assert rep["robustness"]["deflated_sharpe"] > 0.95
    assert rep["deployable"] is True
    # bootstrap CI brackets the point estimate (lo <= point <= hi up to noise)
    ci = rep["robustness"]["sharpe_ci"]
    assert ci["lo"] <= ci["point"] <= ci["hi"]


def test_weak_series_not_deployable():
    rep = full_validation_report(_series(-0.0002, 0.015), n_iter=200)
    assert rep["metrics"]["sharpe"] < 1.0
    assert rep["deployable"] is False
    # the §4.3.1 health table should flag reds on a losing series
    assert rep["health"]["counts"]["red"] > 0


def test_report_structure():
    rep = full_validation_report(_series(0.0005, 0.01), n_iter=100)
    assert {"metrics", "health", "robustness", "bars", "deployable"} <= set(rep)
    assert {"sharpe", "cagr", "dsr"} <= set(rep["bars"])
    assert len(rep["health"]["rows"]) == 13
    assert {"sharpe_ci", "mc_edge_pvalue", "deflated_sharpe", "n_trials"} <= set(rep["robustness"])


def test_deterministic_under_same_seed():
    a = full_validation_report(_series(0.0005, 0.01), n_iter=200, seed=7)
    b = full_validation_report(_series(0.0005, 0.01), n_iter=200, seed=7)
    assert a["robustness"]["mc_edge_pvalue"] == b["robustness"]["mc_edge_pvalue"]
    assert a["robustness"]["sharpe_ci"] == b["robustness"]["sharpe_ci"]


def test_n_trials_deflates_dsr():
    # searching more configs lowers the Deflated Sharpe (selection-bias penalty)
    base = full_validation_report(_series(0.0008, 0.009), n_trials=1, n_iter=100)
    many = full_validation_report(_series(0.0008, 0.009), n_trials=500, n_iter=100)
    assert many["robustness"]["deflated_sharpe"] <= base["robustness"]["deflated_sharpe"]


def test_too_few_observations_raises():
    with pytest.raises(ValueError, match=">= 2 finite"):
        full_validation_report(pd.Series([0.01]))
