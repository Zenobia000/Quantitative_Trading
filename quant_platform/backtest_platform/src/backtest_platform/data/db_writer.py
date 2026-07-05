"""Back-compat re-export shim for the DB writers (W5.2 relocation).

Historically this module owned every TimescaleDB writer. The W5.2 wave split
each writer out to the module/service that owns its concern:

  * connection kernel (DBConfig / _connection / _serialize_cell) → data.db_kernel
  * runs main-table upsert (upsert_runs + _RUNS_* specs)          → data.runs_writer
  * ETL-bundle upsert (upsert_bundle / _upsert_frame + _*_COLS)   → services.data_platform.bundle_writer
  * telemetry writers (signals / equity / fills)                  → services.monitoring_ops.telemetry_writer

This module is now a pure re-export shim: the public surface (``__all__``) is
kept so existing ``from data.db_writer import …`` consumers and tests stay
untouched while the migration window is open.
"""
from __future__ import annotations

from backtest_platform.data.db_kernel import DBConfig, _connection, _serialize_cell
from backtest_platform.data.runs_writer import (
    _RUNS_COLS,
    _RUNS_IMMUTABLE_COLS,
    _RUNS_JSON_COLS,
    upsert_runs,
)
from backtest_platform.services.data_platform.bundle_writer import (
    _BROKER_CHIPS_COLS,
    _DAILY_BARS_COLS,
    _INSTITUTIONAL_COLS,
    _upsert_frame,
    upsert_bundle,
)
from backtest_platform.services.monitoring_ops.telemetry_writer import (
    _EQUITY_COLS,
    _EQUITY_PK,
    _FILLS_COLS,
    _SIGNALS_COLS,
    _execute_write,
    upsert_equity_snapshots,
    upsert_fills,
    upsert_signals,
)

__all__ = [
    "_BROKER_CHIPS_COLS",
    "_DAILY_BARS_COLS",
    "_EQUITY_COLS",
    "_EQUITY_PK",
    "_FILLS_COLS",
    "_INSTITUTIONAL_COLS",
    "_RUNS_COLS",
    "_RUNS_IMMUTABLE_COLS",
    "_RUNS_JSON_COLS",
    "_SIGNALS_COLS",
    "DBConfig",
    "_connection",
    "_execute_write",
    "_serialize_cell",
    "_upsert_frame",
    "upsert_bundle",
    "upsert_equity_snapshots",
    "upsert_fills",
    "upsert_runs",
    "upsert_signals",
]
