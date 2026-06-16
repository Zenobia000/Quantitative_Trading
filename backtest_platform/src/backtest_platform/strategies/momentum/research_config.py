"""Momentum strategy — research workflow configuration."""
from datetime import date
from backtest_platform.research.workflows.config import (
    DOEConfig, GOGatesConfig, TruthGateConfig, PaperReplayConfig,
)
from backtest_platform.strategies.momentum.strategy import MomentumConfig

_WIDE = ['2330', '2317', '2454', '2308', '2382', '2412', '2303', '2881', '2882', '2891', '2886', '2884', '1303', '1301', '1326', '2002', '2207', '3008', '3711', '2357']
_FIXED = MomentumConfig(lookback_days=252, top_fraction=1/3, rebalance="monthly")

DOE = DOEConfig(
    strategy="momentum",
    grid={
        "lookback_days":     [120, 252],
        "top_fraction":      [0.25, 1/3],
        "rebalance":         ["monthly", "quarterly"],
        "vol_target_annual": [None, 0.15],
    },
    symbols=_WIDE,
    is_start=date(2016, 1, 1),
    is_end=date(2020, 12, 31),
)

GO_GATES = GOGatesConfig(
    strategy="momentum",
    fixed_config=_FIXED,
    config_grid={
        "lookback_days":     [120, 252],
        "top_fraction":      [0.25, 1/3],
        "rebalance":         ["monthly", "quarterly"],
        "vol_target_annual": [None, 0.15],
    },
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
    n_trials=16,
    slippage_stress=0.003,
)

PAPER_REPLAY = PaperReplayConfig(
    strategy="momentum",
    fixed_config=_FIXED,
    symbols=_WIDE,
    as_of=date(2023, 1, 3),
)
