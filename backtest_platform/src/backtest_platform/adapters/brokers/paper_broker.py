"""Re-export shim (W5.1b) — moved to ``services.execution_gateway.paper_broker``."""
from __future__ import annotations

from backtest_platform.services.execution_gateway.paper_broker import (
    Fill,
    InsufficientPositionError,
    OrderSide,
    PaperBroker,
    Position,
)

__all__ = [
    "Fill",
    "InsufficientPositionError",
    "OrderSide",
    "PaperBroker",
    "Position",
]
