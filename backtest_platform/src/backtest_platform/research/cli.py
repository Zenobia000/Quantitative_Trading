"""Research-loop CLI — formalizes the one-off-script workflow.

    uv run python -m backtest_platform.research.cli run-is \\
        --preset v3 --hypothesis "v3 放寬是否在雙窗有一致正期望" \\
        --stocks 2330,1101,1303 --start 2020-01-01 --end 2024-12-31

Builds a RunConfig (forces a hypothesis), runs the IS sim, judges it with the
gate_state審判庭, prints逐條綠紅, and appends the result to the runs ledger —
turning '手寫 script 半天' into one disciplined, lineage-bearing command.
"""
from __future__ import annotations

from pathlib import Path

import click

from backtest_platform.research.is_harness import run_and_judge_with_returns
from backtest_platform.research.run_config import RunConfig
from backtest_platform.research.runs_store import DEFAULT_RUNS_PATH, append_run, read_runs
from backtest_platform.validation.gate_machine import GateState, ValidationGate
from backtest_platform.validation.tearsheet import write_tearsheet


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
@click.option(
    "--tearsheet", is_flag=True, default=False,
    help="額外輸出 quantstats HTML tear sheet（需 validation extra）",
)
@click.option(
    "--tearsheet-dir", default="reports/tearsheets", show_default=True,
    help="tear sheet 輸出目錄（檔名 = <run_id>.html）",
)
def run_is_cmd(preset, hypothesis, stocks, start, end, runs_path, tearsheet, tearsheet_dir) -> None:
    cfg = RunConfig(
        hypothesis=hypothesis,
        preset=preset,
        stocks=tuple(s.strip() for s in stocks.split(",") if s.strip()),
        is_start=start.date(),
        is_end=end.date(),
    )
    rec, returns = run_and_judge_with_returns(cfg)
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
    if tearsheet:
        out_path = Path(tearsheet_dir) / f"{rec['run_id']}.html"
        written = write_tearsheet(
            returns, out_path, title=f"{preset} IS {cfg.is_start}..{cfg.is_end}"
        )
        if written is not None:
            click.echo(f"  → tear sheet: {written}")
        else:
            click.echo("  → tear sheet skipped（quantstats 不可用 / 資料 < 2 bars）")


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


@cli.command("compare")
@click.option("--runs-path", default=str(DEFAULT_RUNS_PATH), show_default=True)
@click.option("--baseline", default=None, help="run_id to diff against (delta vs baseline)")
def compare_cmd(runs_path, baseline) -> None:
    """Compare runs in the ledger (rank + delta vs baseline + sign consistency)."""
    from backtest_platform.research.compare import compare_runs

    records = read_runs(runs_path)
    if not records:
        click.echo(f"no runs in {runs_path}")
        return
    rep = compare_runs(records, baseline_id=baseline)
    click.echo(f"baseline={rep.baseline_id}  sign_consistent={rep.sign_consistent}")
    for c in rep.comparisons:
        base = " (baseline)" if c.is_baseline else ""
        delta = " ".join(f"{k}Δ{v:+.3f}" for k, v in (c.delta or {}).items()) if c.delta else ""
        rank_sharpe = c.rank.get("sharpe", "?") if isinstance(c.rank, dict) else c.rank
        click.echo(
            f"  rank(sharpe)={rank_sharpe} {c.run_id} [{c.gate_status}]{base}  "
            f"cagr={c.metrics.get('cagr', float('nan')):.4f} "
            f"sharpe={c.metrics.get('sharpe', float('nan')):.3f}  {delta}"
        )


@cli.command("validate")
@click.option("--run-id", required=True, help="ledger 內要驗的 run_id")
@click.option("--runs-path", default=str(DEFAULT_RUNS_PATH), show_default=True)
def validate_cmd(run_id, runs_path) -> None:
    """Drive a ledger run through the IS→WFA→OOS 工作流 gate (IS phase).

    Unlike `run-is`（唯讀審判庭），this feeds the run's IS metrics into the
    *stateful* ``ValidationGate``: PASS → IS_PASS（WFA 解鎖）；否則 FAILED。也回報
    OOS sealed-vault 狀態（OOS 在 IS+WFA 都通過前保持封存，防 look-ahead leak）。
    """
    records = read_runs(runs_path)
    rec = next((r for r in records if str(r.get("run_id")) == run_id), None)
    if rec is None:
        raise click.ClickException(f"run {run_id!r} not found in {runs_path}")

    metrics = rec.get("metrics") or {}
    gate = ValidationGate()
    state = gate.submit_is(metrics)
    result = gate.last_is_result

    click.echo(
        f"run_id={run_id}  preset={rec.get('preset')}  hypothesis={rec.get('hypothesis')}"
    )
    click.echo(result.summary())
    click.echo(f"\nGATE STATE: {state.value}")
    if state is GateState.IS_PASS:
        click.echo("  IS gate ✅ → WFA 已解鎖（submit WFA 結果後才解 OOS）")
    else:
        failing = [r.criterion.label for r in result.failing()]
        missing = [r.criterion.label for r in result.missing()]
        if failing:
            click.echo(f"  IS gate ❌ FAIL：{', '.join(failing)}")
        if missing:
            click.echo(f"  IS gate ⚠ INCOMPLETE（缺指標）：{', '.join(missing)}")
    click.echo(
        f"  OOS vault：{'UNSEALED' if gate.oos_unsealed else 'SEALED（IS+WFA 通過前不可讀）'}"
    )


