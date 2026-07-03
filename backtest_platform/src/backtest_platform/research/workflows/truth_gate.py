"""ADR-025 two-stage truth gate workflow via strategy dispatch (ADR-028/029).

The 審判庭: judge whether a pre-registered edge is REAL and, if so, size it.
ADR-030 corrected four proven defects in the original implementation:

  1. DSR was fed the *annualized* Sharpe (×√252) with a *daily returns variance* —
     mixed units that inflated the Deflated Sharpe to 1.0. It now uses the
     per-period Sharpe with a per-period cross-trial Sharpe variance V[SR_n].
  2. The locked OOS holdout [oos_start, is_end] was never executed; it now runs
     and gates the verdict (a negative holdout Sharpe is definitive overfit).
  3. ``survivorship_clean`` was hardwired True; it is now config-driven (defaults
     False) so the hard precondition is a claim to prove, not a free pass.
  4. Downstream deflation guards live in ``validation/dsr.py`` (fail fast).

A REAL verdict flows into the ADR-025 SizingGate → a continuous position weight.
"""
from __future__ import annotations

import functools
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

# Import side-effect: ensure the built-in strategies are registered.
from backtest_platform.research import runners as _runners  # noqa: F401
from backtest_platform.research.is_harness import load_merged_parquet
from backtest_platform.research.workflows.config import TruthGateConfig
from backtest_platform.strategies.protocol import Loader, get_strategy
from backtest_platform.validation.dsr import deflated_sharpe_ratio
from backtest_platform.validation.two_stage_gate import (
    SizingInput,
    TruthGateInput,
    evaluate_two_stage,
)
from backtest_platform.validation.wfa import walk_forward_splits

_OOS_DAYS = 365
_IS_DAYS = 3 * 365


@dataclass(frozen=True)
class TruthGateResult:
    strategy: str
    verdict: str     # "REAL" | "PAPER_WATCH" | "REJECTED" | "INCOMPLETE" (ADR-025/033)
    dsr: float
    slippage_sharpe: float
    wfa_oos_positive_frac: float
    oos_holdout_sharpe: float
    position_size: float
    reasons: tuple[str, ...]
    details: dict[str, Any]


def _resolve_loader(cfg: TruthGateConfig, loader: Loader | None) -> Loader:
    """Pick the data loader: explicit arg wins; else honour ``cfg.parquet_dir``.

    An explicit ``loader`` (as tests inject) is used verbatim. Otherwise a declared
    ``cfg.parquet_dir`` (e.g. the survivorship-clean FinLab cache, ADR-032) binds
    ``load_merged_parquet`` to that directory; None falls back to ``data/parquet``.
    """
    if loader is not None:
        return loader
    if cfg.parquet_dir is not None:
        return functools.partial(load_merged_parquet, parquet_dir=cfg.parquet_dir)
    return load_merged_parquet


def run_truth_gate(cfg: TruthGateConfig, loader: Loader | None = None) -> TruthGateResult:
    """Evaluate the pre-registered ``fixed_config`` through the ADR-025 two-stage gate.

    ``loader`` defaults to None so the config's ``parquet_dir`` can take effect (ADR-032);
    callers that inject a loader keep full control.
    """
    loader = _resolve_loader(cfg, loader)
    runner = get_strategy(cfg.strategy)
    sconf = runner.config_model(**cfg.fixed_config.model_dump())

    # --- 1. WFA OOS breadth on the IS span (strictly before the holdout) ---
    frac, oos_sharpes, n_folds = _wfa_oos_breadth(runner, cfg, sconf, loader)

    # --- 2. Full IS-span run → per-period trials-deflated DSR (units-correct) ---
    full = runner.run(list(cfg.symbols), cfg.is_start, cfg.oos_start, sconf, loader)
    dsr = _deflated_sharpe(full.returns, cfg.n_trials)

    # --- 3. Locked OOS holdout [oos_start, is_end] — the never-touched period ---
    oos_run = runner.run(list(cfg.symbols), cfg.oos_start, cfg.is_end, sconf, loader)
    oos_holdout_sharpe = float(oos_run.metrics.get("sharpe", 0.0))

    # --- 4. K3 slippage-robustness Sharpe ---
    slippage_sharpe = _slippage_sharpe(runner, cfg, sconf, loader)

    # --- 5. Two-stage gate: judge REAL, then size only if REAL ---
    decision = evaluate_two_stage(
        TruthGateInput(
            survivorship_clean=cfg.survivorship_clean,
            pre_registered=cfg.pre_registered,
            wfa_oos_positive_frac=frac,
            dsr=dsr,
            slippage_sharpe=slippage_sharpe,
            oos_holdout_sharpe=oos_holdout_sharpe,
        ),
        SizingInput(oos_sharpe=oos_holdout_sharpe),
    )

    return TruthGateResult(
        strategy=cfg.strategy,
        verdict=decision.truth.verdict.value,
        dsr=dsr,
        slippage_sharpe=slippage_sharpe,
        wfa_oos_positive_frac=frac,
        oos_holdout_sharpe=oos_holdout_sharpe,
        position_size=decision.size,
        reasons=decision.truth.reasons,
        details={
            "sharpe_is": float(full.metrics.get("sharpe", 0.0)),
            "n_obs": int(full.returns.size),
            "n_trials": cfg.n_trials,
            "wfa_folds": n_folds,
            "oos_sharpes": oos_sharpes,
            "oos_holdout_sharpe": oos_holdout_sharpe,
            "oos_window": (cfg.oos_start.isoformat(), cfg.is_end.isoformat()),
            "survivorship_clean": cfg.survivorship_clean,
        },
    )


