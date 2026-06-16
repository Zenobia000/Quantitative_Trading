"""Institutional-flow runner — plugs net-buy-intensity into the platform (ADR-027/028).

Implements ``strategies.protocol.StrategyRunner``: build close/flow/volume panels
from the loader, run the pure ``backtest_inst_flow`` (normal + extra-slippage), and
return a gate-ready ``StrategyRun``. Importing this module registers ``"inst_flow"``.
"""
from __future__ import annotations

from datetime import date
from typing import ClassVar

from backtest_platform.strategies.common.panel import flow_panels, panel_metrics
from backtest_platform.strategies.inst_flow.strategy import (
    InstFlowConfig,
    backtest_inst_flow,
)
from backtest_platform.strategies.protocol import (
    Loader,
    StrategyRun,
    register_strategy,
)

_SLIP_STRESS = 0.003

_EMPTY_METRICS: dict = {
    "trades": 0, "bars": 0,
    "cagr": 0.0, "sharpe": 0.0, "slippage_sharpe": 0.0, "maxdd": 0.0,
}


@register_strategy("inst_flow")
class InstFlowRunner:
    """Long-top-fraction by trailing institutional net-buy intensity."""

    config_model: ClassVar[type[InstFlowConfig]] = InstFlowConfig
    title: ClassVar[str] = "Institutional Net-Buy Flow"

    def run(
        self,
        symbols: list[str],
        start: date | str,
        end: date | str,
        config: InstFlowConfig,
        loader: Loader,
    ) -> StrategyRun:
        cfg = config  # caller already validated via config_model(**params)
        close, flow, vol = flow_panels(symbols, loader, cfg.flow_cols)
        if close.empty:
            return StrategyRun(_EMPTY_METRICS)
        res = backtest_inst_flow(close, flow, vol, cfg, start, end)
        slip = backtest_inst_flow(
            close, flow, vol, cfg.with_extra_slippage(_SLIP_STRESS), start, end
        )
        return StrategyRun(panel_metrics(res, slip), res.daily_returns)
