"""TEMPLATE strategy — copy this folder to author a new strategy (ADR-027).

================================ HOW TO USE ================================
1. Copy ``strategies/_template/`` → ``strategies/<your_strategy>/``.
2. Rename the config + result + backtest function, write YOUR signal logic in
   ``backtest_template`` (this file is the only place your alpha idea lives).
3. Edit ``runner.py``: rename the class, change ``@register_strategy("template")``
   to your name, call your backtest function.
4. Register it for the platform by adding one import line to
   ``research/runners.py`` (the aggregator). That's it — 2-3 files, no edits to
   the engine / CLI / gate.
5. ``get_strategy("<your_strategy>").run(symbols, start, end, cfg, loader)`` now
   returns a ``StrategyRun`` the platform judges like every other strategy.

============================ THE CONTRACT (I/O) ============================
INPUT  — your backtest is a PURE function (no IO, ADR-003) over:
           • a price/data panel (built by the runner from the shared ``Loader``)
           • your frozen config
           • the [start, end] window
OUTPUT — daily portfolio returns + execution diagnostics. The runner wraps this
         into the uniform ``StrategyRun(metrics, returns, trades)`` every
         consumer (metrics / gate / ledger) depends on.

This template is a *working* trivial strategy — equal-weight buy-and-hold of the
whole universe — so it also serves as a tested baseline and a smoke test of the
contract. Replace the body, keep the shape.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd
from pydantic import BaseModel, Field

from backtest_platform.strategies.common import clean_returns


class TemplateConfig(BaseModel):
    """Your strategy's parameters. Frozen so it can't mutate mid-backtest.

    Keep ``frozen=True`` + ``extra="forbid"`` — the platform relies on configs
    being immutable and rejecting typos.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    max_daily_return: float = Field(
        0.5, gt=0, le=2.0, description="winsorize 超過此絕對值的日報酬（資料缺口防護）"
    )

    def with_extra_slippage(self, slip: float) -> TemplateConfig:
        """A copy carrying extra cost — used for the K3 robustness Sharpe.

        Buy-and-hold has no turnover, so this template ignores ``slip``; a real
        strategy returns a copy with its cost field bumped (see momentum).
        """
        return self.model_copy()


@dataclass(frozen=True)
class TemplateResult:
    """One backtest run: portfolio daily returns + execution diagnostics.

    The diagnostic fields (``n_rebalances`` / ``avg_holdings`` / ``avg_turnover``)
    are what ``strategies.common.panel.panel_metrics`` reads — keep them if you
    reuse that helper.
    """

    daily_returns: pd.Series
    n_rebalances: int
    avg_holdings: float
    avg_turnover: float


def backtest_template(
    prices: pd.DataFrame,
    cfg: TemplateConfig,
    start: date | str,
    end: date | str,
) -> TemplateResult:
    """Equal-weight buy-and-hold over ``[start, end]`` — replace with your alpha.

    ``prices``: wide close panel (date x symbol). The portfolio return each day is
    the cross-sectional mean of the per-stock returns (everyone held, equal
    weight). A real strategy would instead *select* names by some signal here.
    """
    px = prices[prices > 0]
    rets = clean_returns(px, cfg.max_daily_return)
    win = rets.loc[str(start):str(end)]
    if win.empty:
        return TemplateResult(pd.Series(dtype=float), 0, 0.0, 0.0)
    daily = win.mean(axis=1)  # equal-weight across all symbols
    return TemplateResult(
        daily_returns=daily,
        n_rebalances=1,                       # bought once, held
        avg_holdings=float(win.shape[1]),     # held the whole universe
        avg_turnover=0.0,                     # buy-and-hold → no turnover
    )
