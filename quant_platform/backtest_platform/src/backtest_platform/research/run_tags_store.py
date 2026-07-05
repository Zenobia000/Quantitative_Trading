"""Re-export shim (W4.1b) — moved to ``research.adapters.run_tags_store``."""
from __future__ import annotations

from backtest_platform.research.adapters.run_tags_store import (
    DEFAULT_RUN_TAGS_PATH,
    tag_run,
    tags_for,
)

__all__ = [
    "DEFAULT_RUN_TAGS_PATH",
    "tag_run",
    "tags_for",
]
