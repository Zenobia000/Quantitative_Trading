"""Institutional-flow strategy — research workflow configuration (ADR-029).

Migrated from the deleted ``scripts/inst_flow_*.py`` one-off drivers: the universe,
grid, fixed config and windows that those scripts hardcoded now live here as
declarations the generic workflows consume.
"""
from datetime import date

from backtest_platform.config.universe import DEFAULT_UNIVERSE
from backtest_platform.research.workflows.config import (
    DOEConfig,
    GOGatesConfig,
    PaperReplayConfig,
    TruthGateConfig,
)
from backtest_platform.strategies.inst_flow.strategy import InstFlowConfig

# Survivor-only 40-stock universe (ADR-024's false-positive set). The corrected
# truth gate (ADR-030) hard-fails it on survivorship until sub-project 2 rebuilds
# the FinLab survivorship-clean universe as a platform workflow.
_WIDE = [
    "2330", "2317", "2454", "2308", "2382", "2412", "2303", "2881", "2882", "2891",
    "2886", "2884", "1303", "1301", "1326", "2002", "2207", "3008", "3711", "2357",
    "2379", "2409", "2474", "4938", "2603", "2609", "2615", "1216", "1101", "2912",
    "2880", "2885", "2887", "2890", "9910", "2105", "1402", "2618", "2353", "3045",
]

_FIXED = InstFlowConfig(rebalance="quarterly", lookback_days=60, flow_source="foreign")
_GRID = {
    "rebalance": ["monthly", "quarterly"],
    "lookback_days": [20, 60],
    "flow_source": ["foreign", "foreign_trust"],
    "vol_target_annual": [None, 0.15],
}

DOE = DOEConfig(
    strategy="inst_flow",
    grid=_GRID,
    symbols=list(DEFAULT_UNIVERSE),
    is_start=date(2016, 1, 1),
    is_end=date(2020, 12, 31),
)

GO_GATES = GOGatesConfig(
    strategy="inst_flow",
    fixed_config=_FIXED,
    config_grid=_GRID,
    symbols=_WIDE,
    is_start=date(2015, 1, 1),
    is_end=date(2024, 12, 31),
)

TRUTH_GATE = TruthGateConfig(
    strategy="inst_flow",
    fixed_config=_FIXED,
    symbols=_WIDE,
    is_start=date(2015, 1, 1),
    oos_start=date(2021, 1, 1),
    is_end=date(2024, 12, 31),
    n_trials=16,  # 2x2x2x2 landscape (matches _GRID: rebalance × lookback × flow × vol_target)
    pre_registered=True,
    slippage_stress=0.003,
)

PAPER_REPLAY = PaperReplayConfig(
    strategy="inst_flow",
    fixed_config=_FIXED,
    symbols=list(DEFAULT_UNIVERSE),
    as_of=date(2023, 1, 3),
)
