"""Four-Layer Resonance Strategy (v2.1).

Re-exports the M1 pure functions (scoring + signals + indicators) consumed by the
strategy runner (``research.runners.FourLayerRunner``) and the research IS harness
via the shared offline close-to-close sim (``strategies.four_layer_resonance.sim``).

Path migration 2026-05-31: was `backtest_platform.strategy`, renamed for
`strategies/` namespace per dev_docs/17 §5 (M2 directory restructure).
"""
from .config import StrategyConfig
from .indicators import macd_weighted, rsi, stochastic_kd
from .scoring import compute_scores
from .signals import compute_signals

__all__ = ["StrategyConfig", "compute_scores", "compute_signals", "macd_weighted", "rsi", "stochastic_kd"]
