"""DOE workflow — parameter grid scan through strategy dispatch (ADR-028/029).

Never imports a strategy's backtest function directly — always calls
``get_strategy(name).run()`` so the dispatch layer validates params via the
strategy's ``config_model``.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd

# Import side-effect: ensure the built-in strategies are registered.
from backtest_platform.research import runners as _runners  # noqa: F401
from backtest_platform.research.is_harness import load_merged_parquet
from backtest_platform.research.workflows.config import DOEConfig
from backtest_platform.strategies.protocol import Loader, get_strategy


@dataclass(frozen=True)
class DOEResult:
    strategy: str
    runs: list[dict[str, Any]]   # [{param_k: v, ..., cagr: x, sharpe: y, ...}]
    n_configs: int
    is_start: date
    is_end: date

    def best(self, key: str = "sharpe") -> dict[str, Any]:
        """Row with the highest value for ``key``."""
        return max(self.runs, key=lambda r: r.get(key, float("-inf")))

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.runs)


def run_doe(cfg: DOEConfig, loader: Loader = load_merged_parquet) -> DOEResult:
    """Run a parameter grid scan for ``cfg.strategy`` over ``cfg.grid``.

    Each grid combination is validated through ``config_model(**params)``
    (Pydantic, raises on bad params) then run via ``runner.run()``. Each result
    row carries the grid params + the run metrics so the caller can pivot/filter
    without re-running.
    """
    runner = get_strategy(cfg.strategy)
    names = list(cfg.grid.keys())
    combos = list(itertools.product(*(cfg.grid[n] for n in names)))

    runs: list[dict[str, Any]] = []
    for combo in combos:
        params = dict(zip(names, combo, strict=True))
        sconf = runner.config_model(**params)          # validate via Pydantic
        run = runner.run(list(cfg.symbols), cfg.is_start, cfg.is_end, sconf, loader)
        runs.append({**params, **run.metrics})

    return DOEResult(
        strategy=cfg.strategy,
        runs=runs,
        n_configs=len(runs),
        is_start=cfg.is_start,
        is_end=cfg.is_end,
    )
