"""DOE workflow — parameter grid scan through strategy dispatch (ADR-028).

Never imports strategy backtest functions directly — always calls
get_strategy(name).run() so the dispatch layer validates params.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from datetime import date

import pandas as pd

from backtest_platform.research import runners as _runners  # noqa: F401
from backtest_platform.research.is_harness import load_merged_parquet
from backtest_platform.research.workflows.config import DOEConfig
from backtest_platform.strategies.conformance import Loader
from backtest_platform.strategies.protocol import get_strategy


@dataclass(frozen=True)
class DOEResult:
    strategy:  str
    runs:      list
    n_configs: int
    is_start:  date
    is_end:    date

    def best(self, key: str = "sharpe") -> dict:
        return max(self.runs, key=lambda r: r.get(key, float("-inf")))

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.runs)


def run_doe(
    cfg: DOEConfig,
    loader: Loader = load_merged_parquet,
) -> DOEResult:
    """Run a parameter grid scan for cfg.strategy over cfg.grid.

    Each grid combination is validated through config_model(**params)
    (Pydantic, raises on bad params) then run through runner.run().
    """
    runner = get_strategy(cfg.strategy)
    names  = list(cfg.grid.keys())
    combos = list(itertools.product(*(cfg.grid[n] for n in names)))

    results: list[dict] = []
    for combo in combos:
        params = dict(zip(names, combo))
        sconf  = runner.config_model(**params)
        run    = runner.run(list(cfg.symbols), cfg.is_start, cfg.is_end, sconf, loader)
        results.append({**params, **run.metrics})

    return DOEResult(
        strategy=cfg.strategy,
        runs=results,
        n_configs=len(results),
        is_start=cfg.is_start,
        is_end=cfg.is_end,
    )
