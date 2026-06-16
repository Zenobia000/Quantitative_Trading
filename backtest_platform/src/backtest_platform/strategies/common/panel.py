"""Shared building blocks for cross-sectional (panel) strategies (ADR-027).

A cross-sectional strategy (momentum, inst_flow, …) needs two neutral things its
runner shouldn't re-implement: (1) turning the per-stock ``Loader`` into wide
``date x symbol`` panels, and (2) turning a rebalanced backtest result into the
gate-ready metrics dict (via ``validation.metrics`` so every strategy is judged by
the same estimators). Keeping them here means a new panel strategy's runner is a
few lines: build panels → call its pure backtest → ``panel_metrics``.

Pure functions; depends only on ``validation`` (acyclic) + pandas.
"""
from __future__ import annotations

from typing import Any, Protocol

import pandas as pd

from backtest_platform.strategies.protocol import Loader
from backtest_platform.validation.metrics import cagr, max_drawdown, sharpe


def column_panel(symbols: list[str], loader: Loader, col: str) -> pd.DataFrame:
    """Wide panel (date x symbol) of one column from each stock's merged frame.

    Symbols that fail to load are skipped — one bad symbol must not sink the
    whole panel.
    """
    cols: dict[str, pd.Series] = {}
    for sid in symbols:
        try:
            df = loader(sid)
        except Exception:
            continue
        s = df[["trade_date", col]].copy()
        s["trade_date"] = pd.to_datetime(s["trade_date"])
        cols[sid] = s.set_index("trade_date")[col].astype(float).sort_index()
    return pd.DataFrame(cols)


def flow_panels(
    symbols: list[str], loader: Loader, flow_cols: tuple[str, ...]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """close / summed-net-buy / volume wide panels aligned on the same index."""
    close: dict[str, pd.Series] = {}
    flow: dict[str, pd.Series] = {}
    vol: dict[str, pd.Series] = {}
    for sid in symbols:
        try:
            df = loader(sid)
        except Exception:
            continue
        d = df.copy()
        d["trade_date"] = pd.to_datetime(d["trade_date"])
        d = d.set_index("trade_date").sort_index()
        close[sid] = d["close"].astype(float)
        vol[sid] = d["volume"].astype(float)
        flow[sid] = sum(d[c].astype(float) for c in flow_cols)
    return pd.DataFrame(close), pd.DataFrame(flow), pd.DataFrame(vol)


class RebalancedResult(Protocol):
    """The shape every rebalanced backtest returns (momentum / inst_flow / …).

    Members are read-only properties so frozen-dataclass results
    (``MomentumResult`` / ``InstFlowResult``) structurally satisfy the protocol.
    """

    @property
    def daily_returns(self) -> pd.Series: ...
    @property
    def n_rebalances(self) -> int: ...
    @property
    def avg_holdings(self) -> float: ...
    @property
    def avg_turnover(self) -> float: ...


def panel_metrics(res: RebalancedResult, slip: RebalancedResult) -> dict[str, Any]:
    """Gate-ready metrics for a rebalanced strategy result.

    ``res`` is the normal run, ``slip`` the same run with extra slippage (the K3
    robustness Sharpe). Metrics come from ``validation.metrics`` so panel
    strategies are held to the same estimators as four-layer.
    """
    d = res.daily_returns
    return {
        "trades": res.n_rebalances,         # rebalances as the trade-count proxy
        "n_rebalances": res.n_rebalances,
        "bars": len(d),
        "cagr": cagr(d) if len(d) else 0.0,
        "sharpe": sharpe(d) if len(d) else 0.0,
        "slippage_sharpe": sharpe(slip.daily_returns) if len(slip.daily_returns) else 0.0,
        "maxdd": max_drawdown(d) if len(d) else 0.0,
        "avg_holdings": res.avg_holdings,
        "avg_turnover": res.avg_turnover,
    }
