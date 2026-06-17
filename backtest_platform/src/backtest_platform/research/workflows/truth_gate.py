"""ADR-025 two-stage truth gate workflow via strategy dispatch (ADR-028/029)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Import side-effect: ensure the built-in strategies are registered.
from backtest_platform.research import runners as _runners  # noqa: F401
from backtest_platform.research.is_harness import load_merged_parquet
from backtest_platform.research.workflows.config import TruthGateConfig
from backtest_platform.strategies.protocol import Loader, get_strategy
from backtest_platform.validation.dsr import deflated_sharpe_ratio
from backtest_platform.validation.two_stage_gate import TruthGateInput, evaluate_truth_gate
from backtest_platform.validation.wfa import walk_forward_splits

_OOS_DAYS = 365
_IS_DAYS = 3 * 365


@dataclass(frozen=True)
class TruthGateResult:
    strategy: str
    verdict: str     # "REAL" | "REJECTED" | "INCOMPLETE"
    dsr: float
    slippage_sharpe: float
    wfa_oos_positive_frac: float
    reasons: tuple[str, ...]
    details: dict[str, Any]


def run_truth_gate(cfg: TruthGateConfig, loader: Loader = load_merged_parquet) -> TruthGateResult:
    """Evaluate the pre-registered ``fixed_config`` through the ADR-025 two-stage gate."""
    runner = get_strategy(cfg.strategy)
    sconf = runner.config_model(**cfg.fixed_config.model_dump())

    # --- 1. WFA on the IS span (strictly before OOS) ---
    folds = walk_forward_splits(
        cfg.is_start, cfg.oos_start, is_days=_IS_DAYS, oos_days=_OOS_DAYS, step_days=_OOS_DAYS,
    )[: cfg.n_wfa_folds]
    oos_sharpes: list[float] = []
    for fold in folds:
        run = runner.run(list(cfg.symbols), fold.oos_start, fold.oos_end, sconf, loader)
        oos_sharpes.append(float(run.metrics.get("sharpe", 0.0)))
    wfa_oos_positive_frac = (
        sum(1 for s in oos_sharpes if s > 0) / len(oos_sharpes) if oos_sharpes else 0.0
    )

    # --- 2. Full IS-span Sharpe + DSR deflation ---
    full = runner.run(list(cfg.symbols), cfg.is_start, cfg.oos_start, sconf, loader)
    sr = float(full.metrics.get("sharpe", 0.0))
    rets = full.returns
    n_obs = max(len(rets), 2)
    skew = float(rets.skew()) if len(rets) > 3 else 0.0
    kurt = float(rets.kurtosis() + 3) if len(rets) > 3 else 3.0
    sharpe_var = max(float(rets.var()), 1e-9) if len(rets) > 1 else 1e-9
    dsr = (
        deflated_sharpe_ratio(
            sr=sr, n_trials=cfg.n_trials, n_obs=n_obs,
            skew=skew, kurtosis=kurt, sharpe_variance=sharpe_var,
        )
        if n_obs > 1 else 0.0
    )

    # --- 3. K3 slippage-robustness Sharpe ---
    slip_conf = runner.config_model(
        **{**cfg.fixed_config.model_dump(), **_add_slippage(cfg.fixed_config, cfg.slippage_stress)}
    )
    slip_run = runner.run(list(cfg.symbols), cfg.is_start, cfg.oos_start, slip_conf, loader)
    slippage_sharpe = float(slip_run.metrics.get("sharpe", 0.0))

    # --- 4. Evaluate the truth gate ---
    gate = evaluate_truth_gate(TruthGateInput(
        survivorship_clean=True,
        pre_registered=cfg.pre_registered,
        wfa_oos_positive_frac=wfa_oos_positive_frac,
        dsr=dsr,
        slippage_sharpe=slippage_sharpe,
    ))

    return TruthGateResult(
        strategy=cfg.strategy,
        verdict=gate.verdict.value,
        dsr=dsr,
        slippage_sharpe=slippage_sharpe,
        wfa_oos_positive_frac=wfa_oos_positive_frac,
        reasons=gate.reasons,
        details={
            "sharpe_is": sr,
            "n_obs": n_obs,
            "n_trials": cfg.n_trials,
            "wfa_folds": len(folds),
            "oos_sharpes": oos_sharpes,
        },
    )


def _add_slippage(config: Any, stress: float) -> dict[str, Any]:
    """Param dict adding ``stress`` to the config's slippage/cost field."""
    if hasattr(config, "slip_rate"):
        return {"slip_rate": config.slip_rate + stress}
    if hasattr(config, "cost_round_rate"):
        return {"cost_round_rate": config.cost_round_rate + 2 * stress}
    return {}
