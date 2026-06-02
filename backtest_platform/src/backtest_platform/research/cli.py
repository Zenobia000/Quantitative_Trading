"""Research-loop CLI — formalizes the one-off-script workflow.

    uv run python -m backtest_platform.research.cli run-is \\
        --preset v3 --hypothesis "v3 放寬是否在雙窗有一致正期望" \\
        --stocks 2330,1101,1303 --start 2020-01-01 --end 2024-12-31

Builds a RunConfig (forces a hypothesis), runs the IS sim, judges it with the
gate_state審判庭, prints逐條綠紅, and appends the result to the runs ledger —
turning '手寫 script 半天' into one disciplined, lineage-bearing command.
"""
from __future__ import annotations

from datetime import datetime

import click

from backtest_platform.research.is_harness import run_and_judge
from backtest_platform.research.run_config import RunConfig
from backtest_platform.research.runs_store import DEFAULT_RUNS_PATH, append_run, read_runs


@click.group()
def cli() -> None:
    """Research loop: run-is / runs."""


@cli.command("run-is")
@click.option("--preset", required=True, help="StrategyConfig preset (v2 / v3 / ...)")
@click.option("--hypothesis", required=True, help="預先註冊：這個 run 在驗什麼（強制）")
@click.option("--stocks", required=True, help="Comma-separated stock_ids")
@click.option("--start", required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option("--end", required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option("--runs-path", default=str(DEFAULT_RUNS_PATH), show_default=True)
def run_is_cmd(preset, hypothesis, stocks, start, end, runs_path) -> None:
    cfg = RunConfig(
        hypothesis=hypothesis,
        preset=preset,
        stocks=tuple(s.strip() for s in stocks.split(",") if s.strip()),
        is_start=start.date(),
        is_end=end.date(),
    )
    rec = run_and_judge(cfg)
    append_run(rec, runs_path)
    click.echo(f"\nrun_id={rec['run_id']}  preset={preset}  [{rec['gate_status']}]")
    click.echo(rec["gate_summary"])
    m = rec["metrics"]
    click.echo(
        f"  metrics: trades={m.get('trades')} cagr={m.get('cagr'):.4f} "
        f"sharpe={m.get('sharpe'):.3f} struct1%={m.get('struct1_pct'):.2f} "
        f"churn%={m.get('churn_pct'):.2f} avg_hold={m.get('avg_hold'):.1f}"
    )
    click.echo(f"  → appended to {runs_path}")


@cli.command("runs")
@click.option("--runs-path", default=str(DEFAULT_RUNS_PATH), show_default=True)
def runs_cmd(runs_path) -> None:
    """List the runs ledger (run_id / preset / gate / hypothesis)."""
    runs = read_runs(runs_path)
    if not runs:
        click.echo(f"no runs in {runs_path}")
        return
    for r in runs:
        click.echo(
            f"{r.get('run_id')}  {r.get('preset'):4}  [{r.get('gate_status'):10}]  "
            f"{r.get('hypothesis')}"
        )


if __name__ == "__main__":
    cli()
