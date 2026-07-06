"""Evaluation orchestrator (rebuild Goal 3 / ADR-039).

``evaluate(strategy, profile)`` is the high-level entrypoint that sits ABOVE the
ADR-029 primitives: it resolves an :class:`EvaluationProfile`, runs the primitive(s)
that profile wraps through the ADR-028 dispatch layer, assembles a contract
``EvaluationResult`` (``result_builder``), writes the report pack (``report_pack``),
and appends the result to the append-only ledger (``store``) — INCLUDING failed /
weak / data-issue strategies (global acceptance #5).

The primitives are WRAPPED, never modified (spec §8 #5): ``deployment_strict`` calls
``research.workflows.truth_gate.run_truth_gate`` unchanged; ``grid_search_selection``
composes ``run_doe`` + ``run_go_gates``; ``fixed_hypothesis_oos`` composes a
single-run + ``run_go_gates``; ``quick_triage`` is one dispatch ``runner.run()``.
"""
from __future__ import annotations

import functools
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pandas as pd

from quant_platform.services.research_validation import runners as _runners  # noqa: F401 — register strategies
from quant_platform.services.research_validation.evaluation.models import RunBundle
from quant_platform.services.research_validation.evaluation.profiles import EvaluationProfile, get_profile
from quant_platform.services.research_validation.evaluation.report_pack import DEFAULT_PACK_ROOT, write_report_pack
from quant_platform.services.research_validation.evaluation.result_builder import assemble_result
from quant_platform.services.research_validation.evaluation.store import DEFAULT_EVALUATIONS_PATH, append_evaluation
from quant_platform.packages.application.is_harness import load_merged_parquet
from quant_platform.packages.domain.run_config import RunConfig
from quant_platform.services.research_validation.workflows.loader import (
    get_doe_config,
    get_go_gates_config,
    get_truth_gate_config,
)
from quant_platform.services.research_validation.strategies.protocol import Loader, get_strategy
from quant_platform.services.research_validation.validation.dsr import deflated_sharpe_from_returns
from quant_platform.services.research_validation.validation.two_stage_gate import PBO_MAX

_TWT = timezone(timedelta(hours=8))


def _now() -> datetime:
    return datetime.now(_TWT)


def _coerce_date(d: date | str | None) -> date | None:
    if d is None or isinstance(d, date):
        return d
    return date.fromisoformat(d)


def _resolve_loader(loader: Loader | None, data_dir: str | None) -> Loader:
    if loader is not None:
        return loader
    if data_dir is not None:
        return functools.partial(load_merged_parquet, parquet_dir=data_dir)
    return load_merged_parquet


def _merge_overrides(params: dict[str, Any], overrides: dict[str, Any] | None) -> dict[str, Any]:
    """A NEW params dict with ``overrides`` applied on top (branch config re-run).

    Immutability: never mutates the resolved config in place — a branch evaluation
    threads its config-delta through here without disturbing the declared config.
    """
    return {**params, **(overrides or {})}


def _single_run_spec(
    strategy: str, symbols: list[str] | None, is_start: date | None, is_end: date | None,
    param_overrides: dict[str, Any] | None = None,
) -> tuple[list[str], date, date, dict[str, Any]]:
    """Resolve (symbols, is_start, is_end, params) for a single-config run.

    Prefers the strategy's declared GO_GATES config (fixed_config + wide universe +
    window), else TRUTH_GATE (IS window), else DOE (default config). Explicit
    overrides win. ``param_overrides`` (a branch config delta) are applied last, on
    top of the resolved params. Raises ``ValueError`` if the strategy declares no
    usable config.
    """
    params: dict[str, Any] = {}
    cfg_symbols: list[str] | None = None
    cfg_start: date | None = None
    cfg_end: date | None = None
    try:
        gg = get_go_gates_config(strategy)
        params = gg.fixed_config.model_dump()
        cfg_symbols, cfg_start, cfg_end = list(gg.symbols), gg.is_start, gg.is_end
    except (ValueError, AttributeError, TypeError):
        try:
            tg = get_truth_gate_config(strategy)
            params = tg.fixed_config.model_dump()
            cfg_symbols, cfg_start, cfg_end = list(tg.symbols), tg.is_start, tg.oos_start
        except (ValueError, AttributeError, TypeError):
            try:
                doe = get_doe_config(strategy)
                cfg_symbols, cfg_start, cfg_end = list(doe.symbols), doe.is_start, doe.is_end
            except (ValueError, AttributeError, TypeError):
                cfg_symbols = None

    symbols = symbols or cfg_symbols
    is_start = is_start or cfg_start
    is_end = is_end or cfg_end
    if not symbols or is_start is None or is_end is None:
        raise ValueError(
            f"cannot resolve a run spec for {strategy!r}: declare GO_GATES/TRUTH_GATE/DOE "
            f"in its research_config.py, or pass --symbols/--start/--end explicitly"
        )
    return symbols, is_start, is_end, _merge_overrides(params, param_overrides)


