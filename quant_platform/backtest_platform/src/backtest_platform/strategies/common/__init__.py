"""Neutral backtest mechanics shared across strategies (see ADR-026)."""
from backtest_platform.strategies.common.mechanics import (
    TRADING_DAYS,
    clean_returns,
    rebalance_dates,
    trim_overlap,
    vol_target,
)

__all__ = ["TRADING_DAYS", "clean_returns", "rebalance_dates", "trim_overlap", "vol_target"]
