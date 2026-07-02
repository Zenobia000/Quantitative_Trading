"""orchestration CLI — drive the daily pipeline (WBS 7.D.2).

    uv run python -m backtest_platform.orchestration.cli run --dry-run
    uv run python -m backtest_platform.orchestration.cli list-stages

``run --dry-run`` (default) executes the no-op demo pipeline — safe, touches no
data/broker/network — and is the smoke test for the flow engine. ``run --real``
runs the canonical ETL→signals→risk→orders→log pipeline; its collaborators are
injected via ``FlowContext.config``. The real collaborators now exist
(``orchestration.collaborators.build_paper_collaborators`` wires FinMind ingest +
RiskGate + PaperBroker + the TimescaleDB sink); supply them programmatically along
with a strategy ``signal_fn``. A bare CLI ``--real`` leaves config empty, so it
reports the first stage missing its collaborator rather than crashing — *which*
strategy to run (the signal_fn) is an edge/deployment decision, not infra.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import click

from backtest_platform.orchestration.after_close import (
    build_session_runner,
    run_after_close,
    safe_discord_notify,
)
from backtest_platform.orchestration.daily_flow import (
    FlowContext,
    build_daily_stages,
    demo_stages,
    run_flow,
)

_TWT = timezone(timedelta(hours=8))


def _today_taipei() -> date:
    """Today's date in Asia/Taipei — the default as-of for a live after-close run."""
    return datetime.now(_TWT).date()


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


@cli.command("after-close")
@click.option("--strategy", required=True, help="registered strategy name (e.g. inst_flow)")
@click.option("--date", "date_str", default=None,
              help="as-of session (YYYY-MM-DD); default = today Asia/Taipei (back-fill supported)")
@click.option("--dry-run", is_flag=True, default=False,
              help="pass the guards but DON'T trigger the daily flow (no finlab/DB touched)")
@click.option("--force", is_flag=True, default=False,
              help="skip the 14:30 Asia/Taipei after-close time gate")
@click.option("--universe", default=None,
              help="comma-separated symbols; else env AFTER_CLOSE_UNIVERSE")
@click.option("--equity", type=float, default=None,
              help="starting paper cash; else env AFTER_CLOSE_EQUITY or 10,000,000")
@click.option("--fresh", is_flag=True, default=False,
              help="skip DB position restore; start from an empty book (cash only)")
def after_close_cmd(
    strategy: str,
    date_str: str | None,
    dry_run: bool,
    force: bool,
    universe: str | None,
    equity: float | None,
    fresh: bool,
) -> None:
    """Run the forward after-close session for one strategy/date (cron/systemd entry).

    Guards a real-calendar run (trading-day → after-close time → idempotency) then
    drives the proven live-panel forward chain. Non-trading / too-early / already-done
    exit 0 with a clear message; a failed daily flow exits 1 (and alerts Discord).
    By default the session rehydrates the strategy's persisted book (cross-day
    position restore); ``--fresh`` opts out and starts from an empty book.
    """
    as_of = date.fromisoformat(date_str) if date_str else _today_taipei()

    def _lazy_runner(strat: str, on: date):  # built only if the guards actually run it
        return build_session_runner(strategy, universe, equity, fresh=fresh)(strat, on)

    # Defer the production wiring (broker / live-panel / universe requirement) until
    # AFTER the cheap guards pass — a non-trading / too-early / already-done day must
    # no-op cleanly (exit 0) without needing a universe or touching finlab/DB. dry-run
    # never runs the flow, so it needs no runner at all.
    runner = None if dry_run else _lazy_runner
    result = run_after_close(
        strategy, as_of,
        dry_run=dry_run, force=force,
        session_runner=runner, notifier=safe_discord_notify,
    )
    click.echo(result.message)
    raise SystemExit(result.exit_code)


if __name__ == "__main__":
    cli()
