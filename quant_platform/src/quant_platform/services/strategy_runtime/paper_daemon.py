"""Paper-trading daemon (8.H.8) — replay core.

Drives the daily-flow chain once per as-of date, persisting each day's telemetry
(signals / orders / equity) through the run's collaborators. This is the engine
that makes the Monitor views + time-series tables come alive.

REPLAY vs LIVE — same core, different clock:
  * **Replay** (this module, buildable/testable now): the date sequence comes from
    historical data, so a full run executes in seconds with no live-calendar wait.
  * **Live** (forward, needs real time + a market feed): swap the date source for a
    real-time scheduler that fires after each session close. The per-date execution
    + persistence path is identical — only where the dates come from changes.

Cross-date resilience: ``run_flow`` is fail-fast *within* a day, but the daemon
keeps going *across* days — one bad session is recorded as a failed step and the
replay continues, so a single data gap can't abort a multi-year run.

No IO of its own: the per-date ``config_for_date`` supplies the collaborators
(ingest / signal_fn / risk / orders / sink), so the daemon is testable with stubs.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from quant_platform.services.strategy_runtime.daily_flow import (
    FlowContext,
    FlowRun,
    Stage,
    StageResult,
    build_daily_stages,
    run_flow,
)


@dataclass(frozen=True)
class ReplayStep:
    """One as-of date's outcome — the date plus its full per-stage FlowRun."""

    as_of: date
    run: FlowRun

    @property
    def ok(self) -> bool:
        return self.run.ok


@dataclass(frozen=True)
class ReplaySummary:
    """The whole replay — every step in order, with roll-up helpers."""

    steps: tuple[ReplayStep, ...]

    @property
    def n_steps(self) -> int:
        return len(self.steps)

    @property
    def n_ok(self) -> int:
        return sum(1 for s in self.steps if s.ok)

    @property
    def ok(self) -> bool:
        """True only if every step's chain passed (and at least one ran)."""
        return bool(self.steps) and all(s.ok for s in self.steps)

    def failures(self) -> list[ReplayStep]:
        return [s for s in self.steps if not s.ok]

    def summary(self) -> str:
        lines = [f"REPLAY: {self.n_ok}/{self.n_steps} sessions green"]
        for s in self.steps:
            mark = "OK " if s.ok else "FAIL"
            tail = "" if s.ok else f" @ {s.run.failed_stage}"
            lines.append(f"  [{mark}] {s.as_of}{tail}")
        return "\n".join(lines)


def run_paper_replay(
    dates: Sequence[date],
    config_for_date: Callable[[date], dict[str, Any]],
    *,
    stages: Sequence[tuple[str, Stage]] | None = None,
) -> ReplaySummary:
    """Run the daily-flow chain once per as-of date.

    ``config_for_date(d)`` returns the ``FlowContext.config`` (collaborators) for
    session ``d`` — letting the strategy/signal rebind per date. Any exception
    building or running a date's chain is captured into a failed step so the
    replay never crashes mid-run.
    """
    stages = stages or build_daily_stages()
    steps: list[ReplayStep] = []
    for d in dates:
        try:
            ctx = FlowContext(config=config_for_date(d))
            run = run_flow(stages, ctx)
        except Exception as exc:  # noqa: BLE001 — a bad session must not abort the run
            run = FlowRun(
                (StageResult("setup", ok=False, detail=f"raised {type(exc).__name__}: {exc}"),)
            )
        steps.append(ReplayStep(d, run))
    return ReplaySummary(tuple(steps))


def replay_schedule(index: Any, freq: str = "quarterly") -> list[date]:
    """Rebalance as-of dates from a price ``DatetimeIndex`` — reuses the shared
    rebalance schedule so the daemon replays on the same cadence the factor trades."""
    from quant_platform.services.research_validation.strategies.common import rebalance_dates

    return [ts.date() for ts in rebalance_dates(index, freq)]
