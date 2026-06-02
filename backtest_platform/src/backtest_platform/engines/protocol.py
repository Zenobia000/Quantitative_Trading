"""Engine Protocol (5.C.1) — a unified backtest interface so upper layers don't
bind to a specific engine (sim / zipline / vectorbt).

``Engine`` is a ``typing.Protocol``: any object exposing
``run(stocks, start, end, config) -> dict`` is structurally an engine. This keeps
the research/orchestration code engine-agnostic — it asks ``get_engine(name)`` for
something it can call, never importing sim/zipline/vectorbt internals directly.

``SimEngine`` is the reference implementation. It wraps the offline close-to-close
portfolio sim from ``research.is_harness`` (the same logic ``run_is`` uses) but
takes a concrete ``StrategyConfig`` per call instead of a preset name, and an
injectable ``loader`` (default = ``load_merged_parquet``) so it is unit-testable
without the parquet cache.

zipline / vectorbt are provided as thin stub engines: they satisfy the Protocol
(so ``get_engine`` can return them and isinstance checks pass) but ``run`` raises
``NotImplementedError`` until their adapters land.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Literal, Protocol, runtime_checkable

import pandas as pd

from backtest_platform.config.strategy_config import StrategyConfig
from backtest_platform.research.is_harness import (
    _SLIP_STRESS,
    _daily_returns,
    _metrics,
    _signaled_window,
    _trades,
    load_merged_parquet,
)

EngineName = Literal["sim", "zipline", "vectorbt"]

# A loader maps a stock id → the merged daily/institutional/chip frame.
Loader = Callable[[str], pd.DataFrame]

# Minimum bars in the signaled window before a stock contributes to the portfolio
# (mirrors research.is_harness.run_is, where short windows are skipped).
_MIN_BARS = 30


@runtime_checkable
class Engine(Protocol):
    """Structural interface every backtest engine implements.

    ``run`` takes an explicit stock list, an IS window, and a concrete
    ``StrategyConfig`` (not a preset name — callers resolve presets upstream) and
    returns a metrics dict (cagr / sharpe / slippage_sharpe / maxdd / trades / …).
    """

    def run(
        self,
        stocks: list[str],
        start: date,
        end: date,
        config: StrategyConfig,
    ) -> dict:
        """Run the backtest and return a metrics dict."""
        ...


@dataclass(frozen=True)
class SimEngine:
    """Offline close-to-close portfolio sim (the ``research.is_harness`` logic).

    Reuses the harness helpers so SimEngine and ``run_is`` stay numerically
    identical; the only difference is SimEngine consumes a ``StrategyConfig``
    directly (preset-agnostic) and is wrapped behind the ``Engine`` Protocol.
    """

    loader: Loader = field(default=load_merged_parquet)

    def run(
        self,
        stocks: list[str],
        start: date,
        end: date,
        config: StrategyConfig,
    ) -> dict:
        """Simulate ``config`` over ``stocks`` in [start, end] → metrics dict."""
        slip_cfg = config.model_copy(update={"slip_rate": _SLIP_STRESS})
        norm_returns: list[pd.Series] = []
        slip_returns: list[pd.Series] = []
        all_trades: list[dict] = []
        n_buys = 0

        for sid in stocks:
            sig = _signaled_window(self.loader(sid), config, start, end)
            if len(sig) < _MIN_BARS:
                continue
            norm_returns.append(_daily_returns(sig, config))
            slip_returns.append(_daily_returns(sig, slip_cfg))
            all_trades.extend(_trades(sig, config))
            n_buys += int((sig["action"] == "buy").sum())

        if not norm_returns:
            return {"trades": 0, "closed": 0, "bars": 0}

        port = pd.concat(norm_returns, axis=1).mean(axis=1)
        port_slip = pd.concat(slip_returns, axis=1).mean(axis=1)
        out = _metrics(port, port_slip, all_trades, n_buys)
        out["bars"] = len(port)
        return out


@dataclass(frozen=True)
class _StubEngine:
    """Placeholder engine that satisfies the Protocol but defers execution.

    Lets ``get_engine('zipline' | 'vectorbt')`` resolve and pass isinstance/Protocol
    checks today, while making the not-yet-implemented status explicit and loud at
    call time instead of silently returning empty metrics.
    """

    name: EngineName

    def run(
        self,
        stocks: list[str],
        start: date,
        end: date,
        config: StrategyConfig,
    ) -> dict:
        raise NotImplementedError(
            f"engine {self.name!r} adapter is not implemented yet; "
            "use 'sim' or wire the adapter before calling run()"
        )


def get_engine(name: EngineName, loader: Loader | None = None) -> Engine:
    """Resolve an engine name to an ``Engine`` instance.

    ``sim`` returns a usable :class:`SimEngine` (optionally with an injected
    ``loader``). ``zipline`` / ``vectorbt`` return stub engines whose ``run``
    raises ``NotImplementedError`` until their adapters land.
    """
    if name == "sim":
        return SimEngine(loader=loader) if loader is not None else SimEngine()
    if name in ("zipline", "vectorbt"):
        return _StubEngine(name=name)
    raise ValueError(
        f"unknown engine {name!r}; choose from ('sim', 'zipline', 'vectorbt')"
    )
