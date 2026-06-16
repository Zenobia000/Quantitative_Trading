"""Momentum IS harness — `run_momentum_is(universe, window) → metrics`.

Back-compat shim over the unified strategy contract (ADR-027): ``run_momentum_is``
now delegates to ``runners.MomentumRunner`` so momentum's IS→gate wiring shares
ONE implementation with every other strategy (metrics from ``validation.metrics``,
the same gate審判庭). ``price_panel`` is kept for callers/tests that build a close
panel directly.

Default loader reads ``data/parquet`` (the cache); inject a synthetic loader to
unit-test without IO.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import date

import pandas as pd

from backtest_platform.research.is_harness import load_merged_parquet
from backtest_platform.research.runners import MomentumRunner, _column_panel
from backtest_platform.strategies.momentum.strategy import MomentumConfig


def price_panel(
    symbols: list[str],
    loader: Callable[[str], pd.DataFrame] = load_merged_parquet,
) -> pd.DataFrame:
    """Wide close-price panel (date x symbol); symbols that fail to load are skipped."""
    return _column_panel(symbols, loader, "close")


def run_momentum_is(
    symbols: list[str],
    start: date | str,
    end: date | str,
    cfg: MomentumConfig | None = None,
    loader: Callable[[str], pd.DataFrame] = load_merged_parquet,
) -> dict:
    """Run momentum IS over a universe/window → a gate-ready metrics dict."""
    return MomentumRunner().run(symbols, start, end, cfg or MomentumConfig(), loader).metrics
