"""Institutional-flow factor backtest (new edge family).

Signal = trailing 三大法人 net-buy **intensity** = sum(net_buy over lookback) /
sum(trading volume over lookback) — net buying as a fraction of volume, so a small
stock heavily bought ranks like a large one. Rank cross-sectionally, long the top
fraction, rebalance. Mechanics (rebalance cadence, turnover cost, vol-target crash
control) are reused verbatim from the momentum module so only the signal differs
and the two strategies are judged on identical plumbing.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from backtest_platform.strategies.common import (
    clean_returns,
    rebalance_dates,
    trim_overlap,
    vol_target,
)

_SOURCES = {
    "foreign": ("foreign_buy",),
    "foreign_trust": ("foreign_buy", "trust_buy"),
    "all": ("foreign_buy", "trust_buy", "dealer_buy"),
}


class InstFlowConfig(BaseModel):
    """Institutional-flow factor parameters (frozen)."""

    model_config = {"frozen": True, "extra": "forbid"}

    lookback_days: int = Field(60, ge=5, le=252, description="net-buy 累積窗 (交易日)")
    top_fraction: float = Field(1 / 3, gt=0, le=1.0, description="做多前 fraction (等權)")
    flow_source: str = Field(
        "foreign", description="foreign | foreign_trust | all（納入哪幾類法人 net-buy）"
    )
    cost_round_rate: float = Field(0.00671, ge=0, le=0.05, description="round-trip 成本")
    cost_mode: str = Field("lump", pattern="^(lump|spread)$")
    rebalance: str = Field("monthly", pattern="^(monthly|quarterly|semiannual)$")
    max_daily_return: float = Field(0.5, gt=0, le=2.0, description="winsorize 日報酬絕對值上限")
    vol_target_annual: float | None = Field(None, description="年化目標波動；None=關")
    vol_lookback: int = Field(20, ge=5, le=120)
    max_leverage: float = Field(1.0, gt=0, le=3.0)
    signal_lag_days: int = Field(
        1, ge=0, le=10,
        description="訊號落後天數（>=1 杜絕同日 look-ahead：用截至 rb-lag 的 net-buy 排序，"
        "避免「外資當日買→當日漲」的同期衝擊被誤當預測力）",
    )
    long_only_positive: bool = Field(
        True, description="只做多 net-buy intensity>0 者（法人實際淨買），否則持現金"
    )

    @property
    def flow_cols(self) -> tuple[str, ...]:
        return _SOURCES[self.flow_source]

    def with_extra_slippage(self, slip: float) -> "InstFlowConfig":
        return self.model_copy(update={"cost_round_rate": self.cost_round_rate + 2.0 * slip})


@dataclass(frozen=True)
class InstFlowResult:
    daily_returns: pd.Series
    n_rebalances: int
    avg_holdings: float
    avg_turnover: float


def flow_intensity(
    flow: pd.DataFrame, volume: pd.DataFrame, lookback: int
) -> pd.DataFrame:
    """Trailing net-buy intensity = Σ net_buy / Σ volume over ``lookback`` (per date).

    Volume-normalized so the signal is comparable across stock sizes. Zero-volume
    windows → NaN (excluded from ranking).
    """
    num = flow.rolling(lookback).sum()
    den = volume.rolling(lookback).sum().replace(0, np.nan)
    return num / den


def backtest_inst_flow(
    close: pd.DataFrame,
    flow: pd.DataFrame,
    volume: pd.DataFrame,
    cfg: InstFlowConfig,
    start: date | str,
    end: date | str,
) -> InstFlowResult:
    """Long-top-fraction by institutional-flow intensity, rebalanced.

    ``close`` / ``flow`` / ``volume`` are wide panels (date × symbol) on the same
    index; ``flow`` is the summed net-buy of ``cfg.flow_cols``. Needs ``lookback``
    history before ``start``.
    """
    px = close[close > 0]
    rets = clean_returns(px, cfg.max_daily_return)
    score = flow_intensity(flow, volume, cfg.lookback_days)
    if cfg.signal_lag_days:
        # rank on net-buy known strictly BEFORE the rebalance day → no same-day
        # look-ahead (foreign buying ↑ price the same day is impact, not foresight).
        score = score.shift(cfg.signal_lag_days)
    win = rets.loc[str(start):str(end)]
    if win.empty:
        return InstFlowResult(pd.Series(dtype=float), 0, 0.0, 0.0)

    rebal = rebalance_dates(win.index, cfg.rebalance)
    segs: list[pd.Series] = []
    holdings: list[int] = []
    turnovers: list[float] = []
    prev: set[str] = set()
    for i, rb in enumerate(rebal):
        nxt = rebal[i + 1] if i + 1 < len(rebal) else win.index[-1]
        if rb not in score.index:
            continue
        ranked = score.loc[rb].dropna().sort_values(ascending=False)
        if ranked.empty:
            continue
        k = max(1, int(len(ranked) * cfg.top_fraction))
        held = list(ranked.index[:k])
        if cfg.long_only_positive:
            held = [name for name in held if ranked[name] > 0]  # only real net buying
        if held:
            seg = trim_overlap(rets.loc[rb:nxt, held].mean(axis=1).copy(), segs)
            turnover = len(set(held) ^ prev) / max(len(held), 1)
            if len(seg):
                total_cost = cfg.cost_round_rate * turnover
                if cfg.cost_mode == "spread":
                    seg = seg - total_cost / len(seg)
                else:
                    seg.iloc[0] = seg.iloc[0] - total_cost
        else:
            seg = trim_overlap(pd.Series(0.0, index=rets.loc[rb:nxt].index), segs)
            turnover = 1.0 if prev else 0.0
        segs.append(seg)
        holdings.append(len(held))
        turnovers.append(turnover)
        prev = set(held)

    if not segs:
        return InstFlowResult(pd.Series(dtype=float), 0, 0.0, 0.0)
    daily = pd.concat(segs).sort_index()
    if cfg.vol_target_annual is not None:
        daily = vol_target(daily, cfg.vol_target_annual, cfg.vol_lookback, cfg.max_leverage)
    return InstFlowResult(
        daily_returns=daily,
        n_rebalances=len(segs),
        avg_holdings=float(np.mean(holdings)) if holdings else 0.0,
        avg_turnover=float(np.mean(turnovers)) if turnovers else 0.0,
    )
