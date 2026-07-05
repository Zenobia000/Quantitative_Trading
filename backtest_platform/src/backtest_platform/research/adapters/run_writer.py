"""Run persistence writer: JSONL ledger (authoritative) + best-effort DB mirror.

Split out of ``research.run_persist`` in W4.1c. Closes the "``upsert_runs`` has
no production caller" gap (A0): every ledger append also mirrors the record into
the ``runs`` hypertable so the run board / SQL analytics can read runs without
parsing JSONL. The ledger stays the single source of truth — a DB failure
(down, bad creds, placeholder password) degrades to ledger-only with a warning,
never blocks or loses a run.

The ``db_writer`` import stays lazy (inside the try) so this module loads
without psycopg2 and the pure research layer never top-level-imports the DB.
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from loguru import logger

from backtest_platform.research.adapters.run_db_mapper import (
    config_to_status_row,
    run_record_to_db_row,
)
from backtest_platform.research.runs_store import DEFAULT_RUNS_PATH, append_run


def mark_run_status(cfg: Any, status: str, *, writer: Any = None) -> bool:
    """Best-effort lifecycle mark in the runs table (running|failed) so the run
    board sees in-flight state. Same degrade-to-warning contract as
    ``persist_run`` — never blocks or fails the run itself."""
    try:
        if writer is None:
            from backtest_platform.data import db_writer as writer
        writer.upsert_runs([config_to_status_row(cfg, status)])
        return True
    except Exception as exc:
        logger.warning(
            "runs status mark '{}' skipped for run_id={}: {}",
            status,
            getattr(cfg, "run_id", "?"),
            exc,
        )
        return False


def persist_run(
    record: Mapping,
    path: Path | str = DEFAULT_RUNS_PATH,
    *,
    writer: Any = None,
) -> bool:
    """Append ``record`` to the JSONL ledger, then best-effort mirror it to the
    ``runs`` hypertable. Returns True iff the DB mirror succeeded.

    ``writer`` is injectable for tests (mirrors ``make_db_sink``'s pattern);
    the default lazy import keeps this module loadable without psycopg2.
    """
    append_run(record, path)
    try:
        if writer is None:
            from backtest_platform.data import db_writer as writer
        writer.upsert_runs([run_record_to_db_row(record)])
        return True
    except Exception as exc:
        logger.warning(
            "runs DB mirror skipped for run_id={} (ledger is authoritative): {}",
            record.get("run_id"),
            exc,
        )
        return False
