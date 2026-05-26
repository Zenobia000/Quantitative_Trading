"""End-to-end smoke pipeline: ETL → scoring → signals → calendar report.

CLI usage::

    python -m backtest_platform.pipeline run --stock-id 2330 \\
        --start 2023-01-01 --end 2024-12-31

Pulls real data via FinMind, runs the v2.md pipeline, and prints the signal
calendar. Designed to validate the M1 implementation against real history.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import click
import pandas as pd
from loguru import logger

from backtest_platform.config.strategy_config import StrategyConfig
from backtest_platform.data.finmind_etl import fetch_bundle, write_parquet
from backtest_platform.strategy.scoring import compute_scores
from backtest_platform.strategy.signals import compute_signals


def run_pipeline(
    stock_id: str,
    start: date,
    end: date,
    parquet_dir: Path | None = None,
    config: StrategyConfig | None = None,
) -> pd.DataFrame:
    """Run the full M1 pipeline on real FinMind data. Returns scored+signaled frame."""
    config = config or StrategyConfig()

    bundle = fetch_bundle(stock_id, start, end)
    logger.info(
        "fetched stock={} rows daily={} inst={} chips={}",
        stock_id,
        len(bundle.daily_bars),
        len(bundle.institutional),
        len(bundle.broker_chips),
    )

    if parquet_dir:
        write_parquet(bundle, parquet_dir)

    merged = bundle.merged()
    if len(merged) < config.box_period + 5:
        logger.warning(
            "only {} bars after merge — need >= {} for any score to be non-NaN",
            len(merged),
            config.box_period + 5,
        )

    scored = compute_scores(merged, config)
    signaled = compute_signals(scored, config)
    return signaled


def signal_calendar(signaled: pd.DataFrame, config: StrategyConfig) -> pd.DataFrame:
    """Slim columns suitable for human review — one row per trading day."""
    # Drop warmup rows where scoring is NaN.
    ready = signaled.dropna(subset=["box_upper", "ma20"]).reset_index(drop=True)
    cols = [
        "trade_date",
        "close",
        "structure_score",
        "direction_score",
        "chip_score",
        "momentum_score",
        "total_score",
        "state_strong_buy",
        "state_hold",
        "state_warning",
        "state_flameout",
        "action",
        "in_position",
    ]
    return ready[cols]


def summary_stats(signaled: pd.DataFrame, config: StrategyConfig) -> dict:
    """Aggregate stats for milestone acceptance: signal frequencies, state distribution."""
    ready = signaled.dropna(subset=["box_upper", "ma20"])
    n = len(ready)
    if n == 0:
        return {"bars": 0}

    state_dist = {
        "strong_buy": int(ready["state_strong_buy"].sum()),
        "hold": int(ready["state_hold"].sum()),
        "warning": int(ready["state_warning"].sum()),
        "flameout": int(ready["state_flameout"].sum()),
    }
    action_counts = ready["action"].value_counts().to_dict()
    score_dist = ready["total_score"].describe().to_dict()
    buy_dates = ready.loc[ready["action"] == "buy", "trade_date"].tolist()
    exit_dates = ready.loc[ready["action"].isin(["stoploss", "exit"]), "trade_date"].tolist()

    return {
        "bars": n,
        "state_distribution": state_dist,
        "action_distribution": action_counts,
        "total_score_describe": score_dist,
        "buy_dates": [d.isoformat() for d in buy_dates],
        "exit_dates": [d.isoformat() for d in exit_dates],
    }


@click.group()
def cli() -> None:
    """End-to-end M1 pipeline."""


@cli.command("run")
@click.option("--stock-id", required=True)
@click.option("--start", required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option("--end", required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option(
    "--parquet-dir",
    type=click.Path(path_type=Path),
    default=Path("data/parquet"),
    help="Where to cache parquet files.",
)
@click.option(
    "--report-dir",
    type=click.Path(path_type=Path),
    default=Path("reports"),
    help="Where to write calendar CSV and summary JSON.",
)
def run_cmd(
    stock_id: str,
    start: datetime,
    end: datetime,
    parquet_dir: Path,
    report_dir: Path,
) -> None:
    """Pull → score → signal → report."""
    config = StrategyConfig()
    signaled = run_pipeline(stock_id, start.date(), end.date(), parquet_dir, config)

    report_dir.mkdir(parents=True, exist_ok=True)
    calendar = signal_calendar(signaled, config)
    cal_path = report_dir / f"calendar__{stock_id}__{start.date()}__{end.date()}.csv"
    calendar.to_csv(cal_path, index=False)
    logger.info("calendar written -> {}", cal_path)

    stats = summary_stats(signaled, config)
    print("\n=== Signal Calendar (last 20 rows) ===")
    print(calendar.tail(20).to_string(index=False))
    print("\n=== Summary ===")
    print(f"Bars (after warmup): {stats['bars']}")
    if stats["bars"] > 0:
        print(f"State distribution : {stats['state_distribution']}")
        print(f"Action counts      : {stats['action_distribution']}")
        print(f"Buy dates ({len(stats['buy_dates'])}): {stats['buy_dates'][:10]}")
        print(f"Exit dates ({len(stats['exit_dates'])}): {stats['exit_dates'][:10]}")
        s = stats["total_score_describe"]
        print(
            f"Total score : mean={s['mean']:.2f} std={s['std']:.2f} "
            f"min={s['min']:.0f} max={s['max']:.0f}"
        )


if __name__ == "__main__":
    cli()
