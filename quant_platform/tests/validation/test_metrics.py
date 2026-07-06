"""Tests for validation/metrics.py — A/B/C/E performance metrics.

TDD: each metric is validated against a hand-computed small case (values
derived independently in a scratch session, see commit body) plus boundary
cases (empty series, zero-variance series) that must return 0.0 — never raise,
never produce nan/inf — so a degenerate run cannot crash the gate pipeline.

Annualization base = 252 (TW trading days, per dev_docs/18 §4 单位约定).
Standard deviations use the population convention (ddof=0), matching quantstats
and the López de Prado / Sharpe (1966) ratio definitions referenced in §4.
"""
from __future__ import annotations

import math

import pandas as pd
import pytest

from quant_platform.services.research_validation.validation.metrics import (
    avg_hold,
    cagr,
    calmar,
    downside_deviation,
    kelly_fraction,
    max_drawdown,
    profit_factor,
    sharpe,
    sortino,
    total_return,
    ulcer_index,
    win_rate,
)

# ---------------------------------------------------------------------------
# Shared fixtures (hand-computed ground truth)
# ---------------------------------------------------------------------------

# A 5-day return series with independently hand-computed statistics.
RETS = pd.Series([0.01, -0.02, 0.03, 0.00, 0.015])
# mean = 0.007, ddof=0 std = 0.01661324772583615
# sharpe (ddof=0) = 0.007 / 0.01661324772583615 * sqrt(252) = 6.688731601341364
# downside dev (sqrt(mean(min(r,0)^2))) = 0.00894427190999916
# sortino = 0.007 / 0.00894427190999916 * sqrt(252) = 12.423767544509193
# total_return = prod(1+r) - 1 = 0.034786409999999934

# Equity curve 100 -> 120 -> 90 -> 110 -> 80 expressed as daily returns.
# cumprod(1+r) = [1.2, 0.9, 1.1, 0.8]; drawdown series = [0, .25, .0833.., .3333..]
DD_RETS = pd.Series([0.20, -0.25, 0.22222222222222232, -0.2727272727272727])

TRADES = [
    {"pnl": 100.0, "hold_days": 5},
    {"pnl": -50.0, "hold_days": 3},
    {"pnl": 200.0, "hold_days": 10},
    {"pnl": -30.0, "hold_days": 2},
    {"pnl": 80.0, "hold_days": 4},
]


# ---------------------------------------------------------------------------
# A 类 — return
# ---------------------------------------------------------------------------

def test_total_return_handcomputed() -> None:
    assert total_return(RETS) == pytest.approx(0.034786409999999934, abs=1e-12)


def test_total_return_empty_is_zero() -> None:
    assert total_return(pd.Series([], dtype=float)) == 0.0


def test_cagr_handcomputed() -> None:
    # total_return for DD_RETS = -0.2 over N=4 days; (1-0.2)^(252/4)-1
    expected = (1 - 0.19999999999999996) ** (252 / 4) - 1
    assert cagr(DD_RETS) == pytest.approx(expected, rel=1e-9)


def test_cagr_positive_compounding() -> None:
    # 1% per day for 252 days annualizes to (1.01^252 - 1).
    r = pd.Series([0.01] * 252)
    expected = 1.01**252 - 1
    assert cagr(r) == pytest.approx(expected, rel=1e-9)


def test_cagr_empty_is_zero() -> None:
    assert cagr(pd.Series([], dtype=float)) == 0.0


# ---------------------------------------------------------------------------
# B 类 — risk
# ---------------------------------------------------------------------------

def test_max_drawdown_known_equity() -> None:
    # peak 1.2 -> trough 0.8 => (1.2-0.8)/1.2 = 1/3
    assert max_drawdown(DD_RETS) == pytest.approx(1 / 3, abs=1e-12)


def test_max_drawdown_monotonic_up_is_zero() -> None:
    assert max_drawdown(pd.Series([0.01, 0.02, 0.005])) == 0.0


def test_max_drawdown_empty_is_zero() -> None:
    assert max_drawdown(pd.Series([], dtype=float)) == 0.0


def test_ulcer_index_handcomputed() -> None:
    # dd series [0, .25, .0833.., .3333..]; sqrt(mean(dd^2)) = 0.21245914639969934
    assert ulcer_index(DD_RETS) == pytest.approx(0.21245914639969934, abs=1e-9)


def test_ulcer_index_no_drawdown_is_zero() -> None:
    assert ulcer_index(pd.Series([0.01, 0.01, 0.01])) == 0.0


def test_downside_deviation_handcomputed() -> None:
    assert downside_deviation(RETS) == pytest.approx(0.00894427190999916, abs=1e-12)


