"""Back-compat re-export shim for the telemetry reader (W5.2f relocation).

The telemetry reader (8.H.8) moved to
``services.monitoring_ops.telemetry_reader`` in W5.2f to sit with the rest of the
monitoring/ops service cluster (alert engine, notifier, jobs, telemetry writer).
This module keeps the old ``data.db_reader`` import path working via re-exports
so existing consumers (api.deps, strategy_runtime.after_close, tests) stay
untouched while the migration window is open.
"""
from __future__ import annotations

from backtest_platform.services.monitoring_ops.telemetry_reader import (
    BrokerState,
    PositionState,
    TelemetryReader,
    load_broker_state,
    reconstruct_positions,
)

__all__ = [
    "BrokerState",
    "PositionState",
    "TelemetryReader",
    "load_broker_state",
    "reconstruct_positions",
]
