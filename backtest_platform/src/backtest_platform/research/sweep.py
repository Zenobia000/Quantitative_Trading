"""Parameter sweep + heatmap data (8.G.5a).

A vectorized-grid sweep over ``StrategyConfig`` variants. The anti-cherry-pick
discipline is structural: :func:`run_sweep` returns the **full grid** — every
config's portfolio metrics — never a single 'best'. Picking the max is the
caller's (visible, auditable) decision, and :func:`to_heatmap` turns the grid
into a 2-D surface so the *stability region* (a broad plateau, not a lone
spike) is what gets judged.

The sweep reuses the same offline close-to-close portfolio sim as
``is_harness.run_is`` (the ``_signaled_window`` / ``_daily_returns`` /
``_trades`` / ``_metrics`` helpers), but eats a ``StrategyConfig`` **directly**
rather than resolving a ``RunConfig.preset`` — a swept variant is, by
definition, not a named preset.

All three public functions are pure given their inputs (``run_sweep`` is pure
modulo the injected ``loader``), and use immutable ``StrategyConfig`` instances
throughout (``base.model_copy(update=...)``).
"""
from __future__ import annotations

import itertools
from collections.abc import Callable
from datetime import date

import numpy as np
import pandas as pd

from backtest_platform.strategies.four_layer_resonance.config import StrategyConfig
from backtest_platform.research.is_harness import (
    _SLIP_STRESS,
    _daily_returns,
    _metrics,
    _signaled_window,
    _trades,
)

_MIN_BARS = 30  # mirror is_harness.run_is: skip a stock with too little window data


def expand_grid(
    base: StrategyConfig, param_grid: dict[str, list],
) -> list[StrategyConfig]:
    """Cartesian product of ``param_grid`` applied onto ``base``.

    Each output row is ``base.model_copy(update={...})`` for one combination of
    the grid axes, so:

    * the result length equals the product of the per-axis lengths,
    * non-swept parameters are inherited from ``base``,
    * ``base`` itself is never mutated (frozen + copy-on-update).

    An empty ``param_grid`` yields ``[base]`` (one no-op combination). Unknown
    parameter names raise ``ValueError`` — ``model_copy(update=...)`` skips
    validation, so the names are checked against the model's fields here to
    fail fast at the boundary rather than silently set a bogus attribute.
    """
    if not param_grid:
        return [base.model_copy()]

    valid_fields = set(type(base).model_fields)
    unknown = [k for k in param_grid if k not in valid_fields]
    if unknown:
        raise ValueError(
            f"unknown StrategyConfig param(s) {unknown}; "
            f"choose from {sorted(valid_fields)}"
        )

    names = list(param_grid.keys())
    value_lists = [param_grid[n] for n in names]
    configs: list[StrategyConfig] = []
    for combo in itertools.product(*value_lists):
        update = dict(zip(names, combo, strict=True))
        configs.append(base.model_copy(update=update))
    return configs


def run_sweep(
    stocks: list[str],
    start: date,
    end: date,
    configs: list[StrategyConfig],
    loader: Callable[[str], pd.DataFrame],
) -> list[dict]:
    """Run the IS portfolio sim for every config; return the **full** grid.

    For each ``StrategyConfig`` in ``configs`` this runs the same offline
    close-to-close portfolio simulation as ``is_harness.run_is`` — but driven
    by the config object directly (no ``RunConfig.preset`` / ``get_preset``
    indirection), so arbitrary swept variants (not just named presets) work.

    Returns one ``dict`` per config: the portfolio metrics from
    ``is_harness._metrics`` (``cagr``/``sharpe``/``slippage_sharpe``/``maxdd``/
    ``win``/``avg_hold``/``struct1_pct``/``churn_pct``/``trades``/``closed``)
    plus ``bars`` and **every field of the config** swept against ``base`` (so
    the heatmap axes are present on each row). Order matches ``configs``; the
    full grid is always returned (anti cherry-pick).
    """
    results: list[dict] = []
    for cfg in configs:
        metrics = _run_one(stocks, start, end, cfg, loader)
        metrics.update(cfg.model_dump())  # attach every param value for the row
        results.append(metrics)
    return results


def _run_one(
    stocks: list[str],
    start: date,
    end: date,
    cfg: StrategyConfig,
    loader: Callable[[str], pd.DataFrame],
) -> dict:
    """Portfolio metrics for one config (mirrors is_harness.run_is internals)."""
    slip = cfg.model_copy(update={"slip_rate": _SLIP_STRESS})
    norm_returns: list[pd.Series] = []
    slip_returns: list[pd.Series] = []
    all_trades: list[dict] = []
    n_buys = 0

    for sid in stocks:
        sig = _signaled_window(loader(sid), cfg, start, end)
        if len(sig) < _MIN_BARS:
            continue
        norm_returns.append(_daily_returns(sig, cfg))
        slip_returns.append(_daily_returns(sig, slip))
        all_trades.extend(_trades(sig, cfg))
        n_buys += int((sig["action"] == "buy").sum())

    if not norm_returns:
        return {"trades": 0, "closed": 0, "bars": 0}

    port = pd.concat(norm_returns, axis=1).mean(axis=1)
    port_slip = pd.concat(slip_returns, axis=1).mean(axis=1)
    out = _metrics(port, port_slip, all_trades, n_buys)
    out["bars"] = len(port)
    return out


def to_heatmap(
    results: list[dict],
    x_param: str,
    y_param: str,
    metric: str,
) -> tuple[list, list, np.ndarray]:
    """Pivot sweep ``results`` into a 2-D ``metric`` surface for plotting.

    Returns ``(x_vals, y_vals, grid)`` where ``x_vals`` / ``y_vals`` are the
    sorted-ascending unique axis values and ``grid`` is a
    ``(len(y_vals), len(x_vals))`` float array with ``grid[yi][xi]`` the metric
    for the ``(y_vals[yi], x_vals[xi])`` cell. Missing combinations are
    ``np.nan`` (so a plotter shows holes, not silently-zeroed cells).

    A heatmap surfaces the *stability region*: the goal is a broad plateau of
    good ``metric`` values, which is far harder to overfit than a single peak.
    """
    x_vals = sorted({row[x_param] for row in results})
    y_vals = sorted({row[y_param] for row in results})
    x_index = {v: i for i, v in enumerate(x_vals)}
    y_index = {v: i for i, v in enumerate(y_vals)}

    grid = np.full((len(y_vals), len(x_vals)), np.nan, dtype=float)
    for row in results:
        yi = y_index[row[y_param]]
        xi = x_index[row[x_param]]
        grid[yi][xi] = float(row[metric])
    return x_vals, y_vals, grid