def _run_single(runner: Any, symbols: list[str], start: date, end: date, params: dict[str, Any], loader: Loader):
    sconf = runner.config_model(**params)
    run = runner.run(list(symbols), start, end, sconf, loader)
    return run.metrics, run.returns, run.trades


def _bundle_quick_triage(strategy, runner, loader, symbols, is_start, is_end, param_overrides=None) -> RunBundle:
    symbols, is_start, is_end, params = _single_run_spec(strategy, symbols, is_start, is_end, param_overrides)
    metrics, returns, trades = _run_single(runner, symbols, is_start, is_end, params, loader)
    return RunBundle(
        metrics=metrics, returns=returns, trades=trades, params=params, symbols=symbols,
        window={"is_start": is_start.isoformat(), "is_end": is_end.isoformat()},
        n_trials=1, survivorship_clean=False, bundle_ref=None,
    )


def _bundle_fixed_hypothesis(strategy, runner, loader, symbols, is_start, is_end, param_overrides=None) -> RunBundle:
    from quant_platform.services.research_validation.workflows.go_gates import run_go_gates
    symbols, is_start, is_end, params = _single_run_spec(strategy, symbols, is_start, is_end, param_overrides)
    metrics, returns, trades = _run_single(runner, symbols, is_start, is_end, params, loader)
    extras: dict[str, Any] = {"slippage_sharpe": metrics.get("slippage_sharpe")}
    try:
        gg = run_go_gates(get_go_gates_config(strategy), loader=loader)
        extras["wfa_oos_positive_frac"] = gg.wfa_oos_positive_frac
    except (ValueError, AttributeError, TypeError):
        pass
    if len(returns):
        extras["dsr"] = deflated_sharpe_from_returns(pd.Series(returns, dtype=float), n_trials=1)
    return RunBundle(
        metrics=metrics, returns=returns, trades=trades, params=params, symbols=symbols,
        window={"is_start": is_start.isoformat(), "is_end": is_end.isoformat()},
        n_trials=1, survivorship_clean=False, bundle_ref=None, extras=extras,
    )


def _bundle_grid_search(strategy, runner, loader, symbols, is_start, is_end, param_overrides=None) -> RunBundle:
    from quant_platform.services.research_validation.workflows.doe import run_doe
    from quant_platform.services.research_validation.workflows.go_gates import run_go_gates
    doe_cfg = get_doe_config(strategy)
    doe_res = run_doe(doe_cfg, loader=loader)
    best = doe_res.best("sharpe")
    grid_keys = set(doe_cfg.grid)
    best_params = _merge_overrides({k: v for k, v in best.items() if k in grid_keys}, param_overrides)
    gg_cfg = get_go_gates_config(strategy)
    metrics, returns, trades = _run_single(
        runner, list(gg_cfg.symbols), gg_cfg.is_start, gg_cfg.is_end, best_params, loader
    )
    extras: dict[str, Any] = {"slippage_sharpe": metrics.get("slippage_sharpe")}
    gg = run_go_gates(gg_cfg, loader=loader)
    extras["wfa_oos_positive_frac"] = gg.wfa_oos_positive_frac
    extras["pbo"] = gg.pbo
    if len(returns):
        extras["dsr"] = deflated_sharpe_from_returns(pd.Series(returns, dtype=float), n_trials=doe_res.n_configs)
    # A selected config whose landscape PBO exceeds the ADR-025 max is config-selection overfit.
    truth_verdict = "REJECTED" if (gg.pbo is not None and gg.pbo >= PBO_MAX) else None
    return RunBundle(
        metrics=metrics, returns=returns, trades=trades, params=best_params, symbols=list(gg_cfg.symbols),
        window={"is_start": gg_cfg.is_start.isoformat(), "is_end": gg_cfg.is_end.isoformat()},
        n_trials=doe_res.n_configs, survivorship_clean=False, bundle_ref=None, extras=extras,
        truth_verdict=truth_verdict,
    )