def _wfa_oos_breadth(runner: Any, cfg: TruthGateConfig, sconf: Any, loader: Loader) -> tuple[float, list[float], int]:
    """Fraction of WFA folds with OOS Sharpe > 0 (pre-registered breadth check)."""
    folds = walk_forward_splits(
        cfg.is_start, cfg.oos_start, is_days=_IS_DAYS, oos_days=_OOS_DAYS, step_days=_OOS_DAYS,
    )[: cfg.n_wfa_folds]
    oos_sharpes = [
        float(runner.run(list(cfg.symbols), f.oos_start, f.oos_end, sconf, loader).metrics.get("sharpe", 0.0))
        for f in folds
    ]
    frac = sum(1 for s in oos_sharpes if s > 0) / len(oos_sharpes) if oos_sharpes else 0.0
    return frac, oos_sharpes, len(folds)


def _deflated_sharpe(returns: pd.Series, n_trials: int) -> float:
    """Trials-deflated Sharpe on a run's daily returns.

    ADR-036 升格：實作搬至 ``validation.dsr.deflated_sharpe_from_returns``
    （portfolio gate 需共用同一條 per-period 單位路徑，ADR-030 修正的單一真相源）；
    此 shim 保留原呼叫介面。
    """
    from backtest_platform.validation.dsr import deflated_sharpe_from_returns

    return deflated_sharpe_from_returns(returns, n_trials=n_trials)


def _slippage_sharpe(runner: Any, cfg: TruthGateConfig, sconf: Any, loader: Loader) -> float:
    """OOS Sharpe under the K3 slippage stress (edge must not collapse)."""
    slip_conf = runner.config_model(
        **{**cfg.fixed_config.model_dump(), **_add_slippage(cfg.fixed_config, cfg.slippage_stress)}
    )
    slip_run = runner.run(list(cfg.symbols), cfg.is_start, cfg.oos_start, slip_conf, loader)
    return float(slip_run.metrics.get("sharpe", 0.0))


def _add_slippage(config: Any, stress: float) -> dict[str, Any]:
    """Param dict adding ``stress`` to the config's slippage/cost field.

    The strategy contract's ``with_extra_slippage`` wins; the attribute probes
    only cover legacy configs. An unknown shape raises — a silent no-op here
    would void the K3 leg of the truth gate (審查缺陷 #18).
    """
    if hasattr(config, "with_extra_slippage"):
        return config.with_extra_slippage(stress).model_dump()
    if hasattr(config, "slip_rate"):
        return {"slip_rate": config.slip_rate + stress}
    if hasattr(config, "cost_round_rate"):
        return {"cost_round_rate": config.cost_round_rate + 2 * stress}
    raise ValueError(
        f"{type(config).__name__} exposes no slippage seam "
        "(with_extra_slippage / slip_rate / cost_round_rate) — K3 stress cannot run"
    )
