"""Research workflow configuration skeleton — copy + fill in for your strategy.

Declare the workflows your strategy should participate in by assigning the
module-level constants below (``DOE`` / ``GO_GATES`` / ``TRUTH_GATE`` /
``PAPER_REPLAY``). Each is read by the generic workflow in ``research/workflows/``;
remove the ones you don't need. Params in a grid must be real fields of your
strategy's config (they are validated via ``config_model(**params)``).
"""
from datetime import date

from backtest_platform.research.workflows.config import DOEConfig

# Minimal example: a DOE over the template's only knob. Replace strategy name,
# grid params, symbols and window with your strategy's real values.
DOE = DOEConfig(
    strategy="template",
    grid={"max_daily_return": [0.3, 0.5]},
    symbols=["2330", "2317"],
    is_start=date(2018, 1, 1),
    is_end=date(2022, 12, 31),
)

# GO_GATES = GOGatesConfig(...)      # WFA + PBO over a wide universe
# TRUTH_GATE = TruthGateConfig(...)  # ADR-025 two-stage gate (pre-registered)
# PAPER_REPLAY = PaperReplayConfig(...)
