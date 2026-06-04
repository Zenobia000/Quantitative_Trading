"""orchestration.daily_flow — the platform's daily-pipeline runner (WBS 7.D).

A small, dependency-free **staged-flow engine** that threads a shared context
through ordered stages, **fail-fast** on the first stage that errors, and returns
a structured per-stage result. It is the strategy-agnostic glue that turns the
modules built across the waves — ETL → signals → risk gate → orders → log — into
one operable daily run.

Two design choices keep it testable and un-coupled:

1. **Collaborators are injected** via ``FlowContext.config`` (the data loader,
   the strategy, the risk gate, the broker, the sink). The stage bodies only
   orchestrate; the heavy work lives in collaborators that tests stub. A stage
   whose collaborator is missing fails cleanly (``ok=False``) rather than raising.
2. **Prefect is optional.** :func:`as_prefect_flow` wraps the same runner in a
   ``@flow`` for scheduling/observability *when prefect is installed*, and falls
   back to the inline runner otherwise — mirroring the quantstats-optional tear
   sheet. Prefect is therefore never a hard dependency.

A daily run must never crash the scheduler: a stage that raises is caught and
recorded as a failed stage, and the flow halts there with a full audit trail.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "StageResult", "FlowContext", "FlowRun", "Stage",
    "run_flow", "as_prefect_flow",
    "build_daily_stages", "demo_stages",
    "stage_etl", "stage_signals", "stage_risk_gate", "stage_orders", "stage_log",
]


@dataclass(frozen=True)
class StageResult:
    """Outcome of one stage. ``output`` is threaded into the context for the next."""

    name: str
    ok: bool
    detail: str = ""
    output: Any = None


@dataclass
class FlowContext:
    """Mutable bag threaded through the flow.

    ``config`` holds inputs + injected collaborators (read-only by convention);
    ``outputs`` accumulates each stage's ``output`` keyed by stage name, so a
    later stage can read an earlier one's result.
    """

    config: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)


Stage = Callable[[FlowContext], StageResult]


@dataclass(frozen=True)
class FlowRun:
    """Immutable record of a flow execution — the per-stage audit trail."""

    stages: tuple[StageResult, ...]

    @property
    def ok(self) -> bool:
        """True only if the flow ran at least one stage and all stages passed."""
        return bool(self.stages) and all(s.ok for s in self.stages)

    @property
    def failed_stage(self) -> str | None:
        """Name of the first failed stage (where the flow halted), else None."""
        for s in self.stages:
            if not s.ok:
                return s.name
        return None

    def summary(self) -> str:
        head = "FLOW: OK" if self.ok else f"FLOW: FAILED @ {self.failed_stage}"
        lines = [head]
        for s in self.stages:
            lines.append(f"  {'✅' if s.ok else '❌'} {s.name}: {s.detail}")
        return "\n".join(lines)


def run_flow(
    stages: Sequence[tuple[str, Stage]],
    context: FlowContext | None = None,
) -> FlowRun:
    """Run named stages in order; **stop at the first failure** (fail-fast).

    A stage halts the flow when it returns ``ok=False`` *or* raises — a raised
    exception is captured into a failed :class:`StageResult` (never propagated,
    so the scheduler stays up). Each stage's ``output`` is stored in
    ``context.outputs[name]`` before the next stage runs. The returned
    :class:`FlowRun` lists every stage that actually executed.
    """
    ctx = context if context is not None else FlowContext()
    results: list[StageResult] = []
    for name, stage in stages:
        try:
            res = stage(ctx)
        except Exception as exc:  # noqa: BLE001 — fail-safe: capture, never crash the run
            res = StageResult(name, ok=False, detail=f"raised {type(exc).__name__}: {exc}")
        # Pin the registered name (a stage may build its result with any label).
        res = StageResult(name, res.ok, res.detail, res.output)
        results.append(res)
        ctx.outputs[name] = res.output
        if not res.ok:
            break
    return FlowRun(tuple(results))


def as_prefect_flow(
    stages: Sequence[tuple[str, Stage]],
    context: FlowContext | None = None,
) -> FlowRun:
    """Run via Prefect's ``@flow`` when available (scheduling/observability), else
    fall back to the inline :func:`run_flow`. Keeps Prefect an optional extra."""
    try:
        from prefect import flow  # type: ignore[import-not-found]
    except ImportError:
        return run_flow(stages, context)

    @flow(name="backtest-daily-flow")  # pragma: no cover — exercised only with prefect installed
    def _daily() -> FlowRun:
        return run_flow(stages, context)

    return _daily()


# --------------------------------------------------------------------------- #
# Canonical daily-pipeline stages — orchestration only; work is in collaborators
# pulled from ``ctx.config`` (so each stage is unit-testable with a stub).
# --------------------------------------------------------------------------- #

def _need(ctx: FlowContext, key: str, stage: str) -> tuple[Any, StageResult | None]:
    """Fetch a required collaborator from config; return a failed result if absent."""
    obj = ctx.config.get(key)
    if obj is None:
        return None, StageResult(stage, ok=False, detail=f"missing collaborator '{key}' in config")
    return obj, None


def stage_etl(ctx: FlowContext) -> StageResult:
    """Refresh market data for the configured universe.

    Collaborator ``config['ingest']``: ``Callable[[list[str]], dict[str, bool]]``
    (per-symbol ok map). Stage passes only when every symbol ingested.
    """
    ingest, miss = _need(ctx, "ingest", "etl")
    if miss:
        return miss
    universe = list(ctx.config.get("universe", []))
    result = ingest(universe)
    ok = bool(result) and all(result.values())
    n_ok = sum(1 for v in result.values() if v)
    return StageResult("etl", ok=ok, detail=f"{n_ok}/{len(result)} symbols ingested", output=result)


def stage_signals(ctx: FlowContext) -> StageResult:
    """Compute the day's signals. Collaborator ``config['signal_fn']``:
    ``Callable[[FlowContext], list]`` → signal records."""
    fn, miss = _need(ctx, "signal_fn", "signals")
    if miss:
        return miss
    signals = fn(ctx)
    return StageResult("signals", ok=True, detail=f"{len(signals)} signals", output=signals)


def stage_risk_gate(ctx: FlowContext) -> StageResult:
    """Ex-ante risk gate. Collaborator ``config['risk_check']``:
    ``Callable[[list], tuple[bool, str]]`` → (approved, reason). A rejection
    halts the flow (no orders placed when risk says no)."""
    check, miss = _need(ctx, "risk_check", "risk_gate")
    if miss:
        return miss
    approved, reason = check(ctx.outputs.get("signals", []))
    return StageResult("risk_gate", ok=bool(approved), detail=reason, output=approved)


def stage_orders(ctx: FlowContext) -> StageResult:
    """Translate approved signals into orders. Collaborator ``config['place']``:
    ``Callable[[list], list]`` → placed orders/fills."""
    place, miss = _need(ctx, "place", "orders")
    if miss:
        return miss
    orders = place(ctx.outputs.get("signals", []))
    return StageResult("orders", ok=True, detail=f"{len(orders)} orders placed", output=orders)


def stage_log(ctx: FlowContext) -> StageResult:
    """Persist the run + emit metrics. Collaborator ``config['sink']``:
    ``Callable[[FlowContext], str]`` → a log/record id."""
    sink, miss = _need(ctx, "sink", "log")
    if miss:
        return miss
    ref = sink(ctx)
    return StageResult("log", ok=True, detail=f"logged → {ref}", output=ref)


def build_daily_stages() -> list[tuple[str, Stage]]:
    """The canonical ETL→signals→risk→orders→log daily pipeline (collaborators
    supplied via ``FlowContext.config``)."""
    return [
        ("etl", stage_etl),
        ("signals", stage_signals),
        ("risk_gate", stage_risk_gate),
        ("orders", stage_orders),
        ("log", stage_log),
    ]


def demo_stages() -> list[tuple[str, Stage]]:
    """A no-op pipeline of the same shape for ``--dry-run`` / smoke tests — every
    stage passes without touching data/broker/network."""
    def _noop(name: str) -> Stage:
        return lambda ctx: StageResult(name, ok=True, detail="dry-run no-op", output=None)

    return [(name, _noop(name)) for name, _ in build_daily_stages()]
