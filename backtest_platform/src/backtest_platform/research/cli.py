"""Research-loop CLI — formalizes the one-off-script workflow.

    uv run python -m backtest_platform.research.cli run-is \\
        --strategy momentum --params '{"lookback_days": 120}' \\
        --hypothesis "momentum edge check" \\
        --stocks 2330,1101,1303 --start 2020-01-01 --end 2024-12-31

    uv run python -m backtest_platform.research.cli validate-strategy momentum

Builds a RunConfig (forces a hypothesis), runs the IS sim, judges it with the
gate_state審判庭, prints逐條綠紅, and appends the result to the runs ledger.
"""
from __future__ import annotations

import json
from pathlib import Path

import click

from backtest_platform.research.is_harness import run_and_judge_with_returns
from backtest_platform.research.run_config import RunConfig
from backtest_platform.research.runs_store import DEFAULT_RUNS_PATH, append_run, read_runs
from backtest_platform.validation.gate_machine import (
    GateState,
    ValidationGate,
    coerce_gate_state,
    derive_is_state,
)
from backtest_platform.validation.tearsheet import write_tearsheet


@click.group()
def cli() -> None:
    """Research loop: run-is / validate-strategy / runs / compare / validate / sweep."""


@cli.command("run-is")
@click.option("--strategy", required=True, help="Registered strategy name (see validate-strategy --list)")
@click.option("--params", default="{}", help="JSON dict of strategy params (e.g. '{\"lookback_days\": 120}')")
@click.option("--hypothesis", required=True, help="預先註冊：這個 run 在驗什麼（強制）")
@click.option("--stocks", required=True, help="Comma-separated stock_ids")
@click.option("--start", required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option("--end", required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option("--runs-path", default=str(DEFAULT_RUNS_PATH), show_default=True)
@click.option("--tearsheet", is_flag=True, default=False,
              help="額外輸出 quantstats HTML tear sheet")
@click.option("--tearsheet-dir", default="reports/tearsheets", show_default=True)
def run_is_cmd(strategy, params, hypothesis, stocks, start, end, runs_path, tearsheet, tearsheet_dir) -> None:
    """Run a strategy IS backtest and append to the runs ledger."""
    from backtest_platform.research import runners as _runners  # noqa: F401
    params_dict = json.loads(params)
    cfg = RunConfig(
        hypothesis=hypothesis,
        strategy=strategy,
        params=params_dict,
        stocks=tuple(s.strip() for s in stocks.split(",") if s.strip()),
        is_start=start.date(),
        is_end=end.date(),
    )
    rec, returns = run_and_judge_with_returns(cfg)
    append_run(rec, runs_path)
    click.echo(f"\nrun_id={rec['run_id']}  strategy={strategy}  [{rec['gate_status']}]")
    click.echo(rec["gate_summary"])
    m = rec["metrics"]
    click.echo(
        f"  metrics: trades={m.get('trades')} cagr={m.get('cagr', float('nan')):.4f} "
        f"sharpe={m.get('sharpe', float('nan')):.3f} maxdd={m.get('maxdd', float('nan')):.4f}"
    )
    click.echo(f"  → appended to {runs_path}")
    if tearsheet:
        out_path = Path(tearsheet_dir) / f"{rec['run_id']}.html"
        written = write_tearsheet(
            returns, out_path, title=f"{strategy} IS {cfg.is_start}..{cfg.is_end}"
        )
        if written is not None:
            click.echo(f"  → tear sheet: {written}")
        else:
            click.echo("  → tear sheet skipped（quantstats 不可用 / 資料 < 2 bars）")


@cli.command("validate-strategy")
@click.argument("name", required=False)
@click.option("--list", "list_all", is_flag=True, default=False, help="List all registered strategies")
def validate_strategy_cmd(name: str | None, list_all: bool) -> None:
    """Run the conformance gate on a registered strategy and print the report.

    Usage:
      validate-strategy momentum
      validate-strategy --list
    """
    from backtest_platform.research import runners as _runners  # noqa: F401
    from backtest_platform.strategies.conformance import check_strategy
    from backtest_platform.strategies.protocol import list_strategies

    if list_all:
        for n in list_strategies():
            click.echo(n)
        return

    if not name:
        raise click.UsageError("provide a strategy name or --list")

    report = check_strategy(name)
    if report.ok:
        click.echo(f"[OK] strategy {name!r} conforms to the contract.")
    else:
        click.echo(f"[FAIL] strategy {name!r} failed conformance:", err=True)
        for e in report.errors:
            click.echo(f"  - {e}", err=True)
        raise SystemExit(1)


@cli.command("runs")
@click.option("--runs-path", default=str(DEFAULT_RUNS_PATH), show_default=True)
def runs_cmd(runs_path) -> None:
    """List the runs ledger (run_id / strategy / gate / hypothesis)."""
    runs = read_runs(runs_path)
    if not runs:
        click.echo(f"no runs in {runs_path}")
        return
    for r in runs:
        strat = r.get("strategy") or r.get("preset", "?")
        click.echo(
            f"{r.get('run_id')}  {strat:12}  [{r.get('gate_status'):10}]  "
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
    """Drive a ledger run through the IS→WFA→OOS 工作流 gate (IS phase)."""
    records = read_runs(runs_path)
    rec = next((r for r in records if str(r.get("run_id")) == run_id), None)
    if rec is None:
        raise click.ClickException(f"run {run_id!r} not found in {runs_path}")

    metrics = rec.get("metrics") or {}
    gate = ValidationGate()
    state = gate.submit_is(metrics)
    result = gate.last_is_result
    strat = rec.get("strategy") or rec.get("preset", "?")

    click.echo(f"run_id={run_id}  strategy={strat}  hypothesis={rec.get('hypothesis')}")
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


_PROMOTION_PHASES: tuple[tuple[GateState, str], ...] = (
    (GateState.IS_PASS, "IS gate"),
    (GateState.WFA_PASS, "WFA"),
    (GateState.OOS_PASS, "OOS"),
    (GateState.APPROVED, "approve"),
)


def _resolve_validation_status(rec: dict) -> GateState:
    state = coerce_gate_state(rec.get("validation_status"))
    if state is not None:
        return state
    return derive_is_state(rec.get("metrics") or {})


def _outstanding_phases(state: GateState) -> list[str]:
    order = [st for st, _ in _PROMOTION_PHASES]
    cleared = order.index(state) if state in order else -1
    return [label for i, (_, label) in enumerate(_PROMOTION_PHASES) if i > cleared]


@cli.command("promote-check")
@click.option("--run-id", required=True, help="ledger 內要查晉升資格的 run_id")
@click.option("--runs-path", default=str(DEFAULT_RUNS_PATH), show_default=True)
def promote_check_cmd(run_id, runs_path) -> None:
    """Report promotion eligibility for a run (read-only)."""
    records = read_runs(runs_path)
    rec = next((r for r in records if str(r.get("run_id")) == run_id), None)
    if rec is None:
        raise click.ClickException(f"run {run_id!r} not found in {runs_path}")

    state = _resolve_validation_status(rec)
    strat = rec.get("strategy") or rec.get("preset", "?")
    click.echo(f"run_id={run_id}  strategy={strat}  hypothesis={rec.get('hypothesis')}")
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
@click.option("--strategy", default="four_layer", show_default=True, help="Strategy to sweep")
@click.option("--base-params", default="{}", show_default=True, help="Base params JSON for the strategy")
@click.option("--grid", required=True, help="e.g. 'entry_min_layers=3,4;entry_confirm_days=1,2'")
@click.option("--stocks", required=True, help="Comma-separated stock_ids")
@click.option("--start", required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option("--end", required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option("--out-csv", default="reports/sweep.csv", show_default=True)
def sweep_cmd(strategy, base_params, grid, stocks, start, end, out_csv) -> None:
    """Parameter sweep over a strategy's config grid."""
    import csv

    from backtest_platform.research import runners as _runners  # noqa: F401
    from backtest_platform.research.is_harness import load_merged_parquet
    from backtest_platform.research.sweep import expand_grid, run_sweep
    from backtest_platform.strategies.protocol import get_strategy

    param_grid: dict[str, list] = {}
    for part in grid.split(";"):
        if not part.strip():
            continue
        k, vals = part.split("=")
        param_grid[k.strip()] = [_coerce(x) for x in vals.split(",")]

    runner = get_strategy(strategy)
    base = runner.config_model(**json.loads(base_params))
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
            )
        click.echo(f"  → full grid ({len(results)} rows) written to {out_csv}")


# ── Research workflow commands (ADR-029) ────────────────────────────────────
# Each reads strategies/<name>/research_config.py and drives the generic workflow
# in research/workflows/ through the ADR-028 dispatch layer.


def _override_window(cfg, is_start: str | None, is_end: str | None):
    """Return a copy of ``cfg`` with is_start/is_end overridden from ISO strings."""
    from datetime import date as _date
    updates = {}
    if is_start:
        updates["is_start"] = _date.fromisoformat(is_start)
    if is_end:
        updates["is_end"] = _date.fromisoformat(is_end)
    return cfg.model_copy(update=updates) if updates else cfg


@cli.command("doe")
@click.option("--strategy", required=True, help="Registered strategy name")
@click.option("--dry-run", is_flag=True, default=False, help="Print config and exit")
@click.option("--is-start", default=None, help="Override is_start (YYYY-MM-DD)")
@click.option("--is-end", default=None, help="Override is_end (YYYY-MM-DD)")
@click.option("--out-csv", default=None, help="Write the full result grid to CSV")
def doe_cmd(strategy, dry_run, is_start, is_end, out_csv) -> None:
    """DOE parameter grid scan — reads research_config.DOE for the strategy."""
    from backtest_platform.research.workflows.loader import get_doe_config
    try:
        cfg = get_doe_config(strategy)
    except (ValueError, AttributeError) as exc:
        raise click.ClickException(str(exc)) from None
    cfg = _override_window(cfg, is_start, is_end)
    if dry_run:
        click.echo(f"[dry-run] DOEConfig for {strategy!r}:")
        click.echo(f"  grid={cfg.grid}  n_configs={cfg.n_configs}")
        click.echo(f"  symbols={len(cfg.symbols)} stocks  {cfg.is_start}..{cfg.is_end}")
        return
    from backtest_platform.research.is_harness import load_merged_parquet
    from backtest_platform.research.workflows.doe import run_doe
    click.echo(f"Running DOE for {strategy!r}: {cfg.n_configs} configs…")
    result = run_doe(cfg, loader=load_merged_parquet)
    for r in result.runs:
        params = {k: r[k] for k in cfg.grid if k in r}
        click.echo(f"  {params}  → cagr={r.get('cagr', float('nan')):.4f} "
                   f"sharpe={r.get('sharpe', float('nan')):.3f}")
    if out_csv and result.runs:
        import csv
        from pathlib import Path
        Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
        keys = sorted(result.runs[0].keys())
        with open(out_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(result.runs)
        click.echo(f"  → {out_csv}")


@cli.command("go-gates")
@click.option("--strategy", required=True)
@click.option("--dry-run", is_flag=True, default=False)
def go_gates_cmd(strategy, dry_run) -> None:
    """WFA + PBO GO-gates — reads research_config.GO_GATES for the strategy."""
    from backtest_platform.research.workflows.loader import get_go_gates_config
    try:
        cfg = get_go_gates_config(strategy)
    except (ValueError, AttributeError) as exc:
        raise click.ClickException(str(exc)) from None
    if dry_run:
        click.echo(f"[dry-run] GOGatesConfig for {strategy!r}:")
        click.echo(f"  symbols={len(cfg.symbols)}  folds={cfg.n_wfa_folds}  "
                   f"{cfg.is_start}..{cfg.is_end}")
        return
    from backtest_platform.research.is_harness import load_merged_parquet
    from backtest_platform.research.workflows.go_gates import run_go_gates
    click.echo(f"Running GO gates for {strategy!r}…")
    result = run_go_gates(cfg, loader=load_merged_parquet)
    click.echo(f"  verdict={result.verdict}  WFA OOS+={result.wfa_oos_positive_frac:.2%}  "
               f"PBO={result.pbo}")


@cli.command("truth-gate")
@click.option("--strategy", required=True)
@click.option("--dry-run", is_flag=True, default=False)
def truth_gate_cmd(strategy, dry_run) -> None:
    """ADR-025 two-stage truth gate — reads research_config.TRUTH_GATE."""
    from backtest_platform.research.workflows.loader import get_truth_gate_config
    try:
        cfg = get_truth_gate_config(strategy)
    except (ValueError, AttributeError) as exc:
        raise click.ClickException(str(exc)) from None
    if dry_run:
        click.echo(f"[dry-run] TruthGateConfig for {strategy!r}:")
        click.echo(f"  n_trials={cfg.n_trials}  pre_registered={cfg.pre_registered}")
        click.echo(f"  {cfg.is_start}..{cfg.oos_start}(OOS)..{cfg.is_end}")
        return
    from backtest_platform.research.is_harness import load_merged_parquet
    from backtest_platform.research.workflows.truth_gate import run_truth_gate
    click.echo(f"Running truth gate for {strategy!r}…")
    result = run_truth_gate(cfg, loader=load_merged_parquet)
    click.echo(f"  verdict={result.verdict}  DSR={result.dsr:.4f}  "
               f"slip_sharpe={result.slippage_sharpe:.3f}  "
               f"WFA OOS+={result.wfa_oos_positive_frac:.2%}")
    for r in result.reasons:
        click.echo(f"  ✗ {r}")


@cli.command("paper-replay")
@click.option("--strategy", required=True)
@click.option("--dry-run", is_flag=True, default=False)
def paper_replay_cmd(strategy, dry_run) -> None:
    """Paper replay — reads research_config.PAPER_REPLAY for the strategy."""
    from backtest_platform.research.workflows.loader import get_paper_replay_config
    try:
        cfg = get_paper_replay_config(strategy)
    except (ValueError, AttributeError) as exc:
        raise click.ClickException(str(exc)) from None
    if dry_run:
        click.echo(f"[dry-run] PaperReplayConfig for {strategy!r}:")
        click.echo(f"  as_of={cfg.as_of}  symbols={len(cfg.symbols)}  "
                   f"cash={cfg.initial_cash:,.0f}")
        return
    from backtest_platform.research.is_harness import load_merged_parquet
    from backtest_platform.research.workflows.paper_replay import run_paper_replay_workflow
    click.echo(f"Running paper replay for {strategy!r} as_of={cfg.as_of}…")
    result = run_paper_replay_workflow(cfg, loader=load_merged_parquet)
    click.echo(f"  run_id={result.run_id}  gate={result.gate_status}")
    click.echo(f"  cagr={result.metrics.get('cagr', float('nan')):.4f}  "
               f"sharpe={result.metrics.get('sharpe', float('nan')):.3f}")


if __name__ == "__main__":
    cli()
