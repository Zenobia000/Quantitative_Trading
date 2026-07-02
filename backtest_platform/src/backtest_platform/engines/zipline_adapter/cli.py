"""CLI entry for zipline-reloaded adapter (plan v3.0 §10 Day 6-7).

Wraps `zipline.run_algorithm()` programmatic API (not the `zipline run`
subprocess CLI) so we can cleanly inject:
- UNIVERSE_FINMIND env (single point of truth, no shell-quoted lists)
- ZIPLINE_ROOT pointing to project-local data/zipline (not ~/.zipline)
- quantstats tearsheet generation post-backtest
- Discord notify hook (M4+ — currently stub)

Usage:
    uv run python -m backtest_platform.engines.zipline_adapter.cli backtest-run \\
        --stocks 2330 --start 2024-01-15 --end 2024-02-29 \\
        --capital-base 1000000 --tearsheet

Why programmatic over `zipline run`:
    1. zipline CLI doesn't pass through arbitrary env vars cleanly on Windows
    2. tearsheet generation needs the perf DataFrame in same process
    3. easier to add Discord notification / DB persistence hooks
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import click
import pandas as pd
from loguru import logger

from backtest_platform.validation.metrics import sharpe


def _ensure_bundle_registered():
    """Register the finmind bundle with zipline (explicit call, dependency-untangle).

    Registration is no longer an import-time side-effect; this wraps the explicit
    ``finmind_bundle.ensure_registered()`` so every zipline entry point in this CLI
    (``backtest-run`` before ``run_algorithm``, ``list-bundles``) opts in the same way.
    """
    from backtest_platform.engines.zipline_adapter.bundles import finmind_bundle

    finmind_bundle.ensure_registered()


def _resolve_zipline_root(explicit: Path | None) -> Path:
    """Choose ZIPLINE_ROOT in priority: explicit flag > env > project-local default."""
    if explicit:
        return explicit.resolve()
    if "ZIPLINE_ROOT" in os.environ:
        return Path(os.environ["ZIPLINE_ROOT"]).resolve()
    return (Path.cwd() / "data" / "zipline").resolve()


def _format_perf_summary(perf: pd.DataFrame, capital_base: float) -> dict:
    """Extract scalar summary from zipline perf DataFrame.

    perf is the daily result frame returned by run_algorithm; columns include
    portfolio_value, returns, alpha/beta if benchmark set, plus our `record()`
    output (n_evaluated, action_*).
    """
    if perf.empty:
        return {"bars": 0, "final_value": capital_base, "total_return": 0.0}

    final_value = float(perf["portfolio_value"].iloc[-1])
    total_return = (final_value / capital_base) - 1.0

    # Trade counts from actual fills (ground truth). The per-bar action_*
    # values recorded via zipline `record()` are FORWARD-FILLED on days an
    # action is absent (record only writes the keys present that bar), so
    # summing them yields meaningless inflated totals — e.g. a single early
    # "buy" reads as ~1000 "buys" over a multi-year run. Count transactions.
    n_buys = n_sells = 0
    if "transactions" in perf.columns:
        for txns in perf["transactions"]:
            if isinstance(txns, list):
                for t in txns:
                    amt = t.get("amount", 0)
                    if amt > 0:
                        n_buys += 1
                    elif amt < 0:
                        n_sells += 1

    summary = {
        "bars": len(perf),
        "start": str(perf.index[0].date()),
        "end": str(perf.index[-1].date()),
        "capital_base": capital_base,
        "final_value": final_value,
        "total_return": total_return,
        "n_evaluated_total": int(perf["n_evaluated"].fillna(0).sum()) if "n_evaluated" in perf else 0,
        "n_buys": n_buys,
        "n_sells": n_sells,
        "n_round_trips": min(n_buys, n_sells),
    }

    # quantstats / empyrical compatible — only when we have ≥2 bars
    if len(perf) >= 2:
        returns = perf["returns"].fillna(0)
        summary["mean_daily_return"] = float(returns.mean())
        summary["std_daily_return"] = float(returns.std())
        if summary["std_daily_return"] > 0:
            # canonical estimator (ADR-027 Stage 2) — single source of truth
            summary["sharpe_naive"] = sharpe(returns)

    return summary


def _maybe_write_tearsheet(
    perf: pd.DataFrame, output_dir: Path, run_id: str
) -> Path | None:
    """quantstats tearsheet HTML if package available + ≥2 bars.

    Gracefully degrades to no-op if quantstats missing (validation extra).
    """
    if len(perf) < 2:
        logger.warning("not enough bars for tearsheet (got {})", len(perf))
        return None
    try:
        import quantstats as qs
    except ImportError:
        logger.warning("quantstats not installed; pip install quantstats")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"tearsheet__{run_id}.html"
    returns = perf["returns"].copy()
    returns.index = pd.to_datetime(returns.index)
    qs.reports.html(returns, output=str(out_path), title=f"FourLayerResonance {run_id}")
    return out_path


def _maybe_notify_discord(summary: dict, run_id: str) -> None:
    """Post run summary to Discord (M4+ — currently best-effort stub).

    Skips silently if DISCORD_BOT_TOKEN not set, so backtest CLI works
    without Discord configuration.
    """
    if not os.environ.get("DISCORD_BOT_TOKEN"):
        logger.debug("DISCORD_BOT_TOKEN not set; skipping Discord notify")
        return
    try:
        from backtest_platform.monitoring.discord_notifier import DiscordNotifier
    except ImportError:
        logger.warning("monitoring/discord_notifier not available")
        return

    try:
        notifier = DiscordNotifier()
        msg = (
            f"**Backtest finished** `{run_id}`\n"
            f"Period: {summary['start']} → {summary['end']} ({summary['bars']} bars)\n"
            f"Total return: **{summary['total_return']:.4%}**\n"
            f"Final value: NT$ {summary['final_value']:,.0f}\n"
            f"Trades: {summary['n_round_trips']} round-trips "
            f"({summary['n_buys']} buys / {summary['n_sells']} sells)"
        )
        notifier.send(content=msg)
    except Exception as exc:
        logger.warning("Discord notify failed: {}", exc)


@click.group()
def cli():
    """zipline-reloaded adapter CLI — backtest / paper / live entry points."""
    # Load .env (FINMIND_TOKEN etc.) so `ingest`/`backtest-run` pick up secrets
    # from the gitignored .env without an explicit shell export. No-op if absent.
    from dotenv import load_dotenv

    load_dotenv()


@cli.command("backtest-run")
@click.option("--stocks", required=True, help="Comma-separated stock_ids, e.g. 2330,2454")
@click.option(
    "--start", required=True, type=click.DateTime(formats=["%Y-%m-%d"])
)
@click.option(
    "--end", required=True, type=click.DateTime(formats=["%Y-%m-%d"])
)
@click.option("--capital-base", default=1_000_000, type=float, show_default=True)
@click.option("--bundle", default="finmind", show_default=True)
@click.option(
    "--zipline-root",
    default=None,
    type=click.Path(path_type=Path),
    help="ZIPLINE_ROOT override (default: <cwd>/data/zipline)",
)
@click.option(
    "--output-dir",
    default=Path("reports"),
    type=click.Path(path_type=Path),
    show_default=True,
)
@click.option("--tearsheet/--no-tearsheet", default=False, show_default=True)
@click.option(
    "--discord-notify/--no-discord-notify",
    default=False,
    help="Post summary to Discord (requires DISCORD_BOT_TOKEN)",
)
@click.option(
    "--config",
    "config_preset",
    type=click.Choice(["v2", "v3"]),
    default="v2",
    show_default=True,
    help="StrategyConfig preset: v2 baseline / v3 relaxed entry (DEFAULT_CONFIG_V3)",
)
def backtest_run(
    stocks: str,
    start: datetime,
    end: datetime,
    capital_base: float,
    bundle: str,
    zipline_root: Path | None,
    output_dir: Path,
    tearsheet: bool,
    discord_notify: bool,
    config_preset: str,
) -> None:
    """Run a backtest with the four-layer resonance algorithm.

    Example:
        backtest-run --stocks 2330 --start 2024-01-15 --end 2024-02-29 --config v3
    """
    # Set env BEFORE importing zipline (bundle/algorithm read these at initialize)
    os.environ["UNIVERSE_FINMIND"] = stocks
    os.environ["STRATEGY_PRESET"] = config_preset
    zipline_root_resolved = _resolve_zipline_root(zipline_root)
    os.environ["ZIPLINE_ROOT"] = str(zipline_root_resolved)

    _ensure_bundle_registered()

    # Import after env is set (algorithm reads UNIVERSE_FINMIND at initialize)
    from zipline import run_algorithm

    from backtest_platform.engines.zipline_adapter.algorithms.four_layer_resonance import (
        handle_data,
        initialize,
    )

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info(
        "backtest-run: stocks={} {}..{} cap={:,.0f} root={}",
        stocks,
        start.date(),
        end.date(),
        capital_base,
        zipline_root_resolved,
    )

    perf = run_algorithm(
        start=pd.Timestamp(start),
        end=pd.Timestamp(end),
        initialize=initialize,
        handle_data=handle_data,
        capital_base=capital_base,
        bundle=bundle,
    )

    summary = _format_perf_summary(perf, capital_base)

    # Persist raw perf + summary
    output_dir.mkdir(parents=True, exist_ok=True)
    perf_path = output_dir / f"perf__{run_id}.pkl"
    summary_path = output_dir / f"summary__{run_id}.json"
    perf.to_pickle(perf_path)
    summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    logger.info("perf → {}", perf_path)
    logger.info("summary → {}", summary_path)

    # Console summary
    click.echo("\n=== Backtest Summary ===")
    click.echo(f"Period       : {summary['start']} → {summary['end']} ({summary['bars']} bars)")
    click.echo(f"Final value  : NT$ {summary['final_value']:,.0f}")
    click.echo(f"Total return : {summary['total_return']:.4%}")
    if "sharpe_naive" in summary:
        click.echo(f"Sharpe (naive): {summary['sharpe_naive']:.3f}")
    click.echo(
        f"Trades       : {summary['n_round_trips']} round-trips "
        f"({summary['n_buys']} buys / {summary['n_sells']} sells)"
    )

    if tearsheet:
        ts_path = _maybe_write_tearsheet(perf, output_dir, run_id)
        if ts_path:
            click.echo(f"Tearsheet    : {ts_path}")

    if discord_notify:
        _maybe_notify_discord(summary, run_id)


@cli.command("list-bundles")
def list_bundles():
    """Show registered zipline bundles (sanity check for `register()` side-effect)."""
    _ensure_bundle_registered()
    from zipline.data.bundles import bundles as _registry

    click.echo("Registered zipline bundles:")
    for name, entry in _registry.items():
        click.echo(f"  - {name:<25} calendar={entry.calendar_name}")


@cli.command("ingest")
@click.option("--start", required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option("--end", required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option(
    "--stocks",
    default=None,
    help="Comma-separated override; default = DEFAULT_UNIVERSE (10 檔)",
)
@click.option(
    "--cache-dir",
    default=None,
    type=click.Path(path_type=Path),
    help="parquet cache dir (default: data/parquet)",
)
@click.option("--dry-run/--no-dry-run", default=False, show_default=True)
def ingest(
    start: datetime,
    end: datetime,
    stocks: str | None,
    cache_dir: Path | None,
    dry_run: bool,
) -> None:
    """Batch-ingest a universe into the parquet cache (FinMind → parquet).

    Per-symbol failures are isolated by ``ingest_universe``; one bad symbol
    does not abort the batch. Exit 1 only when every symbol fails.

    Example:
        ingest --start 2020-01-01 --end 2024-12-31
    """
    from backtest_platform.engines.zipline_adapter.bundles import finmind_bundle

    universe = (
        [s.strip() for s in stocks.split(",") if s.strip()]
        if stocks
        else list(finmind_bundle.DEFAULT_UNIVERSE)
    )

    if dry_run:
        click.echo(
            f"[dry-run] would ingest {len(universe)} symbols "
            f"{start.date()}..{end.date()}"
        )
        for sym in universe:
            click.echo(f"  - {sym}")
        click.echo(f"cache_dir = {cache_dir or 'data/parquet (default)'}")
        return

    try:
        result = finmind_bundle.ingest_universe(
            universe, start=start.date(), end=end.date(), cache_dir=cache_dir
        )
    except RuntimeError as exc:
        click.echo(f"ingest failed — every symbol failed: {exc}", err=True)
        sys.exit(1)

    click.echo("\n=== Ingest Summary ===")
    click.echo(f"ok     : {len(result.bundles)} / {len(universe)}")
    if result.failed_symbols:
        click.echo(f"failed : {result.failed_symbols}")
    click.echo(f"cache  : {cache_dir or 'data/parquet'}")


if __name__ == "__main__":
    cli()
