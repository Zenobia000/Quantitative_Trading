"""Cross-sectional momentum (12-1) — a first-class platform strategy.

After four-layer-resonance tested value-DESTRUCTIVE on the same data+cost+gate
(`dev_docs/factor_baseline_diagnostic_result_2026-06-04.md`), this productionizes
the control factor that DID pass the gate: classic 12-1 cross-sectional momentum
(Jegadeesh & Titman 1993). Each month, rank the universe by trailing return over
``lookback_days`` *skipping* the most recent ``skip_days`` (the 1-month reversal),
go long the top ``top_fraction`` equal-weight, hold to the next rebalance, and
charge ``cost_round_rate`` on the rebalance turnover.

Pure functions over a price panel (date × symbol); no IO, so unit-testable with
synthetic prices. The IS harness (`research.momentum_harness`) wires it to a
loader + the gate審判庭 so momentum is judged by the same objective criteria as
any strategy. This is the platform's proof that it is strategy-agnostic: a second,
structurally different strategy plugs into the same metrics/gate/ledger.

Ref: Jegadeesh, N. & Titman, S. (1993). *Returns to Buying Winners and Selling
Losers*. Journal of Finance 48(1).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

TRADING_DAYS = 252


class MomentumConfig(BaseModel):
    """Momentum parameters. Frozen so a config can't mutate mid-backtest."""

    model_config = {"frozen": True, "extra": "forbid"}

    lookback_days: int = Field(252, ge=40, le=756, description="動能回看窗 J (交易日)")
    skip_days: int = Field(21, ge=0, le=63, description="跳過最近 N 日 (避 1 月反轉)")
    top_fraction: float = Field(1 / 3, gt=0, le=1.0, description="做多前 fraction (等權)")
    cost_round_rate: float = Field(
        0.00671, ge=0, le=0.05, description="round-trip 成本 (StrategyConfig.cost_round_rate)"
    )
    max_daily_return: float = Field(
        0.5, gt=0, le=2.0, description="winsorize 超過此絕對值的日報酬 (資料缺口/未調整防護)"
    )

    def with_extra_slippage(self, slip: float) -> "MomentumConfig":
        """A copy with ``2*slip`` extra round-trip cost — for the K3 slippage Sharpe."""
        return self.model_copy(update={"cost_round_rate": self.cost_round_rate + 2.0 * slip})


@dataclass(frozen=True)
class MomentumResult:
    """One backtest run: the portfolio daily returns + execution diagnostics."""

    daily_returns: pd.Series
    n_rebalances: int
    avg_holdings: float
    avg_turnover: float


def _clean_returns(prices: pd.DataFrame, max_daily: float) -> pd.DataFrame:
    """Daily returns with inf + >max_daily/day data-error jumps winsorized to NaN."""
    r = prices.pct_change().replace([np.inf, -np.inf], np.nan)
    return r.where(r.abs() <= max_daily)


def _rebalance_dates(index: pd.DatetimeIndex) -> list[pd.Timestamp]:
    """First trading day of each (year, month) present in ``index``."""
    s = pd.Series(index, index=index)
    return [grp.index[0] for _, grp in s.groupby([index.year, index.month])]


def backtest_momentum(
    prices: pd.DataFrame,
    cfg: MomentumConfig,
    start: date | str,
    end: date | str,
) -> MomentumResult:
    """Run monthly-rebalanced 12-1 momentum over ``[start, end]`` on a price panel.

    ``prices``: wide DataFrame indexed by date, one column per symbol. Needs
    ``lookback_days`` of history *before* ``start`` for the first signal. Cost is
    charged on each rebalance's turnover. Empty/insufficient data → empty result.
    """
    px = prices[prices > 0]  # non-positive closes = halt placeholders → drop
    rets = _clean_returns(px, cfg.max_daily_return)
    mom = px.shift(cfg.skip_days) / px.shift(cfg.lookback_days) - 1.0  # 12-1, per date
    win = rets.loc[str(start):str(end)]
    if win.empty:
        return MomentumResult(pd.Series(dtype=float), 0, 0.0, 0.0)

    rebal = _rebalance_dates(win.index)
    segs: list[pd.Series] = []
    holdings: list[int] = []
    turnovers: list[float] = []
    prev: set[str] = set()
    for i, rb in enumerate(rebal):
        nxt = rebal[i + 1] if i + 1 < len(rebal) else win.index[-1]
        ranked = mom.loc[rb].dropna().sort_values(ascending=False)
        if ranked.empty:
            continue
        k = max(1, int(len(ranked) * cfg.top_fraction))
        held = list(ranked.index[:k])
        seg = rets.loc[rb:nxt, held].mean(axis=1).copy()
        turnover = len(set(held) ^ prev) / max(len(held), 1)
        if len(seg):
            # NOTE (Sharpe-optimistic, follow-up): charging the round-trip cost as a
            # single lump-sum on the rebalance day dents CAGR but barely touches the
            # daily-return volatility (the Sharpe denominator) — so Sharpe is near
            # cost-immune here. Realistic intraday-spread/impact modeling would spread
            # the drag. Judge cost-sensitivity via CAGR, not Sharpe, until refined.
            seg.iloc[0] = seg.iloc[0] - cfg.cost_round_rate * turnover
        segs.append(seg)
        holdings.append(len(held))
        turnovers.append(turnover)
        prev = set(held)

    if not segs:
        return MomentumResult(pd.Series(dtype=float), 0, 0.0, 0.0)
    daily = pd.concat(segs).groupby(level=0).first()  # overlapping rebalance day → first
    return MomentumResult(
        daily_returns=daily,
        n_rebalances=len(segs),
        avg_holdings=float(np.mean(holdings)),
        avg_turnover=float(np.mean(turnovers)),
    )
