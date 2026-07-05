"""Execution gateway service — PaperBroker (sim撮合) + real daily-flow collaborators.

Physical home (W5.1b) for the order-execution cluster extracted out of the legacy
``adapters.brokers`` / ``orchestration`` packages: the simulated broker plus the
factory functions that wire ingest / risk / place / persistence collaborators for a
paper run. Old import paths keep working via re-export shims during the migration.
"""
from backtest_platform.services.execution_gateway.collaborators import (
    build_paper_collaborators,
    make_db_sink,
    make_ingest,
    make_place,
    make_risk_check,
)
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
    "build_paper_collaborators",
    "make_db_sink",
    "make_ingest",
    "make_place",
    "make_risk_check",
]
