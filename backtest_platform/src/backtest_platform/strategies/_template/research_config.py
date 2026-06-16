"""Research workflow configuration skeleton — copy + fill in for your strategy.

Replace every placeholder with actual values. Remove workflows you don't need.
"""
from datetime import date
from backtest_platform.research.workflows.config import DOEConfig

# Uncomment and fill in the workflows you want:
DOE = DOEConfig(
    strategy="template",
    grid={"max_daily_return": [0.3, 0.5]},  # replace with real params
    symbols=["2330", "2317"],
    is_start=date(2018, 1, 1),
    is_end=date(2022, 12, 31),
)
# GO_GATES = GOGatesConfig(...)
# TRUTH_GATE = TruthGateConfig(...)
# PAPER_REPLAY = PaperReplayConfig(...)
