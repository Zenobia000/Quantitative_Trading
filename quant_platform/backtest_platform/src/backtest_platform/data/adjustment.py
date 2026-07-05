"""Forward price adjustment (前復權) from cash dividends.

FinMind's pre-adjusted endpoint (``taiwan_stock_daily_adj``) is paid-tier only.
The free tier exposes ``taiwan_stock_dividend`` which lets us reconstruct the
forward-adjustment factor:

    For each ex-dividend date ``d`` (sorted descending), the adjustment factor
    applied to every bar with ``trade_date < d`` is::

        factor = (close_before_d - cash_div - stock_value) / close_before_d

    Latest bar's ``adj_factor`` is 1.0; older bars compound down.

Limitations (M1 scope — backlog for M2):
    * Stock dividends (盈餘配股 / 法盈餘配股) handled approximately by treating
      the implied share-count change as a price reduction. For 2330 (cash only)
      this is exact; for stocks with stock dividends the approximation
      under-adjusts share count.
    * Cash capital increases (現金增資) are ignored — rare for our universe.
    * Reverse splits / reduction events (減資) are not handled. Universe filter
      should drop stocks with active 減資 events.
"""
from __future__ import annotations

import warnings
from datetime import date

import numpy as np
import pandas as pd
from loguru import logger


def compute_adj_factor(daily: pd.DataFrame, dividends: pd.DataFrame) -> pd.Series:
    """Return adj_factor Series aligned to ``daily['trade_date']``.

    Multiply raw OHLC by adj_factor to get forward-adjusted OHLC.

    Args:
        daily: DataFrame with at least ``trade_date`` and ``close`` columns,
            sorted ascending by date.
        dividends: FinMind ``taiwan_stock_dividend`` raw frame.
            Empty frame is fine — returns all-ones.
    """
    if daily.empty:
        return pd.Series([], dtype="float64", name="adj_factor")

    daily_sorted = daily.sort_values("trade_date").reset_index(drop=True)
    factor = pd.Series(1.0, index=daily_sorted.index, name="adj_factor")

    if dividends is None or dividends.empty:
        return factor

    events = _extract_ex_dividend_events(dividends, daily_sorted)
    if not events:
        return factor

    # Walk ex-div events from earliest to latest. For each event, every bar
    # strictly BEFORE the ex-div date has its adj_factor scaled down.
    for ev in events:
        pre_close = ev["pre_close"]
        if pre_close <= 0:
            continue
        ratio = (pre_close - ev["cash_div"] - ev["stock_value"]) / pre_close
        if ratio <= 0 or not np.isfinite(ratio):
            logger.warning(
                "skip ex-div on {} (pre_close={}, cash={}, stock_value={}): bad ratio {}",
                ev["date"],
                pre_close,
                ev["cash_div"],
                ev["stock_value"],
                ratio,
            )
            continue
        mask = daily_sorted["trade_date"] < ev["date"]
        factor.loc[mask] *= ratio

    return factor


def _extract_ex_dividend_events(
    dividends: pd.DataFrame, daily_sorted: pd.DataFrame
) -> list[dict]:
    """Build a chronological list of ex-div events with pre-event close prices."""
    events: list[dict] = []
    closes = daily_sorted.set_index("trade_date")["close"]
    daily_dates = list(daily_sorted["trade_date"])

    for _, row in dividends.iterrows():
        ex_date_str = row.get("CashExDividendTradingDate") or row.get("StockExDividendTradingDate")
        if not ex_date_str or pd.isna(ex_date_str) or ex_date_str == "":
            continue
        try:
            ex_date = pd.to_datetime(ex_date_str).date()
        except (ValueError, TypeError):
            continue

        # Only handle ex-div dates within the trading-day range we have, else
        # we can't establish pre-close and downstream adjustment is meaningless.
        if ex_date < daily_dates[0] or ex_date > daily_dates[-1]:
            continue

        pre_close = _find_previous_close(closes, ex_date)
        if pre_close is None:
            continue

        cash_div = float(row.get("CashEarningsDistribution", 0) or 0)
        cash_div += float(row.get("CashStatutorySurplus", 0) or 0)
        stock_div_shares = float(row.get("StockEarningsDistribution", 0) or 0)
        stock_div_shares += float(row.get("StockStatutorySurplus", 0) or 0)
        # Stock dividend impact in price terms ≈ pre_close * stock_shares / 10
        # (per-1000-shares convention in TW). Approximation; see docstring.
        stock_value = pre_close * stock_div_shares / 10.0

        if cash_div + stock_value <= 0:
            continue
        if stock_div_shares > 0:
            warnings.warn(
                f"stock dividend on {ex_date} approximated; verify adjustment manually",
                stacklevel=3,
            )

        events.append(
            {
                "date": ex_date,
                "pre_close": pre_close,
                "cash_div": cash_div,
                "stock_value": stock_value,
            }
        )

    events.sort(key=lambda e: e["date"])
    return events


def _find_previous_close(closes: pd.Series, ex_date: date) -> float | None:
    """Find the last close ON OR BEFORE (ex_date - 1 calendar day).

    Trading-day calendar — walk back through index entries.
    """
    eligible = closes[closes.index < ex_date]
    if eligible.empty:
        return None
    return float(eligible.iloc[-1])


def apply_adjustment(daily: pd.DataFrame, adj_factor: pd.Series) -> pd.DataFrame:
    """Return a copy of ``daily`` with OHLC scaled by adj_factor.

    Adds ``raw_open / raw_high / raw_low / raw_close`` columns for audit
    while overwriting ``open / high / low / close`` with adjusted values.
    """
    out = daily.copy().reset_index(drop=True)
    factor = adj_factor.reset_index(drop=True)
    if len(factor) != len(out):
        raise ValueError(
            f"adj_factor length {len(factor)} != daily length {len(out)}"
        )

    for col in ("open", "high", "low", "close"):
        out[f"raw_{col}"] = out[col]
        out[col] = (out[col] * factor).round(4)
    out["adj_factor"] = factor.values
    return out
