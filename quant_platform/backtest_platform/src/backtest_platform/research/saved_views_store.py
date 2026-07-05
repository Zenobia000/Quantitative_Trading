"""Re-export shim (W4.1b) — moved to ``research.adapters.saved_views_store``."""
from __future__ import annotations

from backtest_platform.research.adapters.saved_views_store import (
    DEFAULT_SAVED_VIEWS_PATH,
    create_view,
    list_views,
)

__all__ = [
    "DEFAULT_SAVED_VIEWS_PATH",
    "create_view",
    "list_views",
]
