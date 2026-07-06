"""Institutional-flow strategy — research workflow configuration (ADR-029).

Migrated from the deleted ``scripts/inst_flow_*.py`` one-off drivers: the universe,
grid, fixed config and windows that those scripts hardcoded now live here as
declarations the generic workflows consume.
"""
from datetime import date

from quant_platform.packages.infrastructure.config.universe import DEFAULT_UNIVERSE
from quant_platform.packages.adapters.finlab_universe import cached_universe_symbols
from quant_platform.services.research_validation.workflows.config import (
    DOEConfig,
    GOGatesConfig,
    PaperReplayConfig,
    TruthGateConfig,
    UniverseConfig,
)
from quant_platform.services.research_validation.strategies.inst_flow.strategy import InstFlowConfig

# Dedicated survivorship-clean FinLab cache (built by the build_universe workflow,
# sub-project ②). The 2010-2024 full-span ingest lands here; when present it is the
# survivorship-clean evidence that flips TRUTH_GATE below.
_UNIVERSE_CACHE_DIR = "data/parquet_finlab_universe"

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

UNIVERSE = UniverseConfig(
    strategy="inst_flow",
    span_start=date(2010, 1, 1),
    span_end=date(2024, 12, 31),
    top_n=200,               # per-quarter top-N by market cap
    min_turnover=2e7,        # 2,000萬 TWD trailing-20d avg (universe_builder floor)
    cache_dir=_UNIVERSE_CACHE_DIR,
)

# TRUTH_GATE declaration follows the evidence (ADR-030/032 anti-self-deception):
# the survivorship-clean claim is NOT a hardwired constant — it tracks whether the
# FinLab survivorship-clean cache actually exists.
#   • cache PRESENT → declare it clean, point the gate at that cache (parquet_dir),
#     run the honest 2010→2024 full-span re-validation over the clean universe.
#   • cache ABSENT  → fall back to the survivor-only _WIDE set (ADR-024's false-
#     positive 40 names) with survivorship_clean left False, so the corrected gate
#     (ADR-030) hard-fails on survivorship until sub-project ② rebuilds the cache.
_CLEAN_UNIVERSE = cached_universe_symbols(_UNIVERSE_CACHE_DIR)

if _CLEAN_UNIVERSE:
    TRUTH_GATE = TruthGateConfig(
        strategy="inst_flow",
        fixed_config=_FIXED,
        symbols=_CLEAN_UNIVERSE,
        is_start=date(2010, 1, 1),
        oos_start=date(2021, 1, 1),
        is_end=date(2024, 12, 31),
        n_trials=16,  # 2x2x2x2 landscape (matches _GRID)
        pre_registered=True,
        slippage_stress=0.003,
        survivorship_clean=True,
        parquet_dir=_UNIVERSE_CACHE_DIR,
    )
else:
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
