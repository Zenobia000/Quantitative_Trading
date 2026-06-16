"""GO gates workflow — WFA + PBO via strategy dispatch."""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from datetime import date

import numpy as np

from backtest_platform.research import runners as _runners  # noqa: F401
from backtest_platform.research.is_harness import load_merged_parquet
from backtest_platform.research.workflows.config import GOGatesConfig
from backtest_platform.strategies.conformance import Loader
from backtest_platform.strategies.protocol import get_strategy
from backtest_platform.validation.pbo import probability_of_backtest_overfitting
from backtest_platform.validation.wfa import walk_forward_splits

_OOS_DAYS = 365
_IS_DAYS  = 3 * 365
_PBO_PASS = 0.30
_WFA_PASS = 0.60


@dataclass(frozen=True)
class GOGatesResult:
    strategy:              str
    wfa_oos_positive_frac: float
    pbo:                   float | None
    wfa_folds_run:         int
    verdict:               str
    details:               dict


def run_go_gates(
    cfg: GOGatesConfig,
    loader: Loader = load_merged_parquet,
) -> GOGatesResult:
    """WFA + PBO for the fixed_config over a wide universe."""
    runner = get_strategy(cfg.strategy)
    sconf  = runner.config_model(**cfg.fixed_config.model_dump())

    folds = walk_forward_splits(
        cfg.is_start, cfg.is_end,
        is_days=_IS_DAYS, oos_days=_OOS_DAYS, step_days=_OOS_DAYS,
    )[:cfg.n_wfa_folds]

    oos_sharpes: list[float] = []
    for fold in folds:
        run = runner.run(list(cfg.symbols), fold.oos_start, fold.oos_end, sconf, loader)
        oos_sharpes.append(float(run.metrics.get("sharpe", 0.0)))

    wfa_oos_positive_frac = (
        sum(1 for s in oos_sharpes if s > 0) / len(oos_sharpes) if oos_sharpes else 0.0
    )

    pbo: float | None = None
    if cfg.config_grid:
        names  = list(cfg.config_grid.keys())
        combos = list(itertools.product(*(cfg.config_grid[n] for n in names)))
        cols: list[np.ndarray] = []
        for combo in combos:
            params   = dict(zip(names, combo))
            sc       = runner.config_model(**{**cfg.fixed_config.model_dump(), **params})
            run_full = runner.run(list(cfg.symbols), cfg.is_start, cfg.is_end, sc, loader)
            ret_arr  = run_full.returns.values.astype(float) if len(run_full.returns) else np.zeros(1)
            cols.append(ret_arr)
        if cols:
            max_len = max(len(c) for c in cols)
            mat = np.column_stack([np.pad(c, (0, max_len - len(c))) for c in cols])
            if mat.shape[1] >= 2 and mat.shape[0] >= cfg.pbo_n_splits:
                try:
                    pbo = probability_of_backtest_overfitting(mat, n_splits=cfg.pbo_n_splits)
                except ValueError:
                    pbo = None

    wfa_pass = wfa_oos_positive_frac >= _WFA_PASS
    pbo_pass = pbo is None or pbo < _PBO_PASS
    if not oos_sharpes:
        verdict = "INCOMPLETE"
    elif wfa_pass and pbo_pass:
        verdict = "PASS"
    else:
        verdict = "FAIL"

    return GOGatesResult(
        strategy=cfg.strategy,
        wfa_oos_positive_frac=wfa_oos_positive_frac,
        pbo=pbo,
        wfa_folds_run=len(folds),
        verdict=verdict,
        details={"oos_sharpes": oos_sharpes, "wfa_pass": wfa_pass, "pbo_pass": pbo_pass},
    )
