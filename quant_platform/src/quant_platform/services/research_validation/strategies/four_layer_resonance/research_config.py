"""Four-layer resonance — research workflow configuration (ADR-029).

Note (ADR-023): four_layer was found value-destructive on the tested universe.
This config is kept for platform completeness — any registered strategy can declare
a ``research_config`` — but only a DOE skeleton is provided. ``GO_GATES`` /
``TRUTH_GATE`` / ``PAPER_REPLAY`` are intentionally NOT declared (verdict already
NEGATIVE); attempting those workflows raises a clear "not declared" error.
"""
from datetime import date

from quant_platform.packages.infrastructure.config.universe import DEFAULT_UNIVERSE
from quant_platform.services.research_validation.workflows.config import DOEConfig

DOE = DOEConfig(
    strategy="four_layer",
    grid={
        "entry_min_layers": [3, 4],
        "entry_confirm_days": [1, 2],
        "entry_cooldown_bars": [0, 3],
    },
    symbols=list(DEFAULT_UNIVERSE),
    is_start=date(2018, 1, 1),
    is_end=date(2022, 12, 31),
)
