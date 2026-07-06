"""Reversal runner — plugs short-term reversal into the platform (ADR-027/028).

Implements ``strategies.protocol.StrategyRunner``: build a close panel from the
loader, run the pure ``backtest_reversal`` (normal + extra-slippage), and return a
gate-ready ``StrategyRun``. Importing this module registers ``"reversal"``.
"""
from __future__ import annotations

from datetime import date
from typing import ClassVar

from quant_platform.services.research_validation.strategies.common.panel import column_panel, panel_metrics
from quant_platform.services.research_validation.strategies.protocol import (
    GateSpec,
    Loader,
    StrategyRun,
    register_strategy,
)
from quant_platform.services.research_validation.strategies.reversal.strategy import (
    ReversalConfig,
    backtest_reversal,
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


@register_strategy("reversal")
class ReversalRunner:
    """Short-term cross-sectional reversal (long recent losers) over a close panel."""

    config_model: ClassVar[type[ReversalConfig]] = ReversalConfig
    title: ClassVar[str] = "Short-term Cross-sectional Reversal"
    # Panel strategy → the generic panel gate (K1/K2/K3 edge + avg_holdings health);
    # its keys ⊆ panel_metrics, so no strategy-specific gate is needed.
    gate: ClassVar[GateSpec] = PANEL_GATE

    def run(
        self,
        symbols: list[str],
        start: date | str,
        end: date | str,
        config: ReversalConfig,
        loader: Loader,
    ) -> StrategyRun:
        cfg = config  # caller already validated via config_model(**params)
        prices = column_panel(symbols, loader, "close")
        if prices.empty:
            return StrategyRun(_EMPTY_METRICS)
        res = backtest_reversal(prices, cfg, start, end)
        slip = backtest_reversal(prices, cfg.with_extra_slippage(_SLIP_STRESS), start, end)
        return StrategyRun(panel_metrics(res, slip), res.daily_returns)
