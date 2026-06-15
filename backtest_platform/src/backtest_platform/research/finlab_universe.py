"""Survivorship-clean universe selection from FinLab wide frames (② re-validation).

The inst_flow factor trades a fixed cross-sectional universe. To make that universe
**survivorship-clean** we select, at each rebalance date, the liquid large names that
are *alive on that date* (so delisted names are included for the quarters they traded)
and take the **union across all rebalance dates** — delisted names survive in the union
exactly because they were alive/liquid earlier. Strictly no look-ahead: every as-of read
uses only data on or before the rebalance date.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date

import pandas as pd


def _asof(wide: pd.DataFrame, ts: pd.Timestamp) -> pd.Series:
    """Last valid value on/before ``ts`` per column (NaN if none) — no look-ahead."""
    hist = wide.loc[:ts]
    if hist.empty:
        return pd.Series(index=wide.columns, dtype="float64")
    return hist.ffill().iloc[-1]


def select_survivorship_universe(
    market_value: pd.DataFrame,
    close: pd.DataFrame,
    turnover: pd.DataFrame,
    rebalance_dates: Sequence[date],
    *,
    top_n: int,
    min_turnover: float,
    alive_window_days: int = 90,
    turnover_window: int = 20,
) -> list[str]:
    """Return the survivorship-clean factor universe (sorted unique stock ids).

    At each rebalance date: keep names *alive* (a valid close within the trailing
    ``alive_window_days``) whose trailing-``turnover_window`` mean turnover clears
    ``min_turnover``; rank the survivors by as-of market cap (desc) and take the
    top ``top_n``. Union the per-date picks → delisted names are retained for the
    quarters they were live.
    """
    amt = turnover.rolling(turnover_window, min_periods=max(5, turnover_window // 4)).mean()
    selected: set[str] = set()

    for d in rebalance_dates:
        ts = pd.Timestamp(d)
        window = close.loc[ts - pd.Timedelta(days=alive_window_days):ts]
        alive = window.notna().any() if not window.empty else pd.Series(False, index=close.columns)

        mv_asof = _asof(market_value, ts)
        amt_asof = _asof(amt, ts)

        candidates = [
            s for s in close.columns
            if bool(alive.get(s, False))
            and float(amt_asof.get(s, 0.0) or 0.0) >= min_turnover
            and pd.notna(mv_asof.get(s, float("nan")))
        ]
        ranked = sorted(candidates, key=lambda s: (-float(mv_asof[s]), s))[:top_n]
        selected.update(ranked)

    return sorted(selected)
