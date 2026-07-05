"""Short-term reversal — research workflow configuration (ADR-029).

Pre-registration discipline (ADR-025/030): every value below is a *literature*
default fixed BEFORE any real-data read, never tuned on the data this platform
holds. The reversal edge and its parameters come from:
  • Jegadeesh, N. (1990) *Evidence of Predictable Behavior of Security Returns*,
    JF 45(3) — short-term (monthly) reversal, decile long-loser portfolios.
  • Lehmann, B. (1990) *Fads, Martingales, and Market Efficiency*, QJE 105(1) —
    weekly contrarian portfolios; the weekly formation window (lookback 5).
  • The 1-day skip (``skip_days=1``) is the standard bid-ask-bounce guard between
    formation and holding (Jegadeesh & Titman 1993 apply the same skip to momentum).

The pre-registered ``_FIXED`` config is the truth-gate candidate and is NEVER
re-selected after the OOS commit: weekly / lookback 5 / skip 1 / decile (0.1) / lump.
"""
from datetime import date

from backtest_platform.config.universe import DEFAULT_UNIVERSE
from backtest_platform.research.finlab_universe import cached_universe_symbols
from backtest_platform.research.workflows.config import (
    DOEConfig,
    GOGatesConfig,
    PaperReplayConfig,
    TruthGateConfig,
)
from backtest_platform.strategies.reversal.strategy import ReversalConfig

# Survivorship-clean FinLab cache (built by the build_universe workflow, sub-project
# ②). Shared with inst_flow: the universe is factor-agnostic (survivorship-clean liquid
# large caps), only the signal differs. When present it is the survivorship-clean
# evidence that flips TRUTH_GATE below (ADR-032).
_UNIVERSE_CACHE_DIR = "data/parquet_finlab_universe"

# Survivor-only 40-stock fallback (ADR-024's set). The corrected truth gate (ADR-030)
# hard-fails it on survivorship until sub-project ② rebuilds the clean universe.
_WIDE = [
    "2330", "2317", "2454", "2308", "2382", "2412", "2303", "2881", "2882", "2891",
    "2886", "2884", "1303", "1301", "1326", "2002", "2207", "3008", "3711", "2357",
    "2379", "2409", "2474", "4938", "2603", "2609", "2615", "1216", "1101", "2912",
    "2880", "2885", "2887", "2890", "9910", "2105", "1402", "2618", "2353", "3045",
]

# Pre-registered fixed config — the literature reversal (weekly / 5 / skip 1 / decile).
_FIXED = ReversalConfig(rebalance="weekly", lookback_days=5, skip_days=1, top_fraction=0.1)
# DOE landscape: 2 × 3 × 2 = 12 configs. Skip is held at the literature value (1) —
# it is a microstructure guard, not a tunable edge knob, so it is NOT swept.
_GRID = {
    "rebalance": ["weekly", "monthly"],
    "lookback_days": [5, 10, 20],
    "top_fraction": [0.1, 0.2],
}

DOE = DOEConfig(
    strategy="reversal",
    grid=_GRID,
    symbols=list(DEFAULT_UNIVERSE),
    is_start=date(2016, 1, 1),
    is_end=date(2020, 12, 31),
)

GO_GATES = GOGatesConfig(
    strategy="reversal",
    fixed_config=_FIXED,
    config_grid=_GRID,
    symbols=_WIDE,
    is_start=date(2015, 1, 1),
    is_end=date(2024, 12, 31),
)

# TRUTH_GATE declaration follows the evidence (ADR-030/032 anti-self-deception): the
# survivorship-clean claim is NOT a hardwired constant — it tracks whether the FinLab
# survivorship-clean cache actually exists.
#   • cache PRESENT → declare it clean, point the gate at that cache (parquet_dir),
#     run the honest 2010→2024 full-span re-validation over the clean universe.
#   • cache ABSENT  → fall back to the survivor-only _WIDE set with survivorship_clean
#     left False, so the corrected gate (ADR-030) hard-fails until ② rebuilds the cache.
_CLEAN_UNIVERSE = cached_universe_symbols(_UNIVERSE_CACHE_DIR)

if _CLEAN_UNIVERSE:
    TRUTH_GATE = TruthGateConfig(
        strategy="reversal",
        fixed_config=_FIXED,
        symbols=_CLEAN_UNIVERSE,
        is_start=date(2010, 1, 1),
        oos_start=date(2021, 1, 1),
        is_end=date(2024, 12, 31),
        n_trials=12,  # matches _GRID cardinality (2×3×2) for DSR deflation
        pre_registered=True,
        slippage_stress=0.003,
        survivorship_clean=True,
        parquet_dir=_UNIVERSE_CACHE_DIR,
    )
else:
    TRUTH_GATE = TruthGateConfig(
        strategy="reversal",
        fixed_config=_FIXED,
        symbols=_WIDE,
        is_start=date(2015, 1, 1),
        oos_start=date(2021, 1, 1),
        is_end=date(2024, 12, 31),
        n_trials=12,  # matches _GRID cardinality (2×3×2)
        pre_registered=True,
        slippage_stress=0.003,
    )

PAPER_REPLAY = PaperReplayConfig(
    strategy="reversal",
    fixed_config=_FIXED,
    symbols=list(DEFAULT_UNIVERSE),
    as_of=date(2023, 1, 3),
)
