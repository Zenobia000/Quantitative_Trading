"""Re-export shim (W4.1c) — run persistence moved into ``research.adapters``.

The ledger→DB mirror mappers now live in ``adapters.run_db_mapper`` and the
write orchestration in ``adapters.run_writer``. This module keeps the historical
``backtest_platform.research.run_persist`` import path stable for existing
consumers (api/routers/runs, research.batch, research.cli) — ADR-R05: maintain
``backtest_platform`` import paths during the clean-arch split.
"""
from __future__ import annotations

from backtest_platform.research.adapters.run_db_mapper import (
    config_to_status_row,
    run_record_to_db_row,
)
from backtest_platform.research.adapters.run_writer import mark_run_status, persist_run

__all__ = [
    "config_to_status_row",
    "mark_run_status",
    "persist_run",
    "run_record_to_db_row",
]
