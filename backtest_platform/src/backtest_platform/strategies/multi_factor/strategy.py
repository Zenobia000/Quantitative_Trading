"""Multi-factor composite backtest (momentum + inst-flow + low-vol).

Combines three orthogonal free-data factors with FIXED equal weights. Per
rebalance: cross-sectionally z-score each factor, average, rank, long the top
fraction. Fixed weights (no per-factor optimization) keep degrees of freedom low
— the structural answer to the single-factor PBO blow-out. Reuses momentum's
tested rebalance / cost / vol-target mechanics; inst-flow is 1-day lagged
(no same-day look-ahead).

Factor sign convention: higher composite z = more attractive (long).
- momentum  : 12-1 return (higher = stronger uptrend)
- inst_flow : net-buy / volume (higher = more institutional buying)
- low_vol   : -trailing vol (higher = lower volatility)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field, field_validator

from backtest_platform.strategies.momentum.strategy import (
    TRADING_DAYS,
    _clean_returns,
    _rebalance_dates,
    _vol_target,
)

_FACTORS = ("momentum", "inst_flow", "low_vol")


class MultiFactorConfig(BaseModel):
    """Composite parameters (frozen). Weights are FIXED equal by design."""

    model_config = {"frozen": True, "extra": "forbid"}

    mom_lookback: int = Field(252, ge=40, le=756, description="動能回看 J")
    mom_skip: int = Field(21, ge=0, le=63, description="動能跳過 (避 1 月反轉)")
    flow_lookback: int = Field(60, ge=5, le=252, description="法人 net-buy 累積窗")
    vol_lookback_signal: int = Field(60, ge=10, le=252, description="低波因子的波動估計窗")
    top_fraction: float = Field(1 / 3, gt=0, le=1.0)
    factors: tuple[str, ...] = Field(
        _FACTORS, description="納入的因子（等權；預設三者）"
    )
    cost_round_rate: float = Field(0.00671, ge=0, le=0.05)
    cost_mode: str = Field("lump", pattern="^(lump|spread)$")
    rebalance: str = Field("monthly", pattern="^(monthly|quarterly|semiannual)$")
    max_daily_return: float = Field(0.5, gt=0, le=2.0)
    flow_lag_days: int = Field(1, ge=0, le=10, description="法人訊號落後 (去 look-ahead)")
    vol_target_annual: float | None = Field(None)
    vol_lookback: int = Field(20, ge=5, le=120)
    max_leverage: float = Field(1.0, gt=0, le=3.0)

    @field_validator("factors")
    @classmethod
    def _known_factors(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        if not v:
            raise ValueError("factors must be non-empty")
        unknown = [f for f in v if f not in _FACTORS]
        if unknown:
            raise ValueError(f"unknown factor(s) {unknown}; choose from {_FACTORS}")
        return tuple(v)

    def with_extra_slippage(self, slip: float) -> "MultiFactorConfig":
        return self.model_copy(update={"cost_round_rate": self.cost_round_rate + 2.0 * slip})


@dataclass(frozen=True)
class MultiFactorResult:
    daily_returns: pd.Series
    n_rebalances: int
    avg_holdings: float
    avg_turnover: float


def _zscore_row(s: pd.Series) -> pd.Series:
    """Cross-sectional z-score (NaN-safe; all-equal → 0)."""
    v = s.astype(float)
    mu, sd = v.mean(), v.std(ddof=0)
    return (v - mu) / sd if sd and sd > 0 else v * 0.0


def composite_scores(
    close: pd.DataFrame,
    flow: pd.DataFrame,
    volume: pd.DataFrame,
    cfg: MultiFactorConfig,
) -> pd.DataFrame:
    """Per-date composite z-score panel = equal-weight mean of factor z-scores."""
    rets = _clean_returns(close[close > 0], cfg.max_daily_return)
    raw: dict[str, pd.DataFrame] = {}
    if "momentum" in cfg.factors:
        raw["momentum"] = close.shift(cfg.mom_skip) / close.shift(cfg.mom_lookback) - 1.0
    if "inst_flow" in cfg.factors:
        fi = flow.rolling(cfg.flow_lookback).sum() / volume.rolling(cfg.flow_lookback).sum().replace(0, np.nan)
        raw["inst_flow"] = fi.shift(cfg.flow_lag_days)
    if "low_vol" in cfg.factors:
        raw["low_vol"] = -rets.rolling(cfg.vol_lookback_signal).std()
    # z-score each factor cross-sectionally per date, then average (equal weight).
    zs = [df.apply(_zscore_row, axis=1) for df in raw.values()]
    return sum(zs) / len(zs)


def backtest_multi_factor(
    close: pd.DataFrame,
    flow: pd.DataFrame,
    volume: pd.DataFrame,
    cfg: MultiFactorConfig,
    start: date | str,
    end: date | str,
) -> MultiFactorResult:
    """Long-top-fraction by composite z-score, rebalanced."""
    rets = _clean_returns(close[close > 0], cfg.max_daily_return)
    score = composite_scores(close, flow, volume, cfg)
    win = rets.loc[str(start):str(end)]
    if win.empty:
        return MultiFactorResult(pd.Series(dtype=float), 0, 0.0, 0.0)

    rebal = _rebalance_dates(win.index, cfg.rebalance)
    segs, holdings, turnovers, prev = [], [], [], set()
    for i, rb in enumerate(rebal):
        nxt = rebal[i + 1] if i + 1 < len(rebal) else win.index[-1]
        if rb not in score.index:
            continue
        ranked = score.loc[rb].dropna().sort_values(ascending=False)
        if ranked.empty:
            continue
        k = max(1, int(len(ranked) * cfg.top_fraction))
        held = list(ranked.index[:k])
        seg = rets.loc[rb:nxt, held].mean(axis=1).copy()
        turnover = len(set(held) ^ prev) / max(len(held), 1)
        if len(seg):
            total_cost = cfg.cost_round_rate * turnover
            if cfg.cost_mode == "spread":
                seg = seg - total_cost / len(seg)
            else:
                seg.iloc[0] = seg.iloc[0] - total_cost
        segs.append(seg)
        holdings.append(len(held))
        turnovers.append(turnover)
        prev = set(held)

    if not segs:
        return MultiFactorResult(pd.Series(dtype=float), 0, 0.0, 0.0)
    daily = pd.concat(segs).groupby(level=0).first()
    if cfg.vol_target_annual is not None:
        daily = _vol_target(daily, cfg.vol_target_annual, cfg.vol_lookback, cfg.max_leverage)
    return MultiFactorResult(
        daily_returns=daily,
        n_rebalances=len(segs),
        avg_holdings=float(np.mean(holdings)) if holdings else 0.0,
        avg_turnover=float(np.mean(turnovers)) if turnovers else 0.0,
    )
