"""Neutral backtest mechanics shared across strategies (see ADR-026)."""
from quant_platform.services.research_validation.strategies.common.mechanics import (
    TRADING_DAYS,
    clean_returns,
    rebalance_dates,
    trim_overlap,
    vol_target,
)

__all__ = ["TRADING_DAYS", "clean_returns", "rebalance_dates", "trim_overlap", "vol_target"]