def test_downside_deviation_all_positive_is_zero() -> None:
    assert downside_deviation(pd.Series([0.01, 0.02, 0.03])) == 0.0


def test_downside_deviation_empty_is_zero() -> None:
    assert downside_deviation(pd.Series([], dtype=float)) == 0.0


# ---------------------------------------------------------------------------
# C 类 — risk-adjusted
# ---------------------------------------------------------------------------

def test_sharpe_handcomputed() -> None:
    assert sharpe(RETS) == pytest.approx(6.688731601341364, abs=1e-9)


def test_sharpe_zero_std_is_zero() -> None:
    # constant series => std 0 => guard returns 0, must not divide-by-zero.
    assert sharpe(pd.Series([0.01, 0.01, 0.01])) == 0.0


def test_sharpe_empty_is_zero() -> None:
    assert sharpe(pd.Series([], dtype=float)) == 0.0


def test_sharpe_risk_free_shifts_mean() -> None:
    # With rf equal to the daily mean, excess mean is 0 => sharpe 0.
    rf_daily = RETS.mean()
    assert sharpe(RETS, risk_free=rf_daily * 252) == pytest.approx(0.0, abs=1e-12)


def test_sortino_handcomputed() -> None:
    assert sortino(RETS) == pytest.approx(12.423767544509193, abs=1e-9)


def test_sortino_no_downside_is_zero() -> None:
    # No returns below MAR=0 => downside dev 0 => guard returns 0.
    assert sortino(pd.Series([0.01, 0.02, 0.03])) == 0.0


def test_sortino_empty_is_zero() -> None:
    assert sortino(pd.Series([], dtype=float)) == 0.0


def test_calmar_handcomputed() -> None:
    c = cagr(DD_RETS)
    mdd = max_drawdown(DD_RETS)
    assert calmar(DD_RETS) == pytest.approx(c / abs(mdd), rel=1e-9)


def test_calmar_zero_mdd_is_zero() -> None:
    # No drawdown => |MDD| 0 => guard returns 0 (avoid inf).
    assert calmar(pd.Series([0.01, 0.02, 0.03])) == 0.0


def test_calmar_empty_is_zero() -> None:
    assert calmar(pd.Series([], dtype=float)) == 0.0


# ---------------------------------------------------------------------------
# E 类 — trade quality
# ---------------------------------------------------------------------------

def test_win_rate_handcomputed() -> None:
    assert win_rate(TRADES) == pytest.approx(0.6, abs=1e-12)


def test_win_rate_empty_is_zero() -> None:
    assert win_rate([]) == 0.0


def test_profit_factor_handcomputed() -> None:
    # wins sum 380, losses abs sum 80 => 4.75
    assert profit_factor(TRADES) == pytest.approx(4.75, abs=1e-12)


def test_profit_factor_no_losses_is_zero() -> None:
    # All winners => denominator 0 => guard returns 0 (avoid inf).
    assert profit_factor([{"pnl": 10.0}, {"pnl": 5.0}]) == 0.0


def test_profit_factor_empty_is_zero() -> None:
    assert profit_factor([]) == 0.0


def test_avg_hold_handcomputed() -> None:
    # (5+3+10+2+4)/5 = 4.8
    assert avg_hold(TRADES) == pytest.approx(4.8, abs=1e-12)


def test_avg_hold_empty_is_zero() -> None:
    assert avg_hold([]) == 0.0


def test_kelly_fraction_handcomputed() -> None:
    # p=0.6, b=avg_win/avg_loss=126.6667/40=3.16667 => (0.6*b-0.4)/b = 0.47368421
    assert kelly_fraction(TRADES) == pytest.approx(0.47368421052631576, abs=1e-9)


def test_kelly_fraction_no_losses_is_zero() -> None:
    # Cannot compute odds b without a loss leg => guard returns 0.
    assert kelly_fraction([{"pnl": 10.0}, {"pnl": 5.0}]) == 0.0


def test_kelly_fraction_empty_is_zero() -> None:
    assert kelly_fraction([]) == 0.0


# ---------------------------------------------------------------------------
# Robustness: no nan / inf leaks anywhere on degenerate input
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "fn",
    [total_return, cagr, max_drawdown, ulcer_index, downside_deviation, sharpe, sortino, calmar],
)
def test_series_metrics_finite_on_empty(fn) -> None:
    out = fn(pd.Series([], dtype=float))
    assert math.isfinite(out)


@pytest.mark.parametrize("fn", [win_rate, profit_factor, avg_hold, kelly_fraction])
def test_trade_metrics_finite_on_empty(fn) -> None:
    out = fn([])
    assert math.isfinite(out)
