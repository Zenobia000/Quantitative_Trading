"""Strategy contract + registry — the platform↔strategy seam (ADR-027/028).

Why this exists
---------------
The platform's job is to judge *any* strategy by identical plumbing
(metrics / gate / ledger). For that, upper layers must depend on a stable
strategy *contract*, never on a concrete strategy. Before ADR-027 the research
path hard-wired four-layer-resonance and grew a parallel harness per new strategy,
so adding a strategy touched 7-12 files. ADR-028 extends the contract with
``config_model`` (self-description) and ``title`` so the registry becomes a
self-describing catalog for dispatch, schema exposure, and the conformance gate.

The seam is at the **output**, not the input
---------------------------------------------
Strategies have genuinely different inputs — four-layer is per-stock
event-driven (scoring → signal state machine), momentum / inst_flow are
cross-sectional panels. What they *share* is the output: a daily-returns series
+ trades + a gate-ready metrics dict. So the contract is a ``StrategyRunner``
whose ``run`` returns a :class:`StrategyRun`.

Design notes
------------
- ``config_model`` ClassVar: the strategy's own frozen Pydantic config class.
  Dispatch uses it to validate ``params`` (``config_model(**params)``); the API
  uses it to expose JSON-schema (``GET /strategies``); the conformance gate uses
  it to build a default config for contract checking.
- ``config`` arg to ``run`` is the already-validated output of
  ``config_model(**params)`` — runners MUST NOT re-wrap it with isinstance guards.
- The registry is a plain name→runner dict (ADR-022 rejected heavyweight registries
  for a single-operator project).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Any, ClassVar, Protocol, runtime_checkable

import pandas as pd
from pydantic import BaseModel

if TYPE_CHECKING:
    from quant_platform.services.research_validation.validation.gate_state import Criterion

# A loader maps a stock id → its merged daily/institutional/chip frame.
# Every strategy slices the columns it needs — ONE data-access seam.
Loader = Callable[[str], pd.DataFrame]

# GateSpec: the strategy's own validation gate — a tuple of
# ``validation.gate_state.Criterion`` (the审判庭's threshold set as data). It is
# written as a forward-ref string so the strategy *contract* stays import-light on
# the validation layer: the concrete Criterion tuples are built in each runner
# (which legitimately imports ``validation.gate_state``), while this module only
# names the shape. Reusing gate_state's Criterion avoids inventing a parallel gate
# type — the seam declares WHICH gate, never a second gate structure.
GateSpec = tuple["Criterion", ...]


@dataclass(frozen=True)
class StrategyRun:
    """The uniform output every strategy produces — the seam consumers depend on.

    ``metrics`` is the gate-ready dict (cagr / sharpe / slippage_sharpe / maxdd /
    trades / bars / …) that ``validation.gate_state.evaluate_gate`` consumes.
    ``returns`` is the portfolio daily-returns series (for tear sheets).
    ``trades`` is the per-trade list (for trade-quality metrics).
    Empty result: metrics must still carry {cagr, sharpe, slippage_sharpe,
    maxdd, trades, bars} all set to 0 / 0.0 so the conformance gate passes.
    """

    metrics: dict[str, Any]
    returns: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    trades: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class StrategyInfo:
    """Self-description of a registered strategy — feeds GET /strategies."""

    name: str
    title: str
    description: str        # from runner class __doc__ (first non-empty line)
    config_schema: dict     # runner.config_model.model_json_schema()


@runtime_checkable
class StrategyRunner(Protocol):
    """Structural interface every strategy implements to plug into the platform.

    ``run`` takes a universe, an IS window, the strategy's own (frozen) config,
    and the shared per-stock ``Loader``, and returns a :class:`StrategyRun`.

    ``config_model`` is the strategy's Pydantic config class — callers use it to
    validate ``params`` and to expose JSON-schema. ``title`` is a short human label.

    ``gate`` is the strategy's own validation gate (the审判庭 criteria that judge
    its runs). It MUST be declared — four-layer's health checks are meaningless for
    a panel strategy and vice-versa, so dispatch resolves each run's gate from the
    strategy that produced it (``get_strategy_gate``) instead of a shared default.

    Contract invariants enforced by the conformance gate:
    - ``config_model()`` (no args) must succeed (all fields have defaults or none).
    - ``run(...)`` must not raise on synthetic data.
    - ``run(...)`` metrics dict ⊇ {cagr, sharpe, slippage_sharpe, maxdd, trades, bars}.
    - ``gate`` is declared and every ``gate`` criterion key ⊆ the produced metrics.
    """

    config_model: ClassVar[type[BaseModel]]
    title: ClassVar[str]
    gate: ClassVar[GateSpec | None]

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

_REGISTRY: dict[str, "StrategyRunner"] = {}


def register_strategy(name: str) -> Callable[[type], type]:
    """Class decorator: register a ``StrategyRunner`` under ``name``.

    Re-registering the same name raises ValueError (catches duplicate imports).
    """

    def deco(cls: type) -> type:
        if name in _REGISTRY:
            raise ValueError(f"strategy {name!r} already registered")
        _REGISTRY[name] = cls()
        return cls

    return deco


def get_strategy(name: str) -> "StrategyRunner":
    """Resolve a registered strategy name to its runner instance."""
    try:
        return _REGISTRY[name]
    except KeyError:
        raise ValueError(
            f"unknown strategy {name!r}; choose from {sorted(_REGISTRY)}"
        ) from None


def get_strategy_gate(name: str) -> GateSpec:
    """Resolve a strategy's declared validation gate (審查缺陷 #8 / completes ADR-027).

    The platform judges every run through ``validation.gate_state.evaluate_gate``,
    but *which* criteria apply is strategy-specific: four-layer's health checks
    (struct1_pct/churn_pct/avg_hold) are entry-quality signals only four-layer
    produces; a cross-sectional panel strategy (momentum/inst_flow) never carries
    them, so judging it by four-layer's DEFAULT_GATE left it perpetually
    INCOMPLETE. Each runner therefore declares its own ``gate`` ClassVar and
    dispatch resolves it here.

    A strategy that declares no gate is a hard error — the platform refuses to
    judge a strategy by a foreign strategy's ruler, and refuses to silently claim
    a verdict it cannot justify.
    """
    runner = get_strategy(name)  # ValueError on unknown name
    gate = getattr(runner, "gate", None)
    if gate is None:
        raise ValueError(
            f"strategy {name!r} declares no validation gate; set its `gate` "
            f"ClassVar on the runner (see strategies/_template/runner.py). "
            f"Refusing to fall back to another strategy's gate."
        )
    return gate


def list_strategies() -> list[str]:
    """Names of all registered strategies (sorted)."""
    return sorted(_REGISTRY)


def describe_strategy(name: str) -> StrategyInfo:
    """Full self-description for one registered strategy."""
    runner = get_strategy(name)
    doc = (runner.__class__.__doc__ or "").strip().splitlines()
    description = next((line.strip() for line in doc if line.strip()), "")
    return StrategyInfo(
        name=name,
        title=getattr(runner, "title", name),
        description=description,
        config_schema=runner.config_model.model_json_schema(),
    )


def describe_strategies() -> list[StrategyInfo]:
    """Self-description of every registered strategy (sorted by name)."""
    return [describe_strategy(n) for n in list_strategies()]
