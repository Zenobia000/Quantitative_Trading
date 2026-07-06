"""Momentum strategy — research workflow configuration (ADR-029)."""
from datetime import date

from quant_platform.packages.infrastructure.config.universe import DEFAULT_UNIVERSE
from quant_platform.services.research_validation.workflows.config import (
    DOEConfig,
    GOGatesConfig,
    PaperReplayConfig,
    TruthGateConfig,
)
from quant_platform.services.research_validation.strategies.momentum.strategy import MomentumConfig

_WIDE = list(DEFAULT_UNIVERSE)
_FIXED = MomentumConfig(lookback_days=252, top_fraction=1 / 3, rebalance="monthly")
_GRID = {
    "lookback_days": [120, 252],
    "top_fraction": [1 / 4, 1 / 3],
    "rebalance": ["monthly", "quarterly"],
    "vol_target_annual": [None, 0.15],
}

DOE = DOEConfig(
    strategy="momentum",
    grid=_GRID,
    symbols=_WIDE,
    is_start=date(2016, 1, 1),
    is_end=date(2020, 12, 31),
)

GO_GATES = GOGatesConfig(
    strategy="momentum",
    fixed_config=_FIXED,
    config_grid=_GRID,
    symbols=_WIDE,
    is_start=date(2015, 1, 1),
    is_end=date(2024, 12, 31),
)

TRUTH_GATE = TruthGateConfig(
    strategy="momentum",
    fixed_config=_FIXED,
    symbols=_WIDE,
    is_start=date(2015, 1, 1),
    oos_start=date(2021, 1, 1),
    is_end=date(2024, 12, 31),
    n_trials=16,  # 2x2x2x2 landscape
    slippage_stress=0.003,
)

PAPER_REPLAY = PaperReplayConfig(
    strategy="momentum",
    fixed_config=_FIXED,
    symbols=_WIDE,
    as_of=date(2023, 1, 3),
)
