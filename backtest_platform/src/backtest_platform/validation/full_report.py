"""Full validation report (6.x) — one returns series → the whole審判庭.

Composes the strategy-agnostic validation modules into a single end-to-end report
so any strategy's daily-returns series can be run through the complete pipeline
(metrics → §4.3.1 health table → bootstrap CI → Monte-Carlo edge p-value →
Deflated Sharpe) in one call. This is the reusable core behind "跑通" — exercising
the platform's validation stack on a real strategy rather than ad-hoc scripts.

Numerical conventions (must not be mixed up — see dsr.py / metrics.py):
- The *health table* and human-facing figures use the **annualized** Sharpe
  (the ADR-016 ``> 1.0`` bar is annualized).
- PSR/DSR use the **per-period** Sharpe with **per-period** moments, and **raw**
  (non-excess) kurtosis (3 for Gaussian) — pandas ``.kurtosis()`` is excess, so
  we add 3.0.

Deterministic: bootstrap / Monte-Carlo take an explicit ``seed`` so a report is
reproducible (re-running the same returns yields the same CI / p-value).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from backtest_platform.validation import metrics as M
from backtest_platform.validation.dsr import deflated_sharpe_ratio
from backtest_platform.validation.health_indicators import health_check
from backtest_platform.validation.resampling import (
    bootstrap_ci,
    monte_carlo_permutation_pvalue,
)

ANNUALIZATION = 252
#: ADR-016 deployment bars (annualized) — surfaced so the report self-judges.
DSR_BAR = 0.95


def _per_period_sharpe(arr: np.ndarray) -> float:
    sd = float(arr.std(ddof=0))
    return float(arr.mean() / sd) if sd > 0 else 0.0


def full_validation_report(
    daily_returns: pd.Series,
    *,
    n_trials: int = 1,
    sharpe_variance: float = 0.5,
    n_iter: int = 1000,
    seed: int = 0,
) -> dict:
    """Run a returns series through the complete validation stack.

    Parameters
    ----------
    daily_returns:
        The strategy's per-period (daily) returns.
    n_trials:
        How many configurations were searched (drives the DSR deflation). Pass the
        real sweep count so the Deflated Sharpe is honest, not optimistic.
    sharpe_variance:
        Cross-trial variance of the Sharpe estimates ``V[SR_n]`` for the DSR
        deflation benchmark.
    n_iter, seed:
        Bootstrap / Monte-Carlo iterations and RNG seed (deterministic report).

    Returns
    -------
    dict
        ``{metrics, health, robustness, deployable, bars}`` — the metrics dict,
        the §4.3.1 health table, the resampling/DSR robustness block, and a
        boolean ``deployable`` roll-up against the ADR-016 bars.
    """
    arr = np.asarray(daily_returns, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size < 2:
        raise ValueError("daily_returns must have >= 2 finite observations")
    s = pd.Series(arr)

    ann_sharpe = M.sharpe(s)
    metrics = {
        "total_return": M.total_return(s),
        "cagr": M.cagr(s),
        "sharpe": ann_sharpe,
        "sortino": M.sortino(s),
        "calmar": M.calmar(s),
        "max_drawdown": M.max_drawdown(s),
        "ulcer_index": M.ulcer_index(s),
        "downside_deviation": M.downside_deviation(s),
    }
    health = health_check(metrics).to_dict()

    # robustness block — bootstrap CI on the annualized Sharpe + MC edge + DSR
    lo, hi, point = bootstrap_ci(
        arr, stat_fn=lambda r: _per_period_sharpe(r) * np.sqrt(ANNUALIZATION),
        n_iter=n_iter, seed=seed,
    )
    mc_p = monte_carlo_permutation_pvalue(arr, n_iter=n_iter, seed=seed)
    dsr = deflated_sharpe_ratio(
        sr=_per_period_sharpe(arr),
        n_trials=n_trials,
        n_obs=arr.size,
        skew=float(s.skew()),
        kurtosis=float(s.kurtosis()) + 3.0,  # pandas excess → raw (3 for Gaussian)
        sharpe_variance=sharpe_variance,
    )
    robustness = {
        "sharpe_ci": {"lo": lo, "hi": hi, "point": point, "ci": 0.95},
        "mc_edge_pvalue": mc_p,
        "deflated_sharpe": dsr,
        "n_trials": n_trials,
    }

    bars = {"sharpe": 1.0, "cagr": 0.18, "dsr": DSR_BAR}
    deployable = (
        metrics["sharpe"] > bars["sharpe"]
        and metrics["cagr"] > bars["cagr"]
        and dsr > bars["dsr"]
    )
    return {
        "metrics": metrics,
        "health": health,
        "robustness": robustness,
        "bars": bars,
        "deployable": deployable,
    }
