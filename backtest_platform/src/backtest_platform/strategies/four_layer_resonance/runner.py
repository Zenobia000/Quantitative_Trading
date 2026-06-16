"""Four-layer-resonance runner — plugs the strategy into the platform (ADR-027/028).

Implements ``strategies.protocol.StrategyRunner``. Unlike the panel strategies,
four-layer is per-stock event-driven: each stock is scored + run through the
signal state machine (``sim``), and the per-stock daily returns are averaged into
an equal-weight portfolio. Importing this module registers ``"four_layer"``.
"""
from __future__ import annotations

from datetime import date
from typing import Any, ClassVar

import pandas as pd

from backtest_platform.strategies.four_layer_resonance.config import StrategyConfig
from backtest_platform.strategies.four_layer_resonance import sim
from backtest_platform.strategies.protocol import (
    Loader,
    StrategyRun,
    register_strategy,
)

_EMPTY_METRICS: dict = {
    "trades": 0, "bars": 0,
    "cagr": 0.0, "sharpe": 0.0, "slippage_sharpe": 0.0, "maxdd": 0.0,
}


@register_strategy("four_layer")
class FourLayerRunner:
    """Per-stock scoring → signal state machine → equal-weight portfolio sim."""

    config_model: ClassVar[type[StrategyConfig]] = StrategyConfig
    title: ClassVar[str] = "Four-Layer Resonance"

    def run(
        self,
        symbols: list[str],
        start: date | str,
        end: date | str,
        config: StrategyConfig,
        loader: Loader,
    ) -> StrategyRun:
        cfg = config  # caller already validated via config_model(**params)
        slip = cfg.with_extra_slippage(sim._SLIP_STRESS)  # unified interface (V4)
        norm: list[pd.Series] = []
        slipr: list[pd.Series] = []
        all_trades: list[dict[str, Any]] = []
        n_buys = 0
        for sid in symbols:
            sig = sim.signaled_window(loader(sid), cfg, start, end)
            if len(sig) < sim.MIN_BARS:
                continue
            norm.append(sim.daily_returns(sig, cfg))
            slipr.append(sim.daily_returns(sig, slip))
            all_trades.extend(sim.trades(sig, cfg))
            n_buys += int((sig["action"] == "buy").sum())
        if not norm:
            return StrategyRun(_EMPTY_METRICS)
        port = pd.concat(norm, axis=1).mean(axis=1)
        port_slip = pd.concat(slipr, axis=1).mean(axis=1)
        m = sim.metrics(port, port_slip, all_trades, n_buys)
        m["bars"] = len(port)
        return StrategyRun(m, port, all_trades)
