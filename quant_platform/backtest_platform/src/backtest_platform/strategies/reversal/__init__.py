"""Short-term reversal factor — a new edge family (non-momentum, non-flow).

Cross-sectional contrarian strategy: rank the universe by trailing short-horizon
return (skipping the most recent day to avoid bid-ask bounce), go long the biggest
*losers* equal-weight, rebalance weekly, hold the mean-reversion bounce. A
liquidity-provision edge orthogonal to price-momentum and to institutional flow —
Taiwan's retail-heavy market amplifies the short-term over-reaction the losers revert
from (Jegadeesh 1990; Lehmann 1990).

Reuses momentum's tested rebalance / cost / vol-target mechanics so only the *signal*
(short window + ascending sort) differs and the strategies are judged on identical
plumbing.
"""
from __future__ import annotations

from backtest_platform.strategies.reversal.strategy import (
    ReversalConfig,
    ReversalResult,
    backtest_reversal,
)

__all__ = ["ReversalConfig", "ReversalResult", "backtest_reversal"]
