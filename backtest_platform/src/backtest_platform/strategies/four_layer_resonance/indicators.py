"""Technical indicators used by the four-layer scoring system.

All functions take pandas Series (price aligned by date) and return Series of the
same length. NaN propagates naturally for warmup periods — caller should drop
NaN rows before evaluating signals.

Match XQ XScript semantics in ``strategy/v2.md`` 2.7 wherever possible:
    - Stochastic(5, 3, 3) — RSV smoothed twice to K/D
    - MACD(weightedClose, 5, 10, 3) — weighted close = (H + L + 2C) / 4
    - RSI: Wilder smoothing
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def weighted_close(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """XQ ``weightedClose`` = (H + L + 2C) / 4."""
    return (high + low + 2 * close) / 4


def stochastic_kd(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    n: int = 5,
    k_period: int = 3,
    d_period: int = 3,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """XQ-style Stochastic. Returns (rsv, k, d).

    K is the EMA-smoothed RSV with alpha = 1/k_period; D is the EMA of K.
    """
    low_n = low.rolling(n, min_periods=n).min()
    high_n = high.rolling(n, min_periods=n).max()
    rsv = (close - low_n) / (high_n - low_n) * 100.0
    k = rsv.ewm(alpha=1 / k_period, adjust=False).mean()
    d = k.ewm(alpha=1 / d_period, adjust=False).mean()
    return rsv, k, d


def macd_weighted(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    fast: int = 5,
    slow: int = 10,
    signal: int = 3,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """XQ ``macd(weightedClose, 5, 10, 3)``. Returns (dif_sl, macd_d, osc_d).

    - ``dif`` = EMA(fast) - EMA(slow) over weighted close
    - ``dif_sl`` (signal line) = EMA(signal) of dif — note the XScript variable
      ``dif_sl`` corresponds to the signal-smoothed DIF, not raw DIF
    - ``macd_d`` mirrors ``dif_sl`` in XScript naming
    - ``osc_d`` = dif - dif_sl (histogram)
    """
    wc = weighted_close(high, low, close)
    ema_fast = wc.ewm(span=fast, adjust=False).mean()
    ema_slow = wc.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dif_sl = dif.ewm(span=signal, adjust=False).mean()
    macd_d = dif_sl
    osc_d = dif - dif_sl
    return dif_sl, macd_d, osc_d


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(50)  # neutral when undefined


def rolling_swing_high(series: pd.Series, period: int) -> pd.Series:
    """Approximation of XQ ``SwingHigh`` — rolling max over the prior ``period`` bars.

    The XScript form ``SwingHigh(body_high, 60, 2, 1, 1)`` finds a pivot in
    the lookback window *excluding* the current bar — otherwise a breakout
    comparison would always be false (today vs today's window max). We use
    ``shift(1)`` to make this explicit so ``close > box_upper`` is a true
    breakout signal.
    """
    return series.rolling(period, min_periods=period).max().shift(1)


def rolling_swing_low(series: pd.Series, period: int) -> pd.Series:
    """Counterpart to :func:`rolling_swing_high` — prior-bar minimum."""
    return series.rolling(period, min_periods=period).min().shift(1)