def _bundle_deployment_strict(strategy, runner, loader, param_overrides=None) -> RunBundle:
    from quant_platform.services.research_validation.workflows.truth_gate import run_truth_gate
    cfg = get_truth_gate_config(strategy)
    # Wrap the truth gate UNCHANGED for the verdict + gate extras (ADR-025/030).
    tg = run_truth_gate(cfg, loader=loader)
    params = _merge_overrides(cfg.fixed_config.model_dump(), param_overrides)
    # One extra IS run (the same window truth_gate uses internally) for scorecards.
    metrics, returns, trades = _run_single(runner, list(cfg.symbols), cfg.is_start, cfg.oos_start, params, loader)
    extras = {
        "oos_holdout_sharpe": tg.oos_holdout_sharpe,
        "dsr": tg.dsr,
        "wfa_oos_positive_frac": tg.wfa_oos_positive_frac,
        "slippage_sharpe": tg.slippage_sharpe,
    }
    return RunBundle(
        metrics=metrics, returns=returns, trades=trades, params=params,
        symbols=list(cfg.symbols),
        window={"is_start": cfg.is_start.isoformat(), "oos_start": cfg.oos_start.isoformat(), "is_end": cfg.is_end.isoformat()},
        n_trials=cfg.n_trials, survivorship_clean=cfg.survivorship_clean, bundle_ref=cfg.parquet_dir,
        extras=extras, truth_verdict=tg.verdict, truth_reasons=tuple(tg.reasons), position_size=tg.position_size,
    )


_BUNDLERS = {
    "quick_triage": lambda s, r, ld, sym, st, en, ov: _bundle_quick_triage(s, r, ld, sym, st, en, ov),
    "fixed_hypothesis_oos": lambda s, r, ld, sym, st, en, ov: _bundle_fixed_hypothesis(s, r, ld, sym, st, en, ov),
    "grid_search_selection": lambda s, r, ld, sym, st, en, ov: _bundle_grid_search(s, r, ld, sym, st, en, ov),
    "deployment_strict": lambda s, r, ld, sym, st, en, ov: _bundle_deployment_strict(s, r, ld, ov),
}


def _equity_drawdown(returns: pd.Series) -> tuple[list[float], list[float]]:
    if returns is None or len(returns) == 0:
        return [], []
    eq = (1.0 + pd.Series(returns, dtype=float)).cumprod()
    dd = eq / eq.cummax() - 1.0
    return [float(x) for x in eq], [float(x) for x in dd]


def evaluate(
    strategy: str,
    profile: str,
    *,
    loader: Loader | None = None,
    data_dir: str | None = None,
    symbols: list[str] | None = None,
    is_start: date | str | None = None,
    is_end: date | str | None = None,
    hypothesis: str | None = None,
    param_overrides: dict[str, Any] | None = None,
    branch_lineage: dict[str, Any] | None = None,
    clock: Any = _now,
    persist: bool = True,
    evaluations_path: Any = DEFAULT_EVALUATIONS_PATH,
    pack_root: Any = DEFAULT_PACK_ROOT,
) -> dict[str, Any]:
    """Evaluate ``strategy`` under ``profile`` → a contract ``EvaluationResult`` dict.

    Resolves the profile + strategy (both ``ValueError`` on unknown → API 404 / clean
    CLI error), runs the wrapped primitive(s), assembles the result, writes the report
    pack, and (``persist``) appends to the ledger. A run that yields no bars is
    persisted as a ``data_issue`` result — never dropped (global acceptance #5).

    ``param_overrides`` layers a config delta on top of the resolved params (the
    branch-experiment re-run, Goal 9): a changed config value shifts the ``run_id``
    config hash, so a branch always gets a distinct ``evaluation_id`` and can never
    fold over its parent. ``branch_lineage`` (when set) tags the result's ``branch``
    key so the candidate pool / report can badge the branch origin.
    """
    prof: EvaluationProfile = get_profile(profile)          # ValueError → unknown profile
    runner = get_strategy(strategy)                          # ValueError → unknown strategy
    resolved_loader = _resolve_loader(loader, data_dir)

    bundle = _BUNDLERS[prof.name](
        strategy, runner, resolved_loader, symbols, _coerce_date(is_start), _coerce_date(is_end),
        param_overrides,
    )

    win = bundle.window
    run_id = RunConfig(
        hypothesis=hypothesis or f"{prof.name} evaluation of {strategy}",
        strategy=strategy, params=bundle.params, stocks=tuple(bundle.symbols),
        is_start=date.fromisoformat(win["is_start"]),
        is_end=date.fromisoformat(win.get("oos_start", win["is_end"])),
    ).run_id
    created_at = clock().isoformat(timespec="seconds")
    evaluation_id = f"eval_{strategy}_{prof.name}_{run_id}"

    result = assemble_result(
        prof, bundle, strategy=strategy, run_id=run_id,
        evaluation_id=evaluation_id, created_at=created_at,
    )
    if branch_lineage:
        result["branch"] = dict(branch_lineage)

    equity, drawdown = _equity_drawdown(bundle.returns)
    write_report_pack(result, {"equity": equity, "drawdown": drawdown, "trades": bundle.trades}, root=pack_root)

    if persist:
        append_evaluation(result, evaluations_path)
    return result
