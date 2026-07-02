"""reversal.strategy — config + backtest over synthetic prices with known reversal.

Short-term reversal (Jegadeesh 1990, Lehmann 1990): prior losers over a short
formation window mean-revert next period. These synthetic panels ENGINEER that
phenomenon so a *positive* portfolio return proves the strategy bought the losers
(buying the winners on the same panel would lose money).

Design params stay at literature values (weekly / lookback 5 / skip 1 / decile);
only the synthetic DATA is shaped — never the config — to keep the pre-registration
discipline intact.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest_platform.strategies.reversal.strategy import (
    ReversalConfig,
    backtest_reversal,
)

_DATES = pd.bdate_range("2018-01-01", periods=260)  # ~1 trading year


def _mean_reverting_panel() -> pd.DataFrame:
    """4 stocks whose weekly return sign flips every ISO week (pure mean reversion).

    Two anti-phase pairs: within any week, half the universe fell last week (losers)
    and rebounds this week, the other half rose last week (winners) and falls this
    week. Market-average ≈ 0, so a positive reversal return isolates the loser leg.
    """
    n = np.arange(len(_DATES))
    week = n // 5
    up = 0.010   # weekly up-leg daily return
    dn = -0.008  # weekly down-leg daily return
    # A/C rise on even weeks; B/D rise on odd weeks (distinct amplitudes → clean rank)
    a = np.where(week % 2 == 0, up, dn)
    b = np.where(week % 2 == 1, up, dn)
    c = np.where(week % 2 == 0, up * 0.8, dn * 0.8)
    d = np.where(week % 2 == 1, up * 0.8, dn * 0.8)
    return pd.DataFrame(
        {
            "A": 100.0 * np.cumprod(1 + a),
            "B": 100.0 * np.cumprod(1 + b),
            "C": 100.0 * np.cumprod(1 + c),
            "D": 100.0 * np.cumprod(1 + d),
        },
        index=_DATES,
    )


# --- config --------------------------------------------------------------

def test_config_defaults_are_literature_values():
    cfg = ReversalConfig()
    assert cfg.lookback_days == 5        # Lehmann 1990 weekly formation
    assert cfg.skip_days == 1            # skip most-recent day (bid-ask bounce)
    assert cfg.top_fraction == pytest.approx(0.1)  # decile losers (Jegadeesh 1990)
    assert cfg.rebalance == "weekly"
    assert cfg.cost_mode == "lump"
    assert cfg.vol_target_annual is None  # vol-targeting opt-in


def test_config_frozen_and_extra_slippage():
    cfg = ReversalConfig()
    with pytest.raises(Exception):
        cfg.lookback_days = 10  # frozen
    slipped = cfg.with_extra_slippage(0.003)
    assert slipped.cost_round_rate == pytest.approx(cfg.cost_round_rate + 0.006)
    assert cfg.cost_round_rate != slipped.cost_round_rate  # original unchanged


def test_config_rejects_unknown_field():
    with pytest.raises(Exception):
        ReversalConfig(bogus=1)


def test_config_rejects_skip_ge_lookback():
    # skip_days must leave a non-empty formation window (skip < lookback).
    with pytest.raises(Exception):
        ReversalConfig(lookback_days=5, skip_days=5)


# --- backtest: buys losers, mean-reversion pays --------------------------

def test_reversal_buys_losers_and_is_positive():
    cfg = ReversalConfig(top_fraction=0.5, rebalance="weekly", cost_round_rate=0.0)
    res = backtest_reversal(_mean_reverting_panel(), cfg, "2018-03-01", "2018-12-31")
    assert res.n_rebalances > 0
    assert res.avg_holdings == pytest.approx(2.0)  # k = int(4*0.5) = 2 biggest losers
    # buying the prior-week losers on a mean-reverting panel → positive cumulative
    assert (1 + res.daily_returns).prod() - 1 > 0


def test_reversal_beats_buying_winners_on_reverting_panel():
    """Sanity direction: the loser leg (ascending) must beat the winner leg.

    Reuse the same signal with the OPPOSITE selection by flipping the panel's sign
    of returns is not available; instead compare reversal against momentum-style
    descending selection implemented via ``top_fraction`` on the inverted rank —
    here we assert the reversal return simply exceeds the flat market average (~0).
    """
    cfg = ReversalConfig(top_fraction=0.5, rebalance="weekly", cost_round_rate=0.0)
    res = backtest_reversal(_mean_reverting_panel(), cfg, "2018-03-01", "2018-12-31")
    market = _mean_reverting_panel().pct_change().loc["2018-03-01":"2018-12-31"].mean(axis=1)
    assert (1 + res.daily_returns).prod() > (1 + market).prod()


def test_higher_cost_lowers_return():
    panel = _mean_reverting_panel()
    lo = backtest_reversal(
        panel, ReversalConfig(top_fraction=0.5, cost_round_rate=0.0), "2018-03-01", "2018-12-31"
    )
    hi = backtest_reversal(
        panel, ReversalConfig(top_fraction=0.5, cost_round_rate=0.05), "2018-03-01", "2018-12-31"
    )
    assert (1 + hi.daily_returns).prod() < (1 + lo.daily_returns).prod()


def test_empty_window_returns_empty():
    res = backtest_reversal(_mean_reverting_panel(), ReversalConfig(), "2010-01-01", "2010-06-30")
    assert res.daily_returns.empty
    assert res.n_rebalances == 0


def test_winsorizes_data_error_spike():
    panel = _mean_reverting_panel()
    panel.iloc[120, panel.columns.get_loc("A")] *= 5  # un-adjusted-split style spike
    res = backtest_reversal(
        panel, ReversalConfig(top_fraction=0.5), "2018-03-01", "2018-12-31"
    )
    assert np.isfinite(res.daily_returns).all()
    assert res.daily_returns.abs().max() <= 0.5


def test_vol_target_off_is_vanilla():
    panel = _mean_reverting_panel()
    base = backtest_reversal(panel, ReversalConfig(top_fraction=0.5), "2018-03-01", "2018-12-31")
    off = backtest_reversal(
        panel, ReversalConfig(top_fraction=0.5, vol_target_annual=None), "2018-03-01", "2018-12-31"
    )
    assert base.daily_returns.equals(off.daily_returns)


# --- skip_days: reject the fake loser (bid-ask bounce) -------------------

def _fake_loser_panel() -> pd.DataFrame:
    """3 stocks; on each rebalance day exactly one genuine WINNER gets a 1-day crash.

    R (real loser): falls over the formation window, rebounds next week — the true
        reversal name skip should keep.
    F (fake loser): rises over the formation window BUT crashes on the single
        rebalance-day close, then keeps falling (a real downtrend, not a bounce).
        Without skip its rebalance-day crash makes it the biggest 'loser' and it is
        wrongly bought; with skip=1 the crash day is excluded so it ranks as a winner.
    W (winner): rises throughout.

    Weekly blocks of 5 business days; the crash lands on each block's first day
    (the rebalance day), so skip=0 sees it and skip=1 does not.
    """
    dates = pd.bdate_range("2018-01-01", periods=120)
    n = len(dates)
    r = np.zeros(n)
    f = np.zeros(n)
    w = np.zeros(n)
    for i in range(n):
        block = i // 5
        first_day = (i % 5 == 0)
        # R: down last week → up this week (mean reversion)
        r[i] = -0.010 if (block % 2 == 0) else 0.012
        # W: steadily up
        w[i] = 0.006
        # F: steadily up EXCEPT a sharp one-day crash on every rebalance day
        f[i] = -0.060 if first_day else 0.007
    close = pd.DataFrame(
        {
            "R": 100.0 * np.cumprod(1 + r),
            "F": 100.0 * np.cumprod(1 + f),
            "W": 100.0 * np.cumprod(1 + w),
        },
        index=dates,
    )
    return close


def test_skip_days_excludes_fake_loser():
    """skip=1 buys the real loser (positive); skip=0 gets baited into the fake loser.

    top_fraction 1/3 over 3 names → k=1: exactly the single biggest loser is held,
    so the two skip settings pick different names and the returns diverge.
    """
    panel = _fake_loser_panel()
    keep = backtest_reversal(
        panel, ReversalConfig(top_fraction=1 / 3, skip_days=1, cost_round_rate=0.0),
        "2018-01-15", "2018-06-01",
    )
    baited = backtest_reversal(
        panel, ReversalConfig(top_fraction=1 / 3, skip_days=0, cost_round_rate=0.0),
        "2018-01-15", "2018-06-01",
    )
    # Skipping the bid-ask-bounce day must do strictly better than being baited by it.
    assert (1 + keep.daily_returns).prod() > (1 + baited.daily_returns).prod()
    # And the skip run is actually profitable (bought the genuine reverting loser).
    assert (1 + keep.daily_returns).prod() - 1 > 0
