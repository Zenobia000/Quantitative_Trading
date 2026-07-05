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
from backtest_platform.research.run_persist import persist_run
from backtest_platform.research.runs_store import DEFAULT_RUNS_PATH, read_runs
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


def _gate_for_record(rec: dict):
    """The审判庭 criteria for a ledger record — dispatched from its strategy.

    A run is judged only by its own strategy's declared gate (審查缺陷 #8), never a
    silent four-layer default. A record whose strategy is unknown / declares no
    gate fails loudly rather than being mis-judged.
    """
    from backtest_platform.research import runners as _runners  # noqa: F401 — register
    from backtest_platform.strategies.protocol import get_strategy_gate

    strat = rec.get("strategy") or rec.get("preset")
    if not strat:
        raise click.ClickException(
            f"run {rec.get('run_id')!r} has no strategy field; cannot dispatch a "
            f"validation gate (審查缺陷 #8)."
        )
    try:
        return get_strategy_gate(strat)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from None


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
    persist_run(rec, runs_path)  # ledger + best-effort runs-table mirror (A0)
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


@cli.command("run-batch")
@click.option("--strategy", required=True, help="Registered strategy name")
@click.option("--params", default="{}", help="JSON dict of strategy params（全組共用）")
@click.option("--hypothesis", required=True, help="預先註冊：這批 run 在驗什麼（強制，全組共用）")
@click.option("--stock-groups", required=True,
              help="分號分隔的股票組，組內逗號分隔：'2330,2317;2454;2308,2303' → 3 個平行 run")
