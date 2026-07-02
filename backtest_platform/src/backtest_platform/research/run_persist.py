"""Run persistence: JSONL ledger (authoritative) + best-effort TimescaleDB mirror.

Closes the "``upsert_runs`` has no production caller" gap (A0): every ledger
append now also mirrors the record into the ``runs`` hypertable so the run
board / SQL analytics can read runs without parsing JSONL. The ledger stays
the single source of truth — a DB failure (down, bad creds, placeholder
password) degrades to ledger-only with a warning, never blocks or loses a run.
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from loguru import logger

from backtest_platform.research.runs_store import DEFAULT_RUNS_PATH, append_run


def run_record_to_db_row(record: Mapping) -> dict[str, Any]:
    """Pure mapping: ledger run record → ``runs`` table row (db_writer._RUNS_COLS).

    * ``window: [start, end]`` splits into the DDL's ``is_start`` / ``is_end``.
    * ``status`` / ``trials_count`` are NOT NULL in the DDL and absent from the
      record — a persisted record is by definition a completed single trial.
    * The 審判庭 verdict (``gate_status`` / ``gate_summary``) rides along so the
      board can badge runs straight from SQL.
    """
    window = record.get("window") or (None, None)
    return {
        "run_id": record.get("run_id"),
        "hypothesis": record.get("hypothesis"),
        "strategy": record.get("strategy"),
        "engine": record.get("engine", "sim"),
        "stocks": record.get("stocks"),
        "is_start": window[0],
        "is_end": window[1],
        "params": record.get("params"),
        "metrics": record.get("metrics"),
        "gate_status": record.get("gate_status"),
        "gate_summary": record.get("gate_summary"),
        "status": "done",
        "trials_count": 1,
    }


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
