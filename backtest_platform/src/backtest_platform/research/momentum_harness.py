"""Momentum IS harness — `run_momentum_is(universe, window) → metrics`.

The momentum analogue of ``is_harness.run_is``: loads a price panel via an
injectable loader, runs ``backtest_momentum`` (normal + extra-slippage for the K3
robustness Sharpe), and returns a metrics dict in the SAME shape the gate審判庭
consumes — so momentum is judged by ``evaluate_gate`` exactly like any strategy.

Default loader reads ``data/parquet`` (the cache); inject a synthetic loader to
unit-test without IO. Metrics reuse ``validation.metrics`` so the numbers are the
same estimators four-layer is held to.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import date

import pandas as pd

from backtest_platform.research.is_harness import load_merged_parquet
from backtest_platform.strategies.momentum.strategy import (
    MomentumConfig,
    MomentumResult,
    backtest_momentum,
)
from backtest_platform.validation.metrics import cagr, max_drawdown, sharpe

_SLIP_STRESS = 0.003  # 0.3% extra slippage for the K3 robustness Sharpe (matches is_harness)


def price_panel(
    symbols: list[str],
    loader: Callable[[str], pd.DataFrame] = load_merged_parquet,
) -> pd.DataFrame:
    """Wide close-price panel (date × symbol); symbols that fail to load are skipped."""
    cols: dict[str, pd.Series] = {}
    for sid in symbols:
        try:
            df = loader(sid)
        except Exception:  # noqa: BLE001 — a missing symbol must not sink the panel
            continue
        s = df[["trade_date", "close"]].copy()
        s["trade_date"] = pd.to_datetime(s["trade_date"])
        cols[sid] = s.set_index("trade_date")["close"].astype(float).sort_index()
    return pd.DataFrame(cols)


def _metrics(res: MomentumResult, slip: MomentumResult) -> dict:
    d = res.daily_returns
    return {
        "trades": res.n_rebalances,         # rebalances as the trade-count proxy
        "n_rebalances": res.n_rebalances,
        "bars": int(len(d)),
        "cagr": cagr(d) if len(d) else 0.0,
        "sharpe": sharpe(d) if len(d) else 0.0,
        "slippage_sharpe": sharpe(slip.daily_returns) if len(slip.daily_returns) else 0.0,
        "maxdd": max_drawdown(d) if len(d) else 0.0,
        "avg_holdings": res.avg_holdings,
        "avg_turnover": res.avg_turnover,
    }


def run_momentum_is(
    symbols: list[str],
    start: date | str,
    end: date | str,
    cfg: MomentumConfig | None = None,
    loader: Callable[[str], pd.DataFrame] = load_merged_parquet,
) -> dict:
    """Run momentum IS over a universe/window → a gate-ready metrics dict."""
    cfg = cfg or MomentumConfig()
    prices = price_panel(symbols, loader)
    if prices.empty:
        return {"trades": 0, "bars": 0}
    res = backtest_momentum(prices, cfg, start, end)
    slip = backtest_momentum(prices, cfg.with_extra_slippage(_SLIP_STRESS), start, end)
    return _metrics(res, slip)
