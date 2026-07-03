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


# --------------------------------------------------------------------------- #
# 觀察艙 (Paper-Watch) registry — ADR-033 enforcement surface                  #
# --------------------------------------------------------------------------- #
@cli.group("watch")
def watch_group() -> None:
    """Paper-Watch 觀察艙 registry: enroll / status (ADR-033 enforcement)."""


@watch_group.command("enroll")
@click.option("--strategy", required=True, help="strategy to admit to the觀察艙")
@click.option("--dsr", "verdict_dsr", type=float, required=True,
              help="the truth-gate DSR — must land in the PAPER_WATCH band [0.90, 0.95)")
@click.option("--enrolled-on", "enrolled_on", default=None,
              help="enrollment date (YYYY-MM-DD); default = today Asia/Taipei")
@click.option("--evidence", "re_enroll_evidence", default=None,
              help="fresh-evidence note required to re-enter after an earlier expiry/exit")
def watch_enroll_cmd(
    strategy: str, verdict_dsr: float, enrolled_on: str | None, re_enroll_evidence: str | None
) -> None:
    """Admit a PAPER_WATCH-band strategy to a zero-capital observation berth.

    Enforces the ADR-033 admission clauses (band / ≤ 2 berths / one-shot re-entry);
    a refused enrollment exits non-zero with the reason. This is the machine gate
    that decides *which* strategy may run paper — the after-close scheduler refuses
    any strategy without an active berth."""
    from backtest_platform.research.watch_registry import WatchRegistryError, enroll

    on = date.fromisoformat(enrolled_on) if enrolled_on else _today_taipei()
    try:
        st = enroll(strategy, verdict_dsr, on, re_enroll_evidence=re_enroll_evidence)
    except WatchRegistryError as exc:
        raise click.ClickException(str(exc)) from None
    click.echo(
        f"🟡 {st.strategy} enrolled — state={st.state} DSR={st.verdict_dsr:.4g} "
        f"進艙 {st.enrolled_on} → 到期 {st.expiry_date}（剩 {st.days_remaining} 天）"
    )


@watch_group.command("status")
@click.option("--strategy", default=None, help="one strategy; omit for all berths")
def watch_status_cmd(strategy: str | None) -> None:
    """Show觀察艙 berths: 進艙日 / 已觀察交易日 / 到期日 / 剩餘天數 / 狀態."""
    from backtest_platform.research.watch_registry import (
        NOMINAL_TRADING_DAYS,
        active_watches,
        status,
    )

    if strategy is not None:
        st = status(strategy)
        if st is None:
            click.echo(f"{strategy}: 無觀察艙紀錄（未進艙）")
            return
        rows = [st]
    else:
        rows = active_watches()
        if not rows:
            click.echo("觀察艙目前無 active 艙位。")
            return

    for st in rows:
        click.echo(
            f"[{st.state}] {st.strategy}  進艙 {st.enrolled_on}  "
            f"觀察日 {st.observed_trading_days}/~{NOMINAL_TRADING_DAYS}  "
            f"到期 {st.expiry_date}  剩 {st.days_remaining} 天  DSR={st.verdict_dsr:.4g}"
        )


@watch_group.command("pause")
@click.option("--strategy", required=True, help="active berth to pause (app-level)")
def watch_pause_cmd(strategy: str) -> None:
    """App-level pause: after-close skips this berth (benign, no Discord) while it
    keeps its enrollment / expiry clock. Idempotent; only an active berth may pause.
    Mirrors the GUI ``POST /monitor/watch/{strategy}/pause``."""
    from backtest_platform.research.watch_registry import WatchRegistryError, pause

    try:
        st = pause(strategy)
    except WatchRegistryError as exc:
        raise click.ClickException(str(exc)) from None
    click.echo(f"⏸  {st.strategy} paused — after-close 將略過（保留到期 {st.expiry_date}）")


@watch_group.command("resume")
@click.option("--strategy", required=True, help="paused berth to resume")
def watch_resume_cmd(strategy: str) -> None:
    """Resume a paused berth back to active (after-close resumes collecting OOS).
    Idempotent; only a paused berth may resume. Mirrors ``POST .../{strategy}/resume``."""
    from backtest_platform.research.watch_registry import WatchRegistryError, resume

    try:
        st = resume(strategy)
    except WatchRegistryError as exc:
        raise click.ClickException(str(exc)) from None
    click.echo(f"▶  {st.strategy} resumed — state={st.state}（剩 {st.days_remaining} 天）")


# --------------------------------------------------------------------------- #
# live-OOS queue — the human-selection layer the after-close scheduler consumes #
# --------------------------------------------------------------------------- #
@cli.group("live-oos")
def live_oos_group() -> None:
    """Live-OOS queue: consume human-selected candidates into paper/live OOS (Goal 10)."""


@live_oos_group.command("consume")
@click.option("--date", "date_str", default=None,
              help="as-of session (YYYY-MM-DD); default = today Asia/Taipei")
def live_oos_consume_cmd(date_str: str | None) -> None:
    """Consume the queue: enroll selected berths, run selected replays, sync berth state.

    ONLY human-selected queue items run — an unselected candidate never auto-runs
    (Goal 10 acceptance #1). Berth enrollment is now queue-driven (ADR-040): this is
    the primary path that gives the after-close scheduler its active berths. Meant to
    fire on the same after-close tick, *before* the per-strategy session — see
    ``deploy/after-close.service`` (``ExecStartPre``) and ``deploy/README``. Always exits
    0 on a normal tick (an empty queue is a clean no-op)."""
    from backtest_platform.research.live_oos_consumer import consume_queue

    as_of = date.fromisoformat(date_str) if date_str else _today_taipei()
    report = consume_queue(as_of)
    click.echo(
        f"live-oos consume {as_of}: enrolled={list(report.enrolled)} "
        f"replayed={list(report.replayed)} synced={list(report.synced)} "
        f"skipped={list(report.skipped)}"
    )


@live_oos_group.command("list")
@click.option("--state", default=None,
              help="filter by queue state (queued/running/paused/completed/expired/cancelled)")
def live_oos_list_cmd(state: str | None) -> None:
    """List the live-OOS queue: latest folded state, kind and selection audit per item."""
    from backtest_platform.research.live_oos_queue import list_queue

    items = list_queue(state=state)
    if not items:
        click.echo("live-oos 佇列目前為空。" if state is None else f"live-oos 佇列無 {state} 項。")
        return
    for it in items:
        obs = it.get("observation", {})
        click.echo(
            f"[{it['state']}] {it['queue_id']}  {it['strategy']}  kind={obs.get('kind')}  "
            f"override={it.get('override')}  reason={it.get('selection_reason')!r}"
        )


if __name__ == "__main__":
    cli()
