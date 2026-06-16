"""TEMPLATE runner — the 4-line adapter that plugs a strategy into the platform.

Copy + rename alongside ``strategy.py``. A runner does exactly three things:
  1. build the data panel(s) your backtest needs from the shared ``Loader``,
  2. call your pure backtest (normal + extra-slippage for the robustness Sharpe),
  3. return a uniform ``StrategyRun(metrics, returns, trades)``.

Keep the ``run(symbols, start, end, config, loader) -> StrategyRun`` signature
EXACTLY — that consistency is what lets the backtest system call any strategy the
same way.
"""
from __future__ import annotations

from datetime import date

from backtest_platform.strategies._template.strategy import (
    TemplateConfig,
    backtest_template,
)
from backtest_platform.strategies.common.panel import column_panel, panel_metrics
from backtest_platform.strategies.protocol import (
    Loader,
    StrategyRun,
    register_strategy,
)

_SLIP_STRESS = 0.003


@register_strategy("template")
class TemplateRunner:
    """Equal-weight buy-and-hold baseline — the worked example of the contract."""

    def run(
        self,
        symbols: list[str],
        start: date | str,
        end: date | str,
        config: TemplateConfig,
        loader: Loader,
    ) -> StrategyRun:
        cfg = config if isinstance(config, TemplateConfig) else TemplateConfig()
        prices = column_panel(symbols, loader, "close")
        if prices.empty:
            return StrategyRun({"trades": 0, "bars": 0})
        res = backtest_template(prices, cfg, start, end)
        slip = backtest_template(prices, cfg.with_extra_slippage(_SLIP_STRESS), start, end)
        return StrategyRun(panel_metrics(res, slip), res.daily_returns)
