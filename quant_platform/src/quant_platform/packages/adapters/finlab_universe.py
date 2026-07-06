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
from pathlib import Path

import pandas as pd

_DAILY_BARS_PREFIX = "daily_bars__"
_PARQUET_SUFFIX = ".parquet"


def cached_universe_symbols(cache_dir: str | Path) -> list[str]:
    """Sorted stock ids already ingested into ``cache_dir`` (empty if dir absent).

    Reads the ``daily_bars__<sid>.parquet`` filenames only — the cache's existence
    *is* the survivorship-clean evidence a strategy's ``research_config`` keys its
    TRUTH_GATE declaration off (ADR-032). Never raises on a missing directory: an
    absent cache is a legitimate "not built yet" state, not an error.
    """
    root = Path(cache_dir)
    if not root.is_dir():
        return []
    return sorted(
        p.name[len(_DAILY_BARS_PREFIX):-len(_PARQUET_SUFFIX)]
        for p in root.glob(f"{_DAILY_BARS_PREFIX}*{_PARQUET_SUFFIX}")
    )


def _asof(wide: pd.DataFrame, ts: pd.Timestamp) -> pd.Series:
    """Last valid value on/before ``ts`` per column (NaN if none) — no look-ahead."""
    hist = wide.loc[:ts]
    if hist.empty:
        return pd.Series(index=wide.columns, dtype="float64")
    return hist.ffill().iloc[-1]


def ineligible_asof(exclude_frames: Sequence[pd.DataFrame], ts: pd.Timestamp) -> set[str]:
    """Symbols flagged *truthy as-of ``ts``* in any eligibility frame (no look-ahead).

    Each frame is a FinLab wide ``date × stock`` status frame where a truthy value
    means "excluded on that date" (verified live 2026-07-05):

    * ``change_transaction:變更交易`` — ``Float64``, ``1.0`` = 變更交易（含全額交割）;
    * ``esb_attention_disposal:處置有價證券`` / ``:注意有價證券`` — ``bool``, ``True``
      during the disposal / attention window.

    We take the last valid row on/before ``ts`` (``_asof`` → strictly no look-ahead)
    and collect every column whose value is truthy. ``1.0`` and ``True`` both count;
    ``0.0`` / ``False`` / NaN do not. An empty ``exclude_frames`` yields an empty set
    (the eligibility layer is fully opt-in — see ADR-007 Slice 3)."""
    excluded: set[str] = set()
    for frame in exclude_frames:
        if frame is None or frame.empty:
            continue
        row = _asof(frame, ts)
        for stock, value in row.items():
            if pd.notna(value) and bool(value):
                excluded.add(str(stock))
    return excluded


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
    exclude_frames: Sequence[pd.DataFrame] = (),
) -> list[str]:
    """Return the survivorship-clean factor universe (sorted unique stock ids).

    At each rebalance date: keep names *alive* (a valid close within the trailing
    ``alive_window_days``) whose trailing-``turnover_window`` mean turnover clears
    ``min_turnover``; drop names *ineligible* as-of that date (``exclude_frames`` —
    全額交割/處置/注意, ADR-007 Slice 3); rank the survivors by as-of market cap
    (desc) and take the top ``top_n``. Union the per-date picks → delisted names are
    retained for the quarters they were live.

    Eligibility is applied *per rebalance date* (not globally): a name disposed in
    2018Q1 but clean in 2020Q3 is correctly excluded only for the 2018Q1 pick — this
    is exactly the point-in-time honesty the survivorship union already guarantees.
    """
    amt = turnover.rolling(turnover_window, min_periods=max(5, turnover_window // 4)).mean()
    selected: set[str] = set()

    for d in rebalance_dates:
        ts = pd.Timestamp(d)
        window = close.loc[ts - pd.Timedelta(days=alive_window_days):ts]
        alive = window.notna().any() if not window.empty else pd.Series(False, index=close.columns)

        mv_asof = _asof(market_value, ts)
        amt_asof = _asof(amt, ts)
        ineligible = ineligible_asof(exclude_frames, ts)

        candidates = [
            s for s in close.columns
            if bool(alive.get(s, False))
            and s not in ineligible
            and float(amt_asof.get(s, 0.0) or 0.0) >= min_turnover
            and pd.notna(mv_asof.get(s, float("nan")))
        ]
        ranked = sorted(candidates, key=lambda s: (-float(mv_asof[s]), s))[:top_n]
        selected.update(ranked)

    return sorted(selected)
