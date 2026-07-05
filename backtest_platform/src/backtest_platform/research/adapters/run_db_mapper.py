"""Ledger record → ``runs`` hypertable row mappers (W4.1c).

These are pure functions that encode the ``runs`` table DDL shape
(``db_writer._RUNS_COLS``): they translate a research ledger record / RunConfig
into the row dict the DB mirror upserts. They belong in ``adapters`` (not
``domain``) because they carry persistence/DDL-schema knowledge, not business
rules. Kept separate from the IO writer so W5.2 (db_writer split) only has to
touch the mapping, never the write orchestration.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


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


def config_to_status_row(cfg: Any, status: str) -> dict[str, Any]:
    """Lifecycle row for a RunConfig that has no ledger record yet (A1 batch):
    identity + window from the config, no metrics/gate, caller-chosen status."""
    return {
        "run_id": cfg.run_id,
        "hypothesis": cfg.hypothesis,
        "strategy": cfg.strategy,
        "engine": cfg.engine,
        "stocks": list(cfg.stocks),
        "is_start": cfg.is_start,
        "is_end": cfg.is_end,
        "params": dict(cfg.params),
        "metrics": None,
        "gate_status": None,
        "gate_summary": None,
        "status": status,
        "trials_count": 0,
    }
