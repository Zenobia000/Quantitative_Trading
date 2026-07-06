"""Four-layer resonance scoring — pure function.

Mirrors ``strategy/archive/v2.md`` 2.3 and the XScript in 2.7. This function is the
single implementation shared by the rqalpha engine and vectorbt parameter
sweeps — both must call ``compute_scores`` for v2.md 5.3.3 signal reproduction
to hold.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quant_platform.services.research_validation.strategies.four_layer_resonance.config import StrategyConfig
from .indicators import (
    macd_weighted,
    rolling_swing_high,
    rolling_swing_low,
    rsi,
    stochastic_kd,
)

REQUIRED_COLUMNS: tuple[str, ...] = (
    "open",
    "high",
    "low",
    "close",
    "volume",
    "foreign_buy",
    "trust_buy",
    "dealer_buy",
    "top_broker_buy",
    "key_broker_buy",
    "gov_broker_buy",
    "geo_broker_buy",
    "day_trade_volume",
    "margin_offset_volume",
)


def compute_scores(df: pd.DataFrame, config: StrategyConfig) -> pd.DataFrame:
    """Return ``df`` augmented with the four layer scores and total score.

    Input is assumed sorted ascending by date with no duplicate dates.
    All required columns must be present (see ``REQUIRED_COLUMNS``).
    Warmup bars (first ``box_period`` rows) will have NaN scores.
    """
    _validate_columns(df)
    out = df.copy()

    # ---------- L1 structure ----------
    body_high = np.where(out["close"] >= out["open"], out["close"], out["open"])
    body_low = np.where(out["close"] >= out["open"], out["open"], out["close"])
    out["body_high"] = body_high
    out["body_low"] = body_low

    out["box_upper"] = rolling_swing_high(out["body_high"], config.box_period)
    out["box_lower"] = rolling_swing_low(out["body_low"], config.box_period)
    out["box_mid"] = (out["box_upper"] + out["box_lower"]) / 2

    out["structure_score"] = np.where(
        out["close"] > out["box_upper"],
        2,
        np.where(out["close"] >= out["box_mid"], 1, 0),
    )

    # ---------- L2 institutional direction ----------
    f = out["foreign_buy"]
    t = out["trust_buy"]
    out["direction_score"] = np.select(
        condlist=[
            (f > 0) & (t > 0),
            (f > 0) | (t > 0),
            (f < 0) & (t < 0),
        ],
        choicelist=[2, 1, -1],
        default=0,
    )

    # ---------- L3 chip strength ----------
    chip_total = (
        out["foreign_buy"]
        + out["trust_buy"]
        + out["dealer_buy"]
        + out["top_broker_buy"]
        + out["key_broker_buy"]
        + out["gov_broker_buy"]
        + out["geo_broker_buy"]
    )
    net_volume = out["volume"] - out["day_trade_volume"] - out["margin_offset_volume"]
    # Mirror XScript: if net_volume == 0, carry previous value forward.
    net_volume = net_volume.replace(0, np.nan).ffill()
    chip_ratio = (chip_total / net_volume).fillna(0)
    out["chip_total"] = chip_total
    out["net_volume"] = net_volume
    out["chip_ratio"] = chip_ratio

    out["chip_score"] = np.select(
        condlist=[
            chip_ratio >= config.chip_strong_threshold,
            chip_ratio > 0,
            chip_ratio < 0,
        ],
        choicelist=[2, 1, -1],
        default=0,
    )

    # ---------- L4 momentum ----------
    _rsv, k, d = stochastic_kd(out["high"], out["low"], out["close"], 5, 3, 3)
    dif_sl, _macd_d, osc_d = macd_weighted(out["high"], out["low"], out["close"], 5, 10, 3)
    rsi_5 = rsi(out["close"], 5)
    rsi_10 = rsi(out["close"], 10)
    ma5 = out["close"].rolling(5, min_periods=5).mean()
    ma10 = out["close"].rolling(10, min_periods=10).mean()
    ma20 = out["close"].rolling(20, min_periods=20).mean()
    ema5 = out["close"].ewm(span=5, adjust=False).mean()
    ema10 = out["close"].ewm(span=10, adjust=False).mean()

    out["k"] = k
    out["d"] = d
    out["dif_sl"] = dif_sl
    out["osc_d"] = osc_d
    out["rsi_5"] = rsi_5
    out["rsi_10"] = rsi_10
    out["ma5"] = ma5
    out["ma10"] = ma10
    out["ma20"] = ma20
    out["ema5"] = ema5
    out["ema10"] = ema10

    rising = lambda s: s > s.shift(1)  # noqa: E731 — local closure is intentional

    flameout = (out["close"] < ma5) & (k < d) & (rsi_5 < rsi_10)
    three_sun = (
        (out["close"] >= ma5)
        & (out["close"] >= ma10)
        & (out["close"] >= ma20)
        & (ema5 >= ema10)
        & rising(rsi_5)
        & rising(k)
        & rising(dif_sl)
        & rising(osc_d)
    )
    gold_cross = (
        (k > d)
        & (rsi_5 > rsi_10)
        & rising(dif_sl)
        & rising(osc_d)
        & (out["close"] >= ema10)
    )
    two_sun = (
        (out["close"] >= ma5)
        & (out["close"] >= ma10)
        & (out["close"] < ma20)
        & (ema5 >= ema10)
        & rising(rsi_5)
        & rising(k)
        & rising(dif_sl)
        & rising(osc_d)
    )

    out["momentum_score"] = np.select(
        condlist=[flameout, three_sun, gold_cross | two_sun],
        choicelist=[-1, 2, 1],
        default=0,
    )

    # ---------- Total ----------
    out["total_score"] = (
        out["structure_score"]
        + out["direction_score"]
        + out["chip_score"]
        + out["momentum_score"]
    )
    return out


def _validate_columns(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"compute_scores missing required columns: {missing}")
