"""Strategy contract + registry — the platform↔strategy seam (ADR-027).

Why this exists
---------------
The platform's job is to judge *any* strategy by identical plumbing
(metrics / gate / ledger). For that, upper layers must depend on a stable
strategy *contract*, never on a concrete strategy. Before this module the
research path hard-wired four-layer-resonance (``is_harness``) and grew a
parallel harness per new strategy (``momentum_harness``), so adding a strategy
touched 7-12 files and four-layer was the only engine-mounted "privileged
citizen". This collapses all of that to one seam.

The seam is at the **output**, not the input
---------------------------------------------
Strategies have genuinely different inputs — four-layer is per-stock
event-driven (scoring → signal state machine), momentum / inst_flow are
cross-sectional panels. Forcing one input shape would be premature
abstraction (special cases pushed into the contract). What they *share* is the
output every consumer needs: a daily-returns series + trades + a gate-ready
metrics dict. So the contract is a ``StrategyRunner`` whose ``run`` returns a
:class:`StrategyRun`; each runner privately knows what data it needs and builds
it from the same per-stock ``Loader`` (``research.is_harness.load_merged_parquet``
returns daily+institutional+chip merged, a superset every strategy slices).

Design notes
------------
- Pure-function strategies stay pure (ADR-003); the runner is a thin adapter,
  not a stateful object. Runners live in ``research/`` (the harness layer that
  may depend on ``validation`` / ``config``); this module holds only the
  contract types + registry, so it has no upward dependency.
- ``config`` is typed as ``pydantic.BaseModel`` (each strategy passes its own
  frozen config) — deliberately NOT a shared ``StrategyConfigBase``: that would
  force ``config.StrategyConfig`` to import from this ``strategies`` module
  (an upward dependency) for zero behavioural gain. YAGNI until a real
  polymorphic-config need appears.
- The registry is a plain name→runner dict, NOT a versioned model registry —
  ADR-022 deliberately rejected the heavyweight champion/challenger registry for
  a single-operator project.
- Mirrors ``engines/protocol.py`` (``Engine`` Protocol + ``get_engine`` factory)
  so the two seams read the same.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol, runtime_checkable

import pandas as pd
from pydantic import BaseModel

# A loader maps a stock id → its merged daily/institutional/chip frame (the
# ETLBundle.merged shape). Every strategy slices the columns it needs from this,
# so the platform has ONE data-access seam, not one per strategy.
Loader = Callable[[str], pd.DataFrame]


@dataclass(frozen=True)
class StrategyRun:
    """The uniform output every strategy produces — the seam consumers depend on.

    ``metrics`` is the gate-ready dict (cagr / sharpe / slippage_sharpe / maxdd /
    trades / …) that ``validation.gate_state.evaluate_gate`` consumes. ``returns``
    is the portfolio daily-returns series the metrics are derived from (exposed so
    a caller can render a tear sheet without re-running). ``trades`` is the
    per-trade list the trade-quality metrics use. Empty Series / empty list when
    the window yields no tradable data.
    """

    metrics: dict[str, Any]
    returns: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    trades: list[dict[str, Any]] = field(default_factory=list)


@runtime_checkable
class StrategyRunner(Protocol):
    """Structural interface every strategy implements to plug into the platform.

    ``run`` takes a universe, an IS window, the strategy's own (frozen) config,
    and the shared per-stock ``Loader``, and returns a :class:`StrategyRun`.
    Callers resolve presets → concrete config upstream (same convention as
    ``engines.protocol``), so the runner never reaches for global preset state.
    """

    def run(
        self,
        symbols: list[str],
        start: date | str,
        end: date | str,
        config: BaseModel,
        loader: Loader,
    ) -> StrategyRun:
        """Run the strategy over ``symbols`` in ``[start, end]`` → a StrategyRun."""
        ...


# --- registry -------------------------------------------------------------

_REGISTRY: dict[str, StrategyRunner] = {}


def register_strategy(name: str) -> Callable[[type], type]:
    """Class decorator: register a ``StrategyRunner`` under ``name``.

    Used at strategy-module import time. Re-registering the same name is an
    error (catches accidental duplicate names / double imports).
    """

    def deco(cls: type) -> type:
        if name in _REGISTRY:
            raise ValueError(f"strategy {name!r} already registered")
        _REGISTRY[name] = cls()
        return cls

    return deco


def get_strategy(name: str) -> StrategyRunner:
    """Resolve a registered strategy name to its runner instance."""
    try:
        return _REGISTRY[name]
    except KeyError:
        raise ValueError(
            f"unknown strategy {name!r}; choose from {sorted(_REGISTRY)}"
        ) from None


def list_strategies() -> list[str]:
    """Names of all registered strategies (sorted)."""
    return sorted(_REGISTRY)
