"""orchestration CLI — drive the daily pipeline (WBS 7.D.2).

    uv run python -m backtest_platform.orchestration.cli run --dry-run
    uv run python -m backtest_platform.orchestration.cli list-stages

``run --dry-run`` (default) executes the no-op demo pipeline — safe, touches no
data/broker/network — and is the smoke test for the flow engine. ``run --real``
runs the canonical ETL→signals→risk→orders→log pipeline; its collaborators are
injected via ``FlowContext.config`` (live wiring is the 7.D.3 follow-up), so a
bare ``--real`` run cleanly reports the first stage missing its collaborator
rather than crashing.
"""
from __future__ import annotations

import click

from backtest_platform.orchestration.daily_flow import (
    FlowContext,
    build_daily_stages,
    demo_stages,
    run_flow,
)


@click.group()
def cli() -> None:
    """Daily-flow orchestration: run / list-stages."""


@cli.command("run")
@click.option(
    "--dry-run/--real", default=True, show_default=True,
    help="dry-run：no-op demo 管線（安全）；real：套用 build_daily_stages（需注入 collaborators，見 7.D.3）",
)
def run_cmd(dry_run: bool) -> None:
    """Run the daily flow (fail-fast); exit non-zero if any stage fails."""
    stages = demo_stages() if dry_run else build_daily_stages()
    run = run_flow(stages, FlowContext(config={}))
    click.echo(run.summary())
    if not run.ok:
        raise SystemExit(1)


@cli.command("list-stages")
def list_stages_cmd() -> None:
    """List the canonical daily-pipeline stage order."""
    for name, _ in build_daily_stages():
        click.echo(name)


if __name__ == "__main__":
    cli()
