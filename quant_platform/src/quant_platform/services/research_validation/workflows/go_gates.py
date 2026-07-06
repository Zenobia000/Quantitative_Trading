"""GO gates workflow — WFA + PBO via strategy dispatch (ADR-028/029)."""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any

import numpy as np

# Import side-effect: ensure the built-in strategies are registered.
from quant_platform.services.research_validation import runners as _runners  # noqa: F401
from quant_platform.packages.application.is_harness import load_merged_parquet
from quant_platform.services.research_validation.workflows.config import GOGatesConfig
from quant_platform.services.research_validation.strategies.protocol import Loader, get_strategy
from quant_platform.services.research_validation.validation.pbo import probability_of_backtest_overfitting
from quant_platform.services.research_validation.validation.wfa import walk_forward_splits

_OOS_DAYS = 365
_IS_DAYS = 3 * 365
_PBO_PASS = 0.30   # PBO < 30% = not overfitting
_WFA_PASS = 0.60   # >=60% of WFA OOS folds positive


@dataclass(frozen=True)
class GOGatesResult:
    strategy: str
    wfa_oos_positive_frac: float
    pbo: float | None             # None if config_grid not provided
    wfa_folds_run: int
    verdict: str                  # "PASS" | "FAIL" | "INCOMPLETE"
    details: dict[str, Any]


def run_go_gates(cfg: GOGatesConfig, loader: Loader = load_merged_parquet) -> GOGatesResult:
    """WFA + PBO for ``fixed_config`` over a wide universe."""
    runner = get_strategy(cfg.strategy)
    sconf = runner.config_model(**cfg.fixed_config.model_dump())

    # --- WFA ---
    folds = walk_forward_splits(
        cfg.is_start, cfg.is_end, is_days=_IS_DAYS, oos_days=_OOS_DAYS, step_days=_OOS_DAYS,
    )[: cfg.n_wfa_folds]
    oos_sharpes: list[float] = []
    for fold in folds:
        run = runner.run(list(cfg.symbols), fold.oos_start, fold.oos_end, sconf, loader)
        oos_sharpes.append(float(run.metrics.get("sharpe", 0.0)))

    wfa_oos_positive_frac = (
        sum(1 for s in oos_sharpes if s > 0) / len(oos_sharpes) if oos_sharpes else 0.0
    )

    # --- PBO (optional, needs a config_grid landscape) ---
    pbo: float | None = None
    if cfg.config_grid:
        names = list(cfg.config_grid.keys())
        combos = list(itertools.product(*(cfg.config_grid[n] for n in names)))
        cols: list[np.ndarray] = []
        for combo in combos:
            params = dict(zip(names, combo, strict=True))
            sc = runner.config_model(**{**cfg.fixed_config.model_dump(), **params})
            full = runner.run(list(cfg.symbols), cfg.is_start, cfg.is_end, sc, loader)
            cols.append(full.returns.to_numpy(dtype=float) if len(full.returns) else np.zeros(1))
        max_len = max(len(c) for c in cols)
        mat = np.column_stack([np.pad(c, (0, max_len - len(c))) for c in cols])
        if mat.shape[1] >= 2 and mat.shape[0] >= cfg.pbo_n_splits:
            try:
                pbo = probability_of_backtest_overfitting(mat, n_splits=cfg.pbo_n_splits)
            except ValueError:
                pbo = None

    # --- Verdict ---
    wfa_pass = wfa_oos_positive_frac >= _WFA_PASS
    pbo_pass = (pbo is None) or (pbo < _PBO_PASS)
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
        details={
            "oos_sharpes": oos_sharpes,
            "wfa_pass_threshold": _WFA_PASS,
            "pbo_pass_threshold": _PBO_PASS,
            "wfa_pass": wfa_pass,
            "pbo_pass": pbo_pass,
        },
    )
