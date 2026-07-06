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
from typing import ClassVar

from quant_platform.services.research_validation.strategies._template.strategy import (
    TemplateConfig,
    backtest_template,
)
from quant_platform.services.research_validation.strategies.common.panel import column_panel, panel_metrics
from quant_platform.services.research_validation.strategies.protocol import (
    GateSpec,
    Loader,
    StrategyRun,
    register_strategy,
)
from quant_platform.services.research_validation.validation.gate_state import PANEL_GATE

_SLIP_STRESS = 0.003

_EMPTY_METRICS: dict = {
    "trades": 0, "bars": 0,
    "cagr": 0.0, "sharpe": 0.0, "slippage_sharpe": 0.0, "maxdd": 0.0,
    # diversification health key the PANEL_GATE reads — present (=0) so an empty
    # run is judged FAIL, never INCOMPLETE (審查缺陷 #8): gate keys ⊆ metrics keys.
    "avg_holdings": 0.0,
}


@register_strategy("template")
class TemplateRunner:
    """Equal-weight buy-and-hold baseline — the worked example of the contract."""

    config_model: ClassVar[type[TemplateConfig]] = TemplateConfig
    title: ClassVar[str] = "Template (equal-weight buy-and-hold)"
    # Panel strategy → the generic panel gate. Copy this line (and pick/author a
    # gate whose keys ⊆ your metrics) when you adapt the template.
    gate: ClassVar[GateSpec] = PANEL_GATE

    def run(
        self,
        symbols: list[str],
        start: date | str,
        end: date | str,
        config: TemplateConfig,
        loader: Loader,
    ) -> StrategyRun:
        cfg = config  # caller already validated via config_model(**params)
        prices = column_panel(symbols, loader, "close")
        if prices.empty:
            return StrategyRun(_EMPTY_METRICS)
        res = backtest_template(prices, cfg, start, end)
        slip = backtest_template(prices, cfg.with_extra_slippage(_SLIP_STRESS), start, end)
        return StrategyRun(panel_metrics(res, slip), res.daily_returns)
