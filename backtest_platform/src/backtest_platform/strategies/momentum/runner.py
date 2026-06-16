"""Momentum runner — plugs 12-1 cross-sectional momentum into the platform (ADR-027).

Implements ``strategies.protocol.StrategyRunner``: build a close panel from the
loader, run the pure ``backtest_momentum`` (normal + extra-slippage), and return a
gate-ready ``StrategyRun``. Importing this module registers ``"momentum"``.
"""
from __future__ import annotations

from datetime import date

from backtest_platform.strategies.common.panel import column_panel, panel_metrics
from backtest_platform.strategies.momentum.strategy import (
    MomentumConfig,
    backtest_momentum,
)
from backtest_platform.strategies.protocol import (
    Loader,
    StrategyRun,
    register_strategy,
)

_SLIP_STRESS = 0.003  # 0.3% robustness slippage (K3) — matches four-layer's sim


@register_strategy("momentum")
class MomentumRunner:
    """12-1 cross-sectional momentum over a close panel."""

    def run(
        self,
        symbols: list[str],
        start: date | str,
        end: date | str,
        config: MomentumConfig,
        loader: Loader,
    ) -> StrategyRun:
        cfg = config if isinstance(config, MomentumConfig) else MomentumConfig()
        prices = column_panel(symbols, loader, "close")
        if prices.empty:
            return StrategyRun({"trades": 0, "bars": 0})
        res = backtest_momentum(prices, cfg, start, end)
        slip = backtest_momentum(prices, cfg.with_extra_slippage(_SLIP_STRESS), start, end)
        return StrategyRun(panel_metrics(res, slip), res.daily_returns)
