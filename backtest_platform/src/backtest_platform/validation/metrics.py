"""Performance metrics — A/B/C/E taxonomy (pure functions, no IO).

Self-contained implementation of the return / risk / risk-adjusted / trade-quality
metrics defined in ``dev_docs/18_reference_architecture_and_metrics.md`` §4. Every
function is a pure transform of ``daily_returns: pd.Series`` (or, for E 类, a
``trades: list[dict]``) and degrades gracefully: empty input or a degenerate
denominator (zero variance, no drawdown, no loss leg) returns ``0.0`` rather than
raising or leaking ``nan``/``inf`` — a degenerate run must never crash the gate
pipeline that consumes these numbers.

Conventions
-----------
- Annualization base ``ANNUALIZATION = 252`` (TW trading days, §4 单位约定).
- Standard deviations use the population estimator (``ddof=0``), matching
  quantstats and the Sharpe (1966) / Sortino (1994) ratio definitions in §4.
- ``risk_free`` is supplied as an **annual** rate and converted to a per-period
  drag of ``risk_free / 252`` before subtracting from each daily return.

References (see §4 of the reference doc for the full taxonomy + citations)
-------------------------------------------------------------------------
- Sharpe, W. F. (1966). *Mutual Fund Performance*. Journal of Business.
- Sortino, F. & Price, L. (1994). *Performance Measurement in a Downside Risk
  Framework*. Journal of Investing.
- Young, T. W. (1991). *Calmar Ratio: A Smoother Tool*. Futures.
- Martin, P. & McCann, B. (1989). *The Investor's Guide to Fidelity Funds*
  (Ulcer Index).
- Kelly, J. L. (1956). *A New Interpretation of Information Rate*. Bell System
  Technical Journal.
- CFA Institute GIPS Standards (Total Return / CAGR, time-weighted return).
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd

ANNUALIZATION: int = 252


def _clean(daily_returns: pd.Series) -> np.ndarray:
    """Drop NaNs and return a float ndarray view of the daily returns."""
    if daily_returns is None or len(daily_returns) == 0:
        return np.asarray([], dtype=float)
    arr = pd.Series(daily_returns, dtype=float).to_numpy()
    return arr[~np.isnan(arr)]


def _pnls(trades: Sequence[dict[str, Any]], key: str = "pnl") -> np.ndarray:
    """Extract a float ndarray of per-trade PnL from a trades list."""
    if not trades:
        return np.asarray([], dtype=float)
    return np.asarray([float(t[key]) for t in trades], dtype=float)


# ---------------------------------------------------------------------------
# A 类 — return
# ---------------------------------------------------------------------------

def total_return(daily_returns: pd.Series) -> float:
    r"""Cumulative (time-weighted) total return over the whole series.

    Formula (§4 A 类, CFA GIPS time-weighted return):
        ``total_return = prod(1 + r_t) - 1``

    Empty series → 0.0.
    """
    r = _clean(daily_returns)
    if r.size == 0:
        return 0.0
    return float(np.prod(1.0 + r) - 1.0)


def cagr(daily_returns: pd.Series, periods_per_year: int = ANNUALIZATION) -> float:
    r"""Compound Annual Growth Rate.

    Formula (§4 A 类, CFA GIPS):
        ``cagr = (1 + total_return)^(252 / N) - 1``
    where ``N`` is the number of observed periods.

    Empty series → 0.0. If the compounded equity is ≤ 0 (total loss), returns
    -1.0 (a 100% annualized loss) instead of producing a complex/nan power.
    """
    r = _clean(daily_returns)
    n = r.size
    if n == 0:
        return 0.0
    growth = 1.0 + total_return(daily_returns)
    if growth <= 0.0:
        return -1.0
    return float(growth ** (periods_per_year / n) - 1.0)


# ---------------------------------------------------------------------------
# B 类 — risk
# ---------------------------------------------------------------------------

def _drawdown_series(daily_returns: pd.Series) -> np.ndarray:
    """Per-period drawdown ``(peak - equity) / peak`` from a cumprod equity curve."""
    r = _clean(daily_returns)
    if r.size == 0:
        return np.asarray([], dtype=float)
    equity = np.cumprod(1.0 + r)
    peak = np.maximum.accumulate(equity)
    return (peak - equity) / peak


def max_drawdown(daily_returns: pd.Series) -> float:
    r"""Maximum drawdown of the cumprod equity curve, as a positive fraction.

    Formula (§4 B 类, quantstats convention):
        ``MDD = max_t ( (peak_t - equity_t) / peak_t )``
    where ``equity = cumprod(1 + r)`` and ``peak = running max(equity)``.

    Empty / monotonic-up series → 0.0.
    """
    dd = _drawdown_series(daily_returns)
    if dd.size == 0:
        return 0.0
    return float(dd.max())


def ulcer_index(daily_returns: pd.Series) -> float:
    r"""Ulcer Index — RMS of the drawdown series (depth + duration penalty).

    Formula (§4 B 类, Martin & McCann 1989):
        ``UI = sqrt( mean( drawdown_t^2 ) )``
    with ``drawdown_t`` the per-period drawdown fraction.

    Empty / no-drawdown series → 0.0.
    """
    dd = _drawdown_series(daily_returns)
    if dd.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(dd**2)))


def downside_deviation(daily_returns: pd.Series, mar: float = 0.0) -> float:
    r"""Downside deviation below a Minimum Acceptable Return (MAR, default 0).

    Formula (§4 B 类, Sortino & Price 1994 — full-length denominator):
        ``DD = sqrt( mean( min(r_t - MAR, 0)^2 ) )``
    Negative deviations are squared and averaged over the **full** sample length
    (not only the count of downside periods), which is the convention pairing
    with the Sortino ratio below.

    Empty series → 0.0. No returns below MAR → 0.0.
    """
    r = _clean(daily_returns)
    if r.size == 0:
        return 0.0
    downside = np.minimum(r - mar, 0.0)
    return float(np.sqrt(np.mean(downside**2)))


# ---------------------------------------------------------------------------
# C 类 — risk-adjusted
# ---------------------------------------------------------------------------

def sharpe(
    daily_returns: pd.Series,
    risk_free: float = 0.0,
    periods_per_year: int = ANNUALIZATION,
) -> float:
    r"""Annualized Sharpe ratio.

    Formula (§4 C 类, Sharpe 1966):
        ``sharpe = mean(r - r_f) / std(r - r_f) * sqrt(252)``
    with ``std`` the population std (``ddof=0``) and ``r_f`` the per-period risk
    free rate (``risk_free / 252``).

    Empty series or zero variance → 0.0 (no divide-by-zero).
    """
    r = _clean(daily_returns)
    if r.size == 0:
        return 0.0
    excess = r - (risk_free / periods_per_year)
    sd = excess.std(ddof=0)
    if sd == 0.0:
        return 0.0
    return float(excess.mean() / sd * np.sqrt(periods_per_year))


def sortino(
    daily_returns: pd.Series,
    risk_free: float = 0.0,
    periods_per_year: int = ANNUALIZATION,
) -> float:
    r"""Annualized Sortino ratio (downside-risk-adjusted).

    Formula (§4 C 类, Sortino & Price 1994):
        ``sortino = mean(r - r_f) / downside_deviation(r, MAR=r_f) * sqrt(252)``
    Downside deviation uses MAR = the per-period risk free rate.

    Empty series or no downside risk → 0.0 (no divide-by-zero).
    """
    r = _clean(daily_returns)
    if r.size == 0:
        return 0.0
    rf_period = risk_free / periods_per_year
    dd = downside_deviation(daily_returns, mar=rf_period)
    if dd == 0.0:
        return 0.0
    excess_mean = (r - rf_period).mean()
    return float(excess_mean / dd * np.sqrt(periods_per_year))


def calmar(daily_returns: pd.Series, periods_per_year: int = ANNUALIZATION) -> float:
    r"""Calmar ratio — CAGR per unit of maximum drawdown.

    Formula (§4 C 类, Young 1991):
        ``calmar = CAGR / |MDD|``

    Empty series or zero drawdown → 0.0 (no divide-by-zero / inf).
    """
    r = _clean(daily_returns)
    if r.size == 0:
        return 0.0
    mdd = max_drawdown(daily_returns)
    if mdd == 0.0:
        return 0.0
    return float(cagr(daily_returns, periods_per_year) / abs(mdd))


# ---------------------------------------------------------------------------
# E 类 — trade quality
# ---------------------------------------------------------------------------

def win_rate(trades: Sequence[dict[str, Any]], pnl_key: str = "pnl") -> float:
    r"""Fraction of trades with positive PnL.

    Formula (§4 E 类):
        ``win_rate = #{pnl > 0} / #trades``

    Empty trade list → 0.0.
    """
    pnls = _pnls(trades, pnl_key)
    if pnls.size == 0:
        return 0.0
    return float(np.count_nonzero(pnls > 0) / pnls.size)


def profit_factor(trades: Sequence[dict[str, Any]], pnl_key: str = "pnl") -> float:
    r"""Gross profit divided by gross loss.

    Formula (§4 E 类):
        ``profit_factor = sum(pnl[pnl>0]) / |sum(pnl[pnl<0])|``

    Empty list or no losing trades → 0.0 (no inf).
    """
    pnls = _pnls(trades, pnl_key)
    if pnls.size == 0:
        return 0.0
    gross_loss = float(np.abs(pnls[pnls < 0].sum()))
    if gross_loss == 0.0:
        return 0.0
    return float(pnls[pnls > 0].sum() / gross_loss)


def avg_hold(trades: Sequence[dict[str, Any]], hold_key: str = "hold_days") -> float:
    r"""Average holding period across trades.

    Formula (§4 E 类, supporting trade-quality stat):
        ``avg_hold = mean(hold_days_i)``

    Empty list → 0.0.
    """
    if not trades:
        return 0.0
    holds = np.asarray([float(t[hold_key]) for t in trades], dtype=float)
    if holds.size == 0:
        return 0.0
    return float(holds.mean())


def kelly_fraction(trades: Sequence[dict[str, Any]], pnl_key: str = "pnl") -> float:
    r"""Kelly optimal capital fraction estimated from realized trades.

    Formula (§4 E 类, Kelly 1956):
        ``f* = (p * b - q) / b``
    where ``p`` = win rate, ``q = 1 - p``, and ``b`` = payoff odds estimated as
    ``mean(win_pnl) / |mean(loss_pnl)|``.

    Empty list, no winners, or no losers (cannot estimate odds ``b``) → 0.0.
    """
    pnls = _pnls(trades, pnl_key)
    if pnls.size == 0:
        return 0.0
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    if wins.size == 0 or losses.size == 0:
        return 0.0
    avg_loss = float(np.abs(losses.mean()))
    if avg_loss == 0.0:
        return 0.0
    b = float(wins.mean()) / avg_loss
    if b == 0.0:
        return 0.0
    p = wins.size / pnls.size
    q = 1.0 - p
    return float((p * b - q) / b)
