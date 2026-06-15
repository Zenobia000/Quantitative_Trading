"""Four-layer-resonance runner — plugs the strategy into the platform (ADR-027).

Implements ``strategies.protocol.StrategyRunner``. Unlike the panel strategies,
four-layer is per-stock event-driven: each stock is scored + run through the
signal state machine (``sim``), and the per-stock daily returns are averaged into
an equal-weight portfolio. Importing this module registers the strategy under
``"four_layer"``.
"""
from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from backtest_platform.config.strategy_config import StrategyConfig
from backtest_platform.strategies.four_layer_resonance import sim
from backtest_platform.strategies.protocol import (
    Loader,
    StrategyRun,
    register_strategy,
)


@register_strategy("four_layer")
class FourLayerRunner:
    """Per-stock scoring → signal state machine → equal-weight portfolio sim."""

    def run(
        self,
        symbols: list[str],
        start: date | str,
        end: date | str,
        config: StrategyConfig,
        loader: Loader,
    ) -> StrategyRun:
        cfg = config if isinstance(config, StrategyConfig) else StrategyConfig()
        slip = cfg.model_copy(update={"slip_rate": sim._SLIP_STRESS})
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
            return StrategyRun({"trades": 0, "closed": 0, "bars": 0})
        port = pd.concat(norm, axis=1).mean(axis=1)
        port_slip = pd.concat(slipr, axis=1).mean(axis=1)
        m = sim.metrics(port, port_slip, all_trades, n_buys)
        m["bars"] = len(port)
        return StrategyRun(m, port, all_trades)
