"""Cross-sectional short-term reversal — a new edge family (non-momentum, non-flow).

Mechanism (orthogonal to 12-1 momentum and to institutional-flow): short-horizon
*losers* over-shoot on the downside and mean-revert next period — the compensation a
liquidity provider earns for absorbing uninformed selling pressure (Lehmann 1990;
Jegadeesh 1990). Taiwan's retail-heavy market makes the over-reaction leg large, so
buying the recent losers and holding a week harvests the bounce.

Signal each rebalance = trailing cumulative return over ``lookback_days`` *skipping*
the most recent ``skip_days`` (the 1-day skip avoids bid-ask bounce inflating a fake
loser). Rank cross-sectionally **ascending** (losers first), go long the bottom
``top_fraction`` equal-weight (platform long-only — the loser leg only), hold to the
next rebalance, and charge ``cost_round_rate`` on the turnover. Weekly rebalancing is
the default because the reversal edge decays within days — which also makes turnover
cost the binding constraint, so cost handling reuses momentum's tested ``trim_overlap``
stitch verbatim.

Pure functions over a price panel (date × symbol); no IO, so unit-testable on
synthetic prices. Structurally identical to ``momentum.strategy`` (same rebalance /
cost / vol-target mechanics) — only the signal window and the sort direction differ,
so the two strategies are judged on identical plumbing.

Refs:
  Jegadeesh, N. (1990). *Evidence of Predictable Behavior of Security Returns.*
    Journal of Finance 45(3) — monthly reversal.
  Lehmann, B. (1990). *Fads, Martingales, and Market Efficiency.* QJE 105(1) —
    weekly reversal / contrarian portfolios.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field, model_validator

from quant_platform.services.research_validation.strategies.common import (
    clean_returns,
    rebalance_dates,
    trim_overlap,
    vol_target,
)


class ReversalConfig(BaseModel):
    """Short-term reversal parameters. Frozen so a config can't mutate mid-backtest."""

    model_config = {"frozen": True, "extra": "forbid"}

    lookback_days: int = Field(5, ge=2, le=60, description="反轉形成窗 J (交易日；文獻標準 5=一週)")
    skip_days: int = Field(
        1, ge=0, le=10,
        description="跳過最近 N 日 (避 bid-ask bounce 造假輸家；文獻標準 1)",
    )
    top_fraction: float = Field(
        0.1, gt=0, le=1.0, description="做多輸家端 fraction (等權；文獻 decile=0.1)"
    )
    cost_round_rate: float = Field(
        0.00671, ge=0, le=0.05, description="round-trip 成本 (StrategyConfig.cost_round_rate)"
    )
    cost_mode: str = Field(
        "lump", pattern="^(lump|spread)$",
        description="lump=再平衡當天一次扣；spread=攤提到持有期每日（較實際，go/no-go 建議）",
    )
    rebalance: str = Field(
        "weekly", pattern="^(weekly|monthly|quarterly|semiannual)$",
        description="再平衡頻率；反轉 edge 週內衰減故預設 weekly（高周轉→成本是 binding 限制）",
    )
    max_daily_return: float = Field(
        0.5, gt=0, le=2.0, description="winsorize 超過此絕對值的日報酬 (資料缺口/未調整防護)"
    )
    # --- exposure scaling (vol-targeting; off by default = vanilla reversal) ---
    vol_target_annual: float | None = Field(
        None, description="年化目標波動；設定則按 trailing 波動縮放曝險。None=關（純反轉）"
    )
    vol_lookback: int = Field(20, ge=5, le=120, description="trailing 波動估計窗 (交易日)")
    max_leverage: float = Field(
        1.0, gt=0, le=3.0, description="vol-target 曝險上限（1.0=僅 de-risk 不加槓桿）"
    )

    @model_validator(mode="after")
    def _skip_leaves_window(self) -> "ReversalConfig":
        # skip_days must leave a non-empty formation window; else the signal is all-NaN
        # and every rebalance silently holds nothing (a fail-fast at the boundary).
        if self.skip_days >= self.lookback_days:
            raise ValueError("skip_days must be < lookback_days (non-empty formation window)")
        return self

    def with_extra_slippage(self, slip: float) -> "ReversalConfig":
        """A copy with ``2*slip`` extra round-trip cost — for the K3 slippage Sharpe."""
        return self.model_copy(update={"cost_round_rate": self.cost_round_rate + 2.0 * slip})


