"""Broker adapters — PaperBroker (sim撮合); Shioaji (live, M5).

W5.1b: PaperBroker moved to ``services.execution_gateway.paper_broker``; this
package now re-exports the same public API for backward compatibility.
"""
from backtest_platform.services.execution_gateway.paper_broker import (
    Fill,
    InsufficientPositionError,
    OrderSide,
    PaperBroker,
    Position,
)

__all__ = ["Fill", "InsufficientPositionError", "OrderSide", "PaperBroker", "Position"]