# Forward path IS_PASS → … → APPROVED, with the human label for the phase each
# state *clears*. Promotion to live requires reaching APPROVED (all four cleared).
_PROMOTION_PHASES: tuple[tuple[GateState, str], ...] = (
    (GateState.IS_PASS, "IS gate"),
    (GateState.WFA_PASS, "WFA"),
    (GateState.OOS_PASS, "OOS"),
    (GateState.APPROVED, "approve"),
)


def _resolve_validation_status(rec: dict) -> GateState:
    """A run's furthest-cleared workflow state.

    An explicit ``validation_status`` (written once v0.2 wires WFA/OOS into the
    ledger) is authoritative. Absent that, v0.1 records carry only the IS verdict,
    so we re-derive it through ``ValidationGate`` (single threshold source): IS
    PASS → IS_PASS, else FAILED. Never fabricates progress past what is recorded.
    """
    raw = rec.get("validation_status")
    if raw:
        try:
            return GateState(raw)
        except ValueError:
            pass
    return ValidationGate().submit_is(rec.get("metrics") or {})


def _outstanding_phases(state: GateState) -> list[str]:
    """Phases still blocking promotion, from ``state`` up to APPROVED.

    A cleared forward state lists only the phases above it. FAILED / PENDING have
    cleared nothing on the promotion path → every phase is outstanding (must
    re-clear IS first).
    """
    order = [st for st, _ in _PROMOTION_PHASES]
    cleared = order.index(state) if state in order else -1
    return [label for i, (_, label) in enumerate(_PROMOTION_PHASES) if i > cleared]


@cli.command("promote-check")
@click.option("--run-id", required=True, help="ledger 內要查晉升資格的 run_id")
@click.option("--runs-path", default=str(DEFAULT_RUNS_PATH), show_default=True)
def promote_check_cmd(run_id, runs_path) -> None:
    """Read a run's validation_status and report promotion eligibility (read-only).

    A run is promotable to live **only** in state ``APPROVED`` (IS→WFA→OOS→approve
    all cleared). The v0.1 ledger records the IS verdict only, so a run that has
    merely passed IS is reported NOT eligible with the outstanding phases listed —
    promotion is never rubber-stamped on IS alone（防未驗證策略上線）.
    """
    records = read_runs(runs_path)
    rec = next((r for r in records if str(r.get("run_id")) == run_id), None)
    if rec is None:
        raise click.ClickException(f"run {run_id!r} not found in {runs_path}")

    state = _resolve_validation_status(rec)
    click.echo(
        f"run_id={run_id}  preset={rec.get('preset')}  hypothesis={rec.get('hypothesis')}"
    )
    click.echo(f"VALIDATION STATUS: {state.value}")
    if state is GateState.APPROVED:
        click.echo("  PROMOTE ✅ ELIGIBLE — IS→WFA→OOS→approve 全數通過，可晉升實盤")
        return
    click.echo("  PROMOTE ⛔ NOT ELIGIBLE — 晉升須 state=APPROVED（防未驗證策略上線）")
    outstanding = _outstanding_phases(state)
    if outstanding:
        click.echo(f"  待完成階段：{' → '.join(outstanding)}")
    if state is GateState.FAILED:
        click.echo("  （IS gate 未通過或無法完整評估；走 ADR-017 退場路徑回 M0 再設）")


def _coerce(v: str):
    v = v.strip()
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    for cast in (int, float):
        try:
            return cast(v)
        except ValueError:
            continue
    return v


@cli.command("sweep")
@click.option("--base-preset", default="v3.1b", show_default=True, help="StrategyConfig preset to sweep from")
@click.option("--grid", required=True, help="e.g. 'entry_min_layers=3,4;entry_confirm_days=1,2'")
@click.option("--stocks", required=True, help="Comma-separated stock_ids")
@click.option("--start", required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option("--end", required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option("--out-csv", default="reports/sweep.csv", show_default=True)
def sweep_cmd(base_preset, grid, stocks, start, end, out_csv) -> None:
    """Parameter sweep — expand a grid of StrategyConfigs, run each, emit the FULL
    grid (anti cherry-pick: never just the single best)."""
    import csv
    from pathlib import Path

    from backtest_platform.config.strategy_config import get_preset
    from backtest_platform.research.is_harness import load_merged_parquet
    from backtest_platform.research.sweep import expand_grid, run_sweep

    param_grid: dict[str, list] = {}
    for part in grid.split(";"):
        if not part.strip():
            continue
        k, vals = part.split("=")
        param_grid[k.strip()] = [_coerce(x) for x in vals.split(",")]

    base = get_preset(base_preset)
    configs = expand_grid(base, param_grid)
    syms = [s.strip() for s in stocks.split(",") if s.strip()]
    click.echo(f"sweep: {len(configs)} configs over {len(syms)} stocks {start.date()}..{end.date()}")
    results = run_sweep(syms, start.date(), end.date(), configs, loader=load_merged_parquet)

    if results:
        Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
        keys = sorted({k for r in results for k in r})
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(results)
        for r in results:
            click.echo(
                "  " + " ".join(f"{k}={r[k]}" for k in param_grid if k in r)
                + f"  → cagr={r.get('cagr', float('nan')):.4f} sharpe={r.get('sharpe', float('nan')):.3f}"
                + f" struct1%={r.get('struct1_pct', float('nan')):.2f}"
            )
        click.echo(f"  → full grid ({len(results)} rows) written to {out_csv}")


if __name__ == "__main__":
    cli()