@click.option("--start", required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option("--end", required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option("--max-workers", default=4, show_default=True, help="平行上限（threads）")
@click.option("--runs-path", default=str(DEFAULT_RUNS_PATH), show_default=True)
def run_batch_cmd(strategy, params, hypothesis, stock_groups, start, end, max_workers, runs_path) -> None:
    """Fan out one spec × N stock groups as parallel IS runs (A1).

    每組一個 run（決定性 run_id，重複組自動去重），runs 表鏡射
    running→done|failed 生命週期供 run board 讀取；失敗互相隔離。
    """
    from pydantic import ValidationError

    from backtest_platform.research import runners as _runners  # noqa: F401 — register
    from backtest_platform.research.batch import expand_stock_groups, run_batch

    groups = [
        [s.strip() for s in grp.split(",") if s.strip()]
        for grp in stock_groups.split(";") if grp.strip()
    ]
    if not groups:
        raise click.UsageError("--stock-groups produced no groups")
    base = {
        "hypothesis": hypothesis,
        "strategy": strategy,
        "params": json.loads(params),
        "is_start": start.date(),
        "is_end": end.date(),
    }
    try:
        configs = expand_stock_groups(base, groups)
    except (ValueError, ValidationError) as exc:
        raise click.ClickException(str(exc)) from None

    click.echo(f"batch: {len(configs)} runs（max_workers={max_workers}）…")
    results = run_batch(configs, runs_path=runs_path, max_workers=max_workers)

    failed = 0
    for r in results:
        if r["batch_status"] == "failed":
            failed += 1
            click.echo(f"  {r['run_id']}  [FAILED]  {r['error']}", err=True)
        else:
            m = r.get("metrics") or {}
            click.echo(
                f"  {r['run_id']}  [{r.get('gate_status'):10}]  "
                f"stocks={','.join(r.get('stocks', []))}  "
                f"sharpe={m.get('sharpe', float('nan')):.3f}"
            )
    click.echo(f"→ {len(results) - failed} done / {failed} failed，appended to {runs_path}")
    if failed:
        raise SystemExit(1)


@cli.command("portfolio-check")
@click.option("--candidate", required=True, help="候選 run_id（sidecar 需存在）")
@click.option("--fleet", default="", help="逗號分隔的艦隊 run_id（空 = 首艙位，組合==standalone）")
@click.option("--n-trials", default=1, show_default=True, help="候選的試驗數（DSR 通縮用）")
@click.option("--oos-sharpe", default=None, type=float, help="候選 OOS Sharpe（給定則附 ADR-025 sizing 建議權重）")
@click.option("--series-dir", default=None, help="run sidecar 目錄（預設 reports/series）")
def portfolio_check_cmd(candidate, fleet, n_trials, oos_sharpe, series_dir) -> None:
    """組合級證據軸（ADR-036）：候選 + 艦隊合成組合的 DSR vs standalone DSR。

    v1 限制：sidecar 無日期索引，跨 run 以「同窗口位置對齊」合成——
    長度不一致即拒絕（ADR-036 §3.4）。輸出是證據，不改寫 standalone verdict。
    """
    import pandas as pd

    from backtest_platform.research.run_series_store import read_series
    from backtest_platform.validation.portfolio_gate import portfolio_gate_report

    kwargs = {} if series_dir is None else {"series_dir": series_dir}

    def _returns(run_id: str) -> pd.Series:
        payload = read_series(run_id, **kwargs)
        equity = payload.get("equity") or []
        if len(equity) < 2:
            raise click.ClickException(f"run {run_id!r}: sidecar equity < 2 points")
        eq = pd.Series([1.0, *equity], dtype=float)  # equity[i] = prod(1+r[:i+1])
        return eq.pct_change().dropna().reset_index(drop=True)

    try:
        cand = _returns(candidate)
        fleet_ids = [f.strip() for f in fleet.split(",") if f.strip()]
        fleet_map = {fid: _returns(fid) for fid in fleet_ids}
    except FileNotFoundError as exc:
        raise click.ClickException(f"sidecar not found: {exc}") from None

    bad = [fid for fid, r in fleet_map.items() if len(r) != len(cand)]
    if bad:
        raise click.ClickException(
            f"positional alignment needs equal-length windows; mismatched vs candidate: {bad}"
        )

    rep = portfolio_gate_report(
        candidate, cand, fleet_map, n_trials=n_trials, candidate_oos_sharpe=oos_sharpe
    )
    click.echo(f"portfolio-check  candidate={candidate}  fleet={fleet_ids or '(empty)'}")
    click.echo(f"  standalone DSR      = {rep.standalone_dsr:.6f}")
    click.echo(f"  portfolio  DSR      = {rep.portfolio_dsr:.6f}")
    click.echo(f"  diversification Δ   = {rep.diversification_premium:+.6f}")
    click.echo(f"  corr to fleet       = {rep.correlation_to_fleet:+.4f}")
    if rep.suggested_weight is not None:
        click.echo(f"  suggested weight    = {rep.suggested_weight:.4f}  (ADR-025 sizing)")
    click.echo("  註：組合級 DSR 為證據軸（艦隊固定的條件性統計），不改寫 standalone verdict（ADR-036 §3.2）")


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
    gate = ValidationGate(gate=_gate_for_record(rec))
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
    return derive_is_state(rec.get("metrics") or {}, _gate_for_record(rec))


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
    """Return a copy of ``cfg`` with is_start/is_end overridden, RE-VALIDATED.

    Re-validates at the boundary (審查缺陷 #11) rather than ``model_copy(update=...)``:
    a malformed date, or an inverted is_start/is_end window, fails HERE as a clean
    ClickException — not a bare ValueError traceback, and not a silently-accepted
    illegal window that only explodes deep inside the workflow.
    """
    from pydantic import ValidationError

    from backtest_platform.research.workflows.config import revalidate_with_overrides

    overrides: dict[str, str] = {}
    if is_start:
        overrides["is_start"] = is_start
    if is_end:
        overrides["is_end"] = is_end
    try:
        return revalidate_with_overrides(cfg, overrides)
    except ValidationError as exc:
        msg = "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}"
                        for e in exc.errors())
        raise click.ClickException(f"invalid --is-start/--is-end override: {msg}") from None


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
        if cfg.parquet_dir:
            click.echo(f"  parquet_dir={cfg.parquet_dir}  survivorship_clean={cfg.survivorship_clean}")
        return
    from backtest_platform.research.workflows.truth_gate import run_truth_gate
    click.echo(f"Running truth gate for {strategy!r}…")
    # No explicit loader → cfg.parquet_dir (ADR-032) selects the data cache.
    result = run_truth_gate(cfg)
    click.echo(f"  verdict={result.verdict}  DSR={result.dsr:.4f}  "
               f"slip_sharpe={result.slippage_sharpe:.3f}  "
               f"WFA OOS+={result.wfa_oos_positive_frac:.2%}")
    if result.verdict == "PAPER_WATCH":
        click.echo("  🟡 觀察艙資格：零資本 paper 收 live OOS，3 個月到期"
                   f"（position_size={result.position_size:.3f}，晉升仍需 DSR ≥ 0.95）")
    for r in result.reasons:
        click.echo(f"  ✗ {r}")


@cli.command("build-universe")
@click.option("--strategy", required=True, help="Registered strategy name")
@click.option("--dry-run", is_flag=True, default=False, help="Print config and exit")
def build_universe_cmd(strategy, dry_run) -> None:
    """Build a survivorship-clean FinLab universe — reads research_config.UNIVERSE (ADR-032)."""
    from backtest_platform.research.workflows.loader import get_universe_config
    try:
        cfg = get_universe_config(strategy)
    except (ValueError, AttributeError, TypeError) as exc:
        raise click.ClickException(str(exc)) from None
    if dry_run:
        click.echo(f"[dry-run] UniverseConfig for {strategy!r}:")
        click.echo(f"  span={cfg.span_start}..{cfg.span_end}  top_n={cfg.top_n}  "
                   f"min_turnover={cfg.min_turnover:,.0f}  (quarterly rebalance)")
        click.echo(f"  cache_dir={cfg.cache_dir}")
        return
    from backtest_platform.research.workflows.universe import run_build_universe
    click.echo(f"Building survivorship-clean universe for {strategy!r} "
               f"({cfg.span_start}..{cfg.span_end})…")
    result = run_build_universe(cfg)
    click.echo(f"  universe={len(result.universe)} names  "
               f"alive={result.n_alive} delisted={result.n_delisted}")
    click.echo(f"  ingest ok={result.n_ingested_ok} failed={result.n_ingested_failed}")
    click.echo(f"  → manifest {result.manifest_path}")


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


# ── Evaluation orchestrator + candidate pool (rebuild Goal 3/4, ADR-039) ─────
# `evaluate` runs a high-level profile above the ADR-029 primitives and writes a
# report pack + persists the result; `candidates` manages the folded candidate pool.


@cli.command("evaluate")
@click.option("--strategy", required=True, help="Registered strategy name")
@click.option("--profile", required=True, help="quick_triage | fixed_hypothesis_oos | grid_search_selection | deployment_strict")
@click.option("--data-dir", default=None, help="Parquet cache dir for the loader (default data/parquet)")
@click.option("--symbols", default=None, help="Comma-separated symbols override (default: research_config universe)")
@click.option("--start", default=None, help="Override IS start (YYYY-MM-DD)")
@click.option("--end", default=None, help="Override IS end (YYYY-MM-DD)")
@click.option("--hypothesis", default=None, help="Pre-registered hypothesis for the run_id lineage")
@click.option("--no-ingest", is_flag=True, default=False, help="Do not create/update a candidate")
def evaluate_cmd(strategy, profile, data_dir, symbols, start, end, hypothesis, no_ingest) -> None:
    """Evaluate a strategy under an evaluation profile → report pack + persisted result."""
    from backtest_platform.research import candidate_store
    from backtest_platform.research.evaluation import evaluate

    syms = [s.strip() for s in symbols.split(",") if s.strip()] if symbols else None
    try:
        result = evaluate(
            strategy, profile, data_dir=data_dir, symbols=syms,
            is_start=start, is_end=end, hypothesis=hypothesis,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from None

    v = result["verdict"]
    click.echo(f"\nevaluation_id={result['evaluation_id']}  run_id={result['run_id']}")
    click.echo(f"  profile={result['profile']}  verdict={v['label']}  "
               f"truth={v['truth_verdict']}  live_oos={v['live_oos_recommendation']}")
    click.echo("  scorecards: " + "  ".join(f"{s['category']}={s['status']}" for s in result["scorecards"]))
    click.echo("  checks: " + ("  ".join(f"{c['metric']}={c['status']}" for c in result["checks"]) or "(none)"))
    click.echo(f"  → report pack: {result['report_pack_ref']}")
    if not no_ingest:
        cand = candidate_store.ingest_evaluation(result, hypothesis=hypothesis)
        click.echo(f"  → candidate {cand['candidate_id']} state={cand['state']} "
                   f"(next: {cand['next_action']})")


@cli.group("candidates")
def candidates_group() -> None:
    """Candidate pool: list / decide / select-live-oos (rebuild Goal 4)."""


@candidates_group.command("list")
@click.option("--state", default=None, help="Filter by candidate state")
@click.option("--strategy", default=None, help="Filter by strategy")
def candidates_list_cmd(state, strategy) -> None:
    """List candidates (folded from the pool + decision log)."""
    from backtest_platform.research.candidate_store import list_candidates

    cands = list_candidates(state=state, strategy=strategy)
    if not cands:
        click.echo("no candidates")
        return
    for c in cands:
        click.echo(
            f"{c['candidate_id']:26} {c['strategy']:14} [{c['state']:18}] "
            f"{c.get('latest_label') or '—':10} reco={c.get('live_oos_recommendation')}"
        )


@candidates_group.command("decide")
@click.option("--candidate", required=True, help="candidate_id (cand_<strategy>)")
@click.option("--action", required=True, help="keep | archive | rerun | mark_data_issue | unarchive")
@click.option("--label", default=None, help="keep target: promising | weak | negative")
@click.option("--reason", default=None, help="Required for archive (and any override)")
def candidates_decide_cmd(candidate, action, label, reason) -> None:
    """Append a candidate decision (state-machine validated)."""
    from backtest_platform.research.candidate_state import IllegalTransitionError
    from backtest_platform.research.candidate_store import (
        CandidateNotFoundError,
        MissingReasonError,
        record_decision,
    )

    try:
        dec = record_decision(candidate, action, target_label=label, reason=reason)
    except CandidateNotFoundError as exc:
        raise click.ClickException(str(exc)) from None
    except IllegalTransitionError as exc:
        raise click.ClickException(f"illegal transition: {exc}") from None
    except MissingReasonError as exc:
        raise click.ClickException(str(exc)) from None
    click.echo(f"{dec['decision_id']}  {dec['action']}  {dec['from_state']} → {dec['to_state']}")


@candidates_group.command("select-live-oos")
@click.option("--candidate", required=True, help="candidate_id (cand_<strategy>)")
@click.option("--reason", default=None, help="Required when recommendation != eligible / on override")
@click.option("--override", is_flag=True, default=False, help="Override a not-recommended / blocked candidate")
@click.option("--kind", default="paper_replay", help="paper_watch_berth | paper_replay | after_close")
def candidates_select_cmd(candidate, reason, override, kind) -> None:
    """Select a candidate for live OOS (enqueues a queue item + appends the decision)."""
    # This CLI command is the composition root for the research `candidates`
    # group: it is the one place allowed to wire the concrete governance-bound
    # live-OOS queue into candidate_store's injected enqueue port (W1.3/W2.1b).
    # The import-linter research ⊄ governance contract exempts exactly this edge.
    from backtest_platform.governance import live_oos_queue
    from backtest_platform.research.candidate_store import (
        BlockedSelectionError,
        CandidateNotFoundError,
        MissingReasonError,
        select_live_oos,
    )

    try:
        out = select_live_oos(
            candidate, reason=reason, override=override, observation_kind=kind,
            queue_path=live_oos_queue.DEFAULT_QUEUE_PATH, enqueue=live_oos_queue.enqueue,
        )
    except CandidateNotFoundError as exc:
        raise click.ClickException(str(exc)) from None
    except BlockedSelectionError as exc:
        raise click.ClickException(str(exc)) from None
    except (MissingReasonError, ValueError) as exc:
        raise click.ClickException(str(exc)) from None
    dec, item = out["decision"], out["queue_item"]
    click.echo(f"{dec['decision_id']}  {dec['action']}  {dec['from_state']} → {dec['to_state']}")
    click.echo(f"  → queued {item['queue_id']} (kind={item['observation']['kind']}, state={item['state']})")


# ── Branch experiments (rebuild Goal 9, ADR-041) ────────────────────────────
# Fork a branch from a parent evaluation with an explicit config delta, run it, and
# compare it against the parent — explicit lineage, never a silent in-place edit.


@cli.group("branches")
def branches_group() -> None:
    """Branch experiments: create / list / evaluate / compare (rebuild Goal 9)."""


def _parse_delta(pairs: tuple[str, ...]) -> list[dict]:
    """``--set key=value`` pairs → ``[{key, to}]`` (value coerced via ``_coerce``)."""
    delta: list[dict] = []
    for p in pairs:
        if "=" not in p:
            raise click.ClickException(f"--set expects key=value, got {p!r}")
        k, v = p.split("=", 1)
        delta.append({"key": k.strip(), "to": _coerce(v.strip())})
    return delta


@branches_group.command("create")
@click.option("--parent", "parent_evaluation_id", required=True, help="parent evaluation_id to fork from")
@click.option("--set", "sets", multiple=True, help="config delta key=value (repeatable)")
@click.option("--origin", default="manual", help="simulation | manual | report_finding")
@click.option("--profile", default="quick_triage", help="profile to evaluate the branch under")
@click.option("--note", default=None, help="why this branch")
def branches_create_cmd(parent_evaluation_id, sets, origin, profile, note) -> None:
    """Fork a branch from a parent evaluation (validates delta keys vs config_schema)."""
    from backtest_platform.research import branch_store

    try:
        branch = branch_store.create_branch(
            parent_evaluation_id, _parse_delta(sets), origin=origin, profile=profile, note=note,
        )
    except (branch_store.ParentNotFoundError, branch_store.IllegalDeltaError) as exc:
        raise click.ClickException(str(exc)) from None
    click.echo(f"{branch['branch_id']}  parent={branch['parent_run_id']}  status={branch['status']}")
    for d in branch["config_delta"]:
        click.echo(f"  {d['key']}: {d['from']} → {d['to']}")
    click.echo(f"  applies_to_rerun={branch['applies_to_rerun']}")


@branches_group.command("list")
@click.option("--strategy", default=None, help="Filter by strategy")
@click.option("--parent", "parent_evaluation_id", default=None, help="Filter by parent evaluation_id")
def branches_list_cmd(strategy, parent_evaluation_id) -> None:
    """List branch experiments (folded, newest-first)."""
    from backtest_platform.research.branch_store import list_branches

    branches = list_branches(strategy=strategy, parent_evaluation_id=parent_evaluation_id)
    if not branches:
        click.echo("no branches")
        return
    for b in branches:
        keys = ",".join(d["key"] for d in b["config_delta"])
        click.echo(
            f"{b['branch_id']:32} {b['strategy']:14} [{b['status']:9}] origin={b['origin']:14} Δ{keys}"
        )


@branches_group.command("evaluate")
@click.option("--branch", "branch_id", required=True, help="branch_id to evaluate")
@click.option("--data-dir", default=None, help="Parquet cache dir for the loader")
def branches_evaluate_cmd(branch_id, data_dir) -> None:
    """Run the branch config through the orchestrator; backfill its evaluation id."""
    from backtest_platform.research import branch_store

    try:
        out = branch_store.evaluate_branch(branch_id, data_dir=data_dir)
    except branch_store.BranchNotFoundError as exc:
        raise click.ClickException(str(exc)) from None
    except branch_store.BranchNotEvaluableError as exc:
        raise click.ClickException(str(exc)) from None
    b, ev = out["branch"], out["evaluation"]
    click.echo(f"{b['branch_id']}  status={b['status']}  evaluation_id={ev['evaluation_id']}")
    click.echo(f"  verdict={ev['verdict']['label']}  run_id={ev['run_id']}")


@branches_group.command("compare")
@click.option("--branch", "branch_id", required=True, help="branch_id to compare vs its parent")
def branches_compare_cmd(branch_id) -> None:
    """Show the branch-vs-parent headline delta table + decision."""
    from backtest_platform.research import branch_store

    try:
        cmp = branch_store.compare_branch(branch_id)
    except branch_store.BranchNotFoundError as exc:
        raise click.ClickException(str(exc)) from None
    if not cmp["branch_evaluated"]:
        click.echo(f"{branch_id}: branch not yet evaluated — run `branches evaluate` first")
        return
    click.echo(f"{branch_id}  ({cmp['strategy']})  parent={cmp['parent_run_id']} branch={cmp['branch_run_id']}")
    click.echo(f"  {'metric':<20}{'parent':>12}{'branch':>12}{'Δ':>12}  change")
    for r in cmp["metrics"]:
        p = "—" if r["parent"] is None else f"{r['parent']:.4f}"
        b = "—" if r["branch"] is None else f"{r['branch']:.4f}"
        d = "—" if r["delta"] is None else f"{r['delta']:+.4f}"
        click.echo(f"  {r['metric']:<20}{p:>12}{b:>12}{d:>12}  {r['change']}")
    dec = cmp["decision"]
    click.echo(f"  → decision: {dec['verdict']} (parent={dec['parent_label']} branch={dec['branch_label']})")


if __name__ == "__main__":
    cli()