@dataclass(frozen=True)
class ReversalResult:
    """One backtest run: the portfolio daily returns + execution diagnostics."""

    daily_returns: pd.Series
    n_rebalances: int
    avg_holdings: float
    avg_turnover: float


def _charge_cost(seg: pd.Series, turnover: float, cfg: ReversalConfig) -> pd.Series:
    """Apply the round-trip cost of one rebalance's ``turnover`` to segment ``seg``.

    ``spread`` amortizes the cost over the holding period (more realistic — you don't
    lose it all on day 1); ``lump`` charges it on the rebalance day. Either way a
    *deterministic* cost shifts mean return, not daily volatility, so judge
    cost-sensitivity via CAGR / net return, not Sharpe.
    """
    if not len(seg):
        return seg
    total_cost = cfg.cost_round_rate * turnover
    if cfg.cost_mode == "spread":
        return seg - total_cost / len(seg)
    seg = seg.copy()
    seg.iloc[0] = seg.iloc[0] - total_cost
    return seg


def _reversal_segments(
    rets: pd.DataFrame, rev: pd.DataFrame, rebal: list, cfg: ReversalConfig
) -> tuple[list[pd.Series], list[int], list[float]]:
    """Stitch one held-return segment per rebalance (long the biggest losers).

    Returns parallel lists (segments / holding-counts / turnovers). ``trim_overlap``
    keeps exactly one row per date so the lump cost on each new segment's first row
    is never silently de-duplicated away (審查缺陷 #18 / PR #148 fix).
    """
    segs: list[pd.Series] = []
    holdings: list[int] = []
    turnovers: list[float] = []
    prev: set[str] = set()
    for i, rb in enumerate(rebal):
        nxt = rebal[i + 1] if i + 1 < len(rebal) else rets.index[-1]
        if rb not in rev.index:
            continue
        ranked = rev.loc[rb].dropna().sort_values(ascending=True)  # losers first
        if ranked.empty:
            continue
        k = max(1, int(len(ranked) * cfg.top_fraction))
        held = list(ranked.index[:k])  # the biggest losers (long-only reversal leg)
        seg = trim_overlap(rets.loc[rb:nxt, held].mean(axis=1).copy(), segs)
        turnover = len(set(held) ^ prev) / max(len(held), 1)
        seg = _charge_cost(seg, turnover, cfg)
        segs.append(seg)
        holdings.append(len(held))
        turnovers.append(turnover)
        prev = set(held)
    return segs, holdings, turnovers


def backtest_reversal(
    prices: pd.DataFrame,
    cfg: ReversalConfig,
    start: date | str,
    end: date | str,
) -> ReversalResult:
    """Run rebalanced short-term reversal over ``[start, end]`` on a price panel.

    ``prices``: wide DataFrame indexed by date, one column per symbol. Needs
    ``lookback_days`` of history *before* ``start`` for the first signal. Long the
    bottom ``top_fraction`` by trailing return (the losers). Cost charged on each
    rebalance's turnover. Empty/insufficient data → empty result.
    """
    px = prices[prices > 0]  # non-positive closes = halt placeholders → drop
    rets = clean_returns(px, cfg.max_daily_return)
    rev = px.shift(cfg.skip_days) / px.shift(cfg.lookback_days) - 1.0  # J-day, skip most recent
    win = rets.loc[str(start):str(end)]
    if win.empty:
        return ReversalResult(pd.Series(dtype=float), 0, 0.0, 0.0)

    rebal = rebalance_dates(win.index, cfg.rebalance)
    segs, holdings, turnovers = _reversal_segments(win, rev, rebal, cfg)
    if not segs:
        return ReversalResult(pd.Series(dtype=float), 0, 0.0, 0.0)
    daily = pd.concat(segs).sort_index()
    if cfg.vol_target_annual is not None:
        daily = vol_target(daily, cfg.vol_target_annual, cfg.vol_lookback, cfg.max_leverage)
    return ReversalResult(
        daily_returns=daily,
        n_rebalances=len(segs),
        avg_holdings=float(np.mean(holdings)) if holdings else 0.0,
        avg_turnover=float(np.mean(turnovers)) if turnovers else 0.0,
    )
