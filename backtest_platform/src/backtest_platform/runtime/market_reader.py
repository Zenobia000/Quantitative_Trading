"""Re-export shim (W5.1d) — moved to ``services.strategy_runtime.live_session``.

The live market reader + forward-paper execution core now lives in the
strategy_runtime service (execution physically separated from research). This
shim keeps the historical ``backtest_platform.runtime.market_reader`` import
path stable for the after-close daemon and tests during the transition.
"""
from __future__ import annotations

from backtest_platform.services.strategy_runtime.live_session import (
    PanelGetter,
    check_panel_freshness,
    live_config_for_date,
    make_position_signal_fn,
    read_live_panel,
    run_forward_session,
)

__all__ = [
    "PanelGetter",
    "check_panel_freshness",
    "live_config_for_date",
    "make_position_signal_fn",
    "read_live_panel",
    "run_forward_session",
]
