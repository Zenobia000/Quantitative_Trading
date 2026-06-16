"""Four-layer resonance — research workflow configuration.

Note (ADR-023): four_layer was found to be value-destructive on the tested universe.
This config is kept for platform completeness only. Treat any results as historical.
"""
from datetime import date
from backtest_platform.research.workflows.config import DOEConfig
from backtest_platform.strategies.four_layer_resonance.config import StrategyConfig

DOE = DOEConfig(
    strategy="four_layer",
    grid={
        "entry_min_layers":    [3, 4],
        "entry_confirm_days":  [1, 2],
        "entry_cooldown_bars": [0, 3],
    },
    symbols=["2330","2317","2454","2308","2382","2412","2303","2881","2882","2891"],
    is_start=date(2018, 1, 1),
    is_end=date(2022, 12, 31),
)
# GO_GATES / TRUTH_GATE / PAPER_REPLAY not declared — ADR-023 verdict: NEGATIVE.
