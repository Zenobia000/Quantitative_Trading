"""Verify TimescaleDB init.sql matches dev_docs/21_data_contract.md §4 spec.

This is a structural parser test — it reads the DDL file as text and checks
table / column / hypertable / index / FK declarations exist. It does NOT spin
up a real DB (that's the responsibility of the @pytest.mark.integration test
``test_real_upsert_idempotent`` in test_db_writer.py).

Why parse-based instead of running through SQL engine:
  * init.sql runs in TimescaleDB Docker, which we don't want to start for unit
    tests (CI must stay fast).
  * The spec in 21_data_contract.md §4 is the source of truth — this test
    asserts the file conforms to it, catching drift early.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


INIT_SQL_PATH = (
    Path(__file__).resolve().parents[2]
    / "docker"
    / "timescaledb"
    / "init.sql"
)


@pytest.fixture(scope="module")
def init_sql() -> str:
    """Load init.sql text once per module."""
    assert INIT_SQL_PATH.exists(), f"init.sql not found at {INIT_SQL_PATH}"
    return INIT_SQL_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _table_block(sql: str, table: str) -> str:
    """Return the body of CREATE TABLE <table> ( ... ); or empty string."""
    pattern = re.compile(
        rf"CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+{re.escape(table)}\s*\((.*?)\)\s*;",
        re.IGNORECASE | re.DOTALL,
    )
    m = pattern.search(sql)
    return m.group(1) if m else ""


def _has_hypertable(sql: str, table: str) -> bool:
    pattern = re.compile(
        rf"create_hypertable\s*\(\s*'{re.escape(table)}'",
        re.IGNORECASE,
    )
    return bool(pattern.search(sql))


def _has_index_on(sql: str, table: str) -> bool:
    pattern = re.compile(
        rf"CREATE\s+(?:UNIQUE\s+)?INDEX(?:\s+IF\s+NOT\s+EXISTS)?[^;]*?ON\s+{re.escape(table)}\b",
        re.IGNORECASE | re.DOTALL,
    )
    return bool(pattern.search(sql))


_COLUMN_TYPE_RE = re.compile(
    r"^\s*(\w+)\s+"
    r"(TEXT|JSONB|DATE|TIMESTAMPTZ|INTEGER|INT|BIGINT|NUMERIC|BOOLEAN|UUID|BIGSERIAL)\b",
    re.IGNORECASE,
)
# Line-leading tokens that are constraints, not columns (defensive; the type
# whitelist above already excludes them since none is followed by a type kw).
_NON_COLUMN_TOKENS = {"CONSTRAINT", "PRIMARY", "UNIQUE", "FOREIGN", "CHECK"}


def _column_names(body: str) -> set[str]:
    """Extract column identifiers from a CREATE TABLE body.

    A column line is ``<name> <TYPE> ...``; constraint lines (CONSTRAINT / PRIMARY
    KEY / UNIQUE / CHECK) never have a type keyword in that position, so the type
    whitelist filters them out.
    """
    names: set[str] = set()
    for line in body.splitlines():
        m = _COLUMN_TYPE_RE.match(line)
        if m and m.group(1).upper() not in _NON_COLUMN_TOKENS:
            names.add(m.group(1))
    return names


# ---------------------------------------------------------------------------
# 3.D.4.1 — equity_snapshots hypertable + retention policy
# ---------------------------------------------------------------------------
def test_equity_snapshots_has_required_columns(init_sql: str) -> None:
    body = _table_block(init_sql, "equity_snapshots")
    assert body, "equity_snapshots CREATE TABLE missing"
    for col in (
        "snapshot_time",
        "strategy_id",
        "mode",
        "run_id",
        "equity",
        "cash",
        "positions_value",
        "open_positions",
        "portfolio_heat",
        "drawdown",
        "daily_return",
        "cumulative_return",
    ):
        assert col in body, f"equity_snapshots missing column {col}"


def test_equity_snapshots_is_hypertable(init_sql: str) -> None:
    assert _has_hypertable(init_sql, "equity_snapshots")


def test_equity_snapshots_has_retention_policy(init_sql: str) -> None:
    # 21 §4.3 — 90-day retention for backtest mode
    pattern = re.compile(
        r"add_retention_policy\s*\(\s*'equity_snapshots'\s*,\s*INTERVAL\s*'90\s+days'",
        re.IGNORECASE,
    )
    assert pattern.search(init_sql), "equity_snapshots missing 90-day retention policy"


# ---------------------------------------------------------------------------
# 3.D.4.3 — signals hypertable + JSONB reason + GIN index
# ---------------------------------------------------------------------------
def test_signals_has_required_columns(init_sql: str) -> None:
    body = _table_block(init_sql, "signals")
    assert body, "signals CREATE TABLE missing"
    for col in (
        "signal_id",
        "signal_time",
        "strategy_id",
        "run_id",
        "stock_id",
        "action",
        "priority",
        "reason_json",
        "submitted",
        "submitted_at",
    ):
        assert col in body, f"signals missing column {col}"
    assert "JSONB" in body.upper(), "signals.reason_json must be JSONB"


def test_signals_is_hypertable(init_sql: str) -> None:
    assert _has_hypertable(init_sql, "signals")


def test_signals_has_gin_index_on_reason_json(init_sql: str) -> None:
    # GIN index enables efficient JSONB containment queries
    pattern = re.compile(
        r"CREATE\s+INDEX[^;]*?ON\s+signals\s+USING\s+GIN\s*\(\s*reason_json\s*\)",
        re.IGNORECASE | re.DOTALL,
    )
    assert pattern.search(init_sql), "signals missing GIN index on reason_json"


# ---------------------------------------------------------------------------
# ADR-038 §4.7 — fills : the single execution store (no separate orders table)
# ---------------------------------------------------------------------------
def test_fills_table_has_required_columns(init_sql: str) -> None:
    body = _table_block(init_sql, "fills")
    assert body, "fills CREATE TABLE missing"
    for col in (
        "fill_id",
        "fill_time",
        "order_id",
        "signal_id",
        "strategy_id",  # ADR-038 — per-sleeve P&L attribution
        "stock_id",
        "side",
        "fill_price",
        "fill_quantity",
        "commission",
        "tax",
        "slippage_bps",
        "broker",
        "broker_trade_id",
    ):
        assert col in body, f"fills missing column {col}"


def test_fills_strategy_id_is_not_null(init_sql: str) -> None:
    # ADR-038 — strategy_id must be NOT NULL so every fill is sleeve-attributable.
    body = _table_block(init_sql, "fills")
    assert re.search(
        r"strategy_id\s+TEXT\s+NOT\s+NULL", body, re.IGNORECASE
    ), "fills.strategy_id must be TEXT NOT NULL"


def test_fills_signal_id_is_plain_column_not_fk_to_hypertable(init_sql: str) -> None:
    body = _table_block(init_sql, "fills")
    # fills.signal_id links to signals by value but must NOT be a SQL foreign key:
    # TimescaleDB 2.x rejects "foreign keys to hypertables", which aborts init.sql.
    assert re.search(r"signal_id\s+UUID", body, re.IGNORECASE), \
        "fills must keep a signal_id UUID column"
    assert not re.search(
        r"signal_id\s+UUID[^,]*REFERENCES\s+signals",
        body,
        re.IGNORECASE,
    ), "fills.signal_id must NOT be a FK to the signals hypertable (TimescaleDB rejects it)"


def test_fills_is_hypertable(init_sql: str) -> None:
    assert _has_hypertable(init_sql, "fills")


def test_fills_has_strategy_index(init_sql: str) -> None:
    # ADR-038 — index (strategy_id, fill_time DESC) unblocks per-sleeve P&L reads.
    assert re.search(
        r"CREATE\s+INDEX[^;]*ON\s+fills\s*\(\s*strategy_id\s*,\s*fill_time\s+DESC",
        init_sql,
        re.IGNORECASE,
    ), "fills missing index on (strategy_id, fill_time DESC)"


def test_signals_defined_before_fills_in_file(init_sql: str) -> None:
    """signals must be declared before fills (fills.signal_id links to signals)."""
    sig_match = re.search(r"create\s+table[^;]*signals\s*\(", init_sql, re.IGNORECASE)
    fill_match = re.search(r"create\s+table[^;]*fills\s*\(", init_sql, re.IGNORECASE)
    assert sig_match is not None and fill_match is not None
    assert sig_match.start() < fill_match.start(), (
        "signals CREATE TABLE must precede fills (fills.signal_id links to signals)"
    )


# ---------------------------------------------------------------------------
# ADR-038 schema convergence — table inventory guard
# ---------------------------------------------------------------------------
def test_surviving_tables_present(init_sql: str) -> None:
    """Post ADR-038: exactly 7 tables survive (8 zero-IO tables dropped)."""
    expected = {
        "daily_bars",
        "institutional_flows",
        "broker_chips",
        "runs",
        "equity_snapshots",
        "signals",
        "fills",
    }
    found = set(
        m.group(1).lower()
        for m in re.finditer(
            r"CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+(\w+)",
            init_sql,
            re.IGNORECASE,
        )
    )
    assert found == expected, (
        f"init.sql table set drifted from the ADR-038 target.\n"
        f"  unexpected: {found - expected}\n"
        f"  missing: {expected - found}"
    )


def test_dropped_tables_absent(init_sql: str) -> None:
    """ADR-038 dropped these 8 zero-IO / inverted tables — they must not return.

    `orders` + `positions` come back when a real producer lands (M5 broker order
    lifecycle); the other six had zero prod IO and are re-added only on demand.
    """
    for table in (
        "trades",
        "universe",
        "orders",
        "positions",
        "risk_metrics",
        "validation_runs",
        "data_quality_log",
        "alerts",
    ):
        assert not _table_block(init_sql, table), (
            f"{table} was dropped by ADR-038 but reappeared in init.sql"
        )
        assert not _has_hypertable(init_sql, table), (
            f"{table} hypertable statement lingered after ADR-038 drop"
        )


# ---------------------------------------------------------------------------
# 8.G.1 — runs main table: DDL must stay in lock-step with db_writer._RUNS_COLS.
# ADR-028 renamed preset→strategy in the writer; the DDL layer was left behind,
# which makes upsert_runs INSERT an undefined column at runtime. This drift
# guard fails the build the moment the two diverge again.
# ---------------------------------------------------------------------------
def test_runs_table_columns_match_db_writer_cols(init_sql: str) -> None:
    from backtest_platform.data.db_writer import _RUNS_COLS

    body = _table_block(init_sql, "runs")
    assert body, "runs CREATE TABLE missing"
    ddl_cols = _column_names(body)
    # _RUNS_COLS omits created_at (DB-defaulted, callers never pass it); the DDL
    # carries it, so the expected set is the writer columns plus created_at.
    expected = set(_RUNS_COLS) | {"created_at"}
    assert ddl_cols == expected, (
        f"runs DDL columns drifted from db_writer._RUNS_COLS.\n"
        f"  only in DDL: {ddl_cols - expected}\n"
        f"  only in writer: {expected - ddl_cols}"
    )


def test_runs_table_has_no_legacy_preset_column(init_sql: str) -> None:
    # ADR-028 removed `preset` entirely; its reappearance means a partial revert.
    body = _table_block(init_sql, "runs")
    assert body, "runs CREATE TABLE missing"
    assert "preset" not in _column_names(body), (
        "runs.preset is a legacy column removed by ADR-028 (use `strategy`)"
    )


def test_runs_index_references_strategy_not_preset(init_sql: str) -> None:
    # The lookup index must target the live column name, else CREATE INDEX aborts.
    assert re.search(
        r"CREATE\s+INDEX[^;]*ON\s+runs\s*\(\s*strategy\b",
        init_sql,
        re.IGNORECASE,
    ), "expected an index on runs(strategy, ...)"
    assert not re.search(
        r"CREATE\s+INDEX[^;]*ON\s+runs\s*\(\s*preset\b",
        init_sql,
        re.IGNORECASE,
    ), "runs index still references the removed `preset` column"
