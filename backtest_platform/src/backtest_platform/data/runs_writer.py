"""Idempotent upsert of run records into the ``runs`` main table — 8.G.1.

Extracted from ``data.db_writer`` in W5.2c and parked in ``data/`` (NOT a
service) so the Layer-2 research adapter (``research.adapters.run_writer``) can
lazy-import the runs writer WITHOUT routing through ``db_writer``. Keeping this
dependency chain — research → runs_writer → db_kernel → config.settings — free
of any service import is what lets later waves (W5.2d/e) turn ``db_writer`` into
a shim that re-exports service symbols without tripping import-linter contract 1.
"""
from __future__ import annotations

from typing import Any

from loguru import logger

from backtest_platform.data.db_kernel import DBConfig, _connection, _serialize_cell

# ---------------------------------------------------------------------------
# runs main table upsert — 8.G.1 (Run single-source-of-truth)
# ---------------------------------------------------------------------------
# Column order mirrors init.sql `runs` DDL. run_id is the deterministic 12-char
# RunConfig hash (PK); created_at defaults in the DB. JSONB columns carry the
# run's lineage/result payloads.
_RUNS_COLS = (
    "run_id",
    "hypothesis",
    "strategy",
    "engine",
    "stocks",
    "is_start",
    "is_end",
    "git_sha",
    "bundle_ref",
    "cost_assumptions",
    "params",
    "metrics",
    "gate_status",
    "gate_summary",
    "status",
    "trials_count",
)
# Immutable on conflict — identity + creation stamp never change on a re-run.
_RUNS_IMMUTABLE_COLS = ("run_id", "created_at")
# JSONB columns — serialized to json text (PostgreSQL text→jsonb assignment cast).
_RUNS_JSON_COLS = ("stocks", "cost_assumptions", "params", "metrics")


def upsert_runs(rows: list[dict[str, Any]], cfg: DBConfig | None = None) -> int:
    """Upsert run records into the `runs` main table (ON CONFLICT run_id DO UPDATE).

    A re-run of the same RunConfig (same deterministic run_id) updates the
    mutable result columns (status / metrics / trials_count / ...) while keeping
    run_id and created_at intact. JSONB columns accept dict/list and are
    json-serialized here. Empty list returns 0 without opening a connection.
    """
    if not rows:
        return 0

    cfg = cfg or DBConfig.from_env()
    from psycopg2.extras import execute_values  # type: ignore[import-not-found]

    update_cols = [c for c in _RUNS_COLS if c not in _RUNS_IMMUTABLE_COLS]
    set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
    sql = (
        f"INSERT INTO runs ({', '.join(_RUNS_COLS)}) VALUES %s "
        f"ON CONFLICT (run_id) DO UPDATE SET {set_clause}"
    )

    tuples = [
        tuple(_serialize_cell(col, row.get(col), _RUNS_JSON_COLS) for col in _RUNS_COLS)
        for row in rows
    ]

    with _connection(cfg) as conn, conn.cursor() as cur:
        execute_values(cur, sql, tuples, page_size=500)
    logger.info("upsert_runs wrote {} rows", len(rows))
    return len(rows)
