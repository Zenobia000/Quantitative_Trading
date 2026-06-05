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
    cost_mode: str = Field(
        "lump", pattern="^(lump|spread)$",
        description="lump=再平衡當天一次扣；spread=攤提到持有期每日（較實際，建議 go/no-go 用）",
    )
    rebalance: str = Field(
        "monthly", pattern="^(monthly|quarterly|semiannual)$",
        description="再平衡頻率；quarterly/semiannual 降周轉→砍交易成本拖累（成本是 binding 限制時的槓桿）",
    )
    max_daily_return: float = Field(
        0.5, gt=0, le=2.0, description="winsorize 超過此絕對值的日報酬 (資料缺口/未調整防護)"
    )
    # --- crash control (vol-targeting; off by default = vanilla momentum) ---
    vol_target_annual: float | None = Field(
        None, description="年化目標波動；設定則按 trailing 波動縮放曝險（馴 momentum crash）。None=關"
    )
    vol_lookback: int = Field(20, ge=5, le=120, description="trailing 波動估計窗 (交易日)")
    max_leverage: float = Field(
        1.0, gt=0, le=3.0, description="vol-target 曝險上限（1.0=僅 de-risk 不加槓桿）"
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


def _rebalance_dates(index: pd.DatetimeIndex, freq: str = "monthly") -> list[pd.Timestamp]:
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


def _vol_target(returns: pd.Series, target_annual: float, lookback: int, max_lev: float) -> pd.Series:
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

    rebal = _rebalance_dates(win.index, cfg.rebalance)
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
            total_cost = cfg.cost_round_rate * turnover
            # ``spread`` amortizes the round-trip cost over the holding period (more
            # realistic — you don't lose it all on day 1); ``lump`` charges it on the
            # rebalance day. Either way a *deterministic* cost shifts mean return, not
            # daily volatility, so Sharpe stays relatively cost-insensitive by design —
            # judge cost-sensitivity via CAGR / net return, not Sharpe.
            if cfg.cost_mode == "spread":
                seg = seg - total_cost / len(seg)
            else:
                seg.iloc[0] = seg.iloc[0] - total_cost
        segs.append(seg)
        holdings.append(len(held))
        turnovers.append(turnover)
        prev = set(held)

    if not segs:
        return MomentumResult(pd.Series(dtype=float), 0, 0.0, 0.0)
    daily = pd.concat(segs).groupby(level=0).first()  # overlapping rebalance day → first
    if cfg.vol_target_annual is not None:
        daily = _vol_target(daily, cfg.vol_target_annual, cfg.vol_lookback, cfg.max_leverage)
    return MomentumResult(
        daily_returns=daily,
        n_rebalances=len(segs),
        avg_holdings=float(np.mean(holdings)),
        avg_turnover=float(np.mean(turnovers)),
    )
