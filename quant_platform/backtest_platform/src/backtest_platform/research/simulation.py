"""Re-export shim (W4.1a) — moved to ``research.domain.simulation``."""
from __future__ import annotations

from backtest_platform.research.domain.simulation import (
    annualized_volatility,
    apply_equity_whatif,
    base_round_trip_cost,
    clamp_trades,
    has_per_trade_returns,
    portfolio_metrics,
    reconstruct_returns,
    simulate,
    trade_metrics,
)

__all__ = [
    "annualized_volatility",
    "apply_equity_whatif",
    "base_round_trip_cost",
    "clamp_trades",
    "has_per_trade_returns",
    "portfolio_metrics",
    "reconstruct_returns",
    "simulate",
    "trade_metrics",
]
