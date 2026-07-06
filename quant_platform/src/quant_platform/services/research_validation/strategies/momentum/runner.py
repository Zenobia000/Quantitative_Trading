"""Momentum runner — plugs 12-1 cross-sectional momentum into the platform (ADR-027/028).

Implements ``strategies.protocol.StrategyRunner``: build a close panel from the
loader, run the pure ``backtest_momentum`` (normal + extra-slippage), and return a
gate-ready ``StrategyRun``. Importing this module registers ``"momentum"``.
"""
from __future__ import annotations

from datetime import date
from typing import ClassVar

from quant_platform.services.research_validation.strategies.common.panel import column_panel, panel_metrics
from quant_platform.services.research_validation.strategies.momentum.strategy import (
    MomentumConfig,
    backtest_momentum,
)
from quant_platform.services.research_validation.strategies.protocol import (
    GateSpec,
    Loader,
    StrategyRun,
    register_strategy,
)
from quant_platform.services.research_validation.validation.gate_state import MOMENTUM_GATE

_SLIP_STRESS = 0.003

_EMPTY_METRICS: dict = {
    "trades": 0, "bars": 0,
    "cagr": 0.0, "sharpe": 0.0, "slippage_sharpe": 0.0, "maxdd": 0.0,
    # diversification health key the MOMENTUM_GATE reads — present (=0) so an empty
    # run is judged FAIL, never INCOMPLETE (審查缺陷 #8): gate keys ⊆ metrics keys.
    "avg_holdings": 0.0,
}


@register_strategy("momentum")
class MomentumRunner:
    """12-1 cross-sectional momentum over a close panel."""

    config_model: ClassVar[type[MomentumConfig]] = MomentumConfig
    title: ClassVar[str] = "12-1 Cross-sectional Momentum"
    # K1/K2/K3 edge + diversification health (avg_holdings) — its keys ⊆ panel_metrics.
    gate: ClassVar[GateSpec] = MOMENTUM_GATE

    def run(
        self,
        symbols: list[str],
        start: date | str,
        end: date | str,
        config: MomentumConfig,
        loader: Loader,
    ) -> StrategyRun:
        cfg = config  # caller already validated via config_model(**params)
        prices = column_panel(symbols, loader, "close")
        if prices.empty:
            return StrategyRun(_EMPTY_METRICS)
        res = backtest_momentum(prices, cfg, start, end)
        slip = backtest_momentum(prices, cfg.with_extra_slippage(_SLIP_STRESS), start, end)
        return StrategyRun(panel_metrics(res, slip), res.daily_returns)
