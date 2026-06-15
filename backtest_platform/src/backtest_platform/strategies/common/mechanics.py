"""Neutral backtest mechanics shared across strategies.

Rebalance-calendar, vol-targeting and return-cleaning primitives that any
periodically-rebalanced strategy needs. These landed in ``strategies.momentum``
only because momentum was the first strategy implemented; later strategies
(inst_flow, multi_factor) then reached into momentum's *private* helpers, making
a specialized strategy an accidental base layer. Extracting them here lets every
strategy depend on a neutral module instead of on each other (see ADR-026).

Pure functions over price/return panels — no IO, no strategy-specific state.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def clean_returns(prices: pd.DataFrame, max_daily: float) -> pd.DataFrame:
    """Daily returns with inf + >max_daily/day data-error jumps winsorized to NaN."""
    r = prices.pct_change().replace([np.inf, -np.inf], np.nan)
    return r.where(r.abs() <= max_daily)


def rebalance_dates(index: pd.DatetimeIndex, freq: str = "monthly") -> list[pd.Timestamp]:
    """First trading day of each period (month / quarter / half-year) in ``index``.

    Lower frequency = fewer rebalances = less turnover = less transaction-cost drag
    (the lever when cost is the binding constraint).
    """
    s = pd.Series(index, index=index)
    if freq == "quarterly":
        key = [index.year, index.quarter]
    elif freq == "semiannual":
        key = [index.year, (index.month - 1) // 6]
    else:  # monthly
        key = [index.year, index.month]
    return [grp.index[0] for _, grp in s.groupby(key)]


def vol_target(returns: pd.Series, target_annual: float, lookback: int, max_lev: float) -> pd.Series:
    """Scale daily returns toward a target annual vol using *trailing* realized vol.

    ``scale_t = clip(target_daily / realized_vol_{t-1}, max=max_lev)`` — uses only
    information up to ``t-1`` (no look-ahead), and with ``max_lev=1.0`` only ever
    *cuts* exposure (de-risks) when vol spikes — the principled momentum-crash
    control. Warmup (vol not yet estimable) → scale 1.0.
    """
    target_daily = target_annual / np.sqrt(TRADING_DAYS)
    realized = returns.rolling(lookback).std(ddof=0).shift(1)
    scale = (target_daily / realized).clip(upper=max_lev)
    scale = scale.where(realized.notna() & (realized > 0), other=1.0).clip(upper=max_lev)
    return returns * scale
