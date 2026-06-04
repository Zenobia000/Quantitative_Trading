"""Momentum strategy — cross-sectional 12-1 (Jegadeesh & Titman 1993).

The platform's second strategy, structurally different from four-layer resonance,
proving the validation/research/gate stack is strategy-agnostic. See ``strategy``
for the pure backtest + ``research.momentum_harness`` for the IS→gate wiring.
"""
from __future__ import annotations

from backtest_platform.strategies.momentum.strategy import (
    MomentumConfig,
    MomentumResult,
    backtest_momentum,
)

__all__ = ["MomentumConfig", "MomentumResult", "backtest_momentum"]
