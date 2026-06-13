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
# 3.D.4.2 — positions (regular table, UUID PK)
# ---------------------------------------------------------------------------
def test_positions_table_uses_uuid_pk(init_sql: str) -> None:
    body = _table_block(init_sql, "positions")
    assert body, "positions CREATE TABLE missing"
    # position_id UUID PRIMARY KEY DEFAULT gen_random_uuid()
    assert re.search(
        r"position_id\s+UUID\s+PRIMARY\s+KEY", body, re.IGNORECASE
    ), "positions must have UUID PRIMARY KEY"
    assert "gen_random_uuid" in body, "positions should default UUID via gen_random_uuid()"


def test_positions_has_unique_constraint(init_sql: str) -> None:
    body = _table_block(init_sql, "positions")
    # UNIQUE (strategy_id, run_id, stock_id, opened_at) per 21 §4.4
    assert re.search(
        r"UNIQUE\s*\(\s*strategy_id\s*,\s*run_id\s*,\s*stock_id\s*,\s*opened_at\s*\)",
        body,
        re.IGNORECASE,
    ), "positions missing UNIQUE (strategy_id, run_id, stock_id, opened_at)"


def test_positions_is_regular_table_not_hypertable(init_sql: str) -> None:
    # 21 §4.1 row 6 — positions = regular (not hypertable)
    assert not _has_hypertable(init_sql, "positions"), (
        "positions must remain a regular table (not hypertable)"
    )


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
# 3.D.4.4 — orders + fills hypertables (orders.signal_id FK → signals)
# ---------------------------------------------------------------------------
def test_orders_table_has_required_columns(init_sql: str) -> None:
    body = _table_block(init_sql, "orders")
    assert body, "orders CREATE TABLE missing"
    for col in (
        "order_id",
        "created_at",
        "signal_id",
        "broker",
        "stock_id",
        "side",
        "order_type",
        "quantity",
        "limit_price",
        "status",
        "broker_order_id",
        "submitted_at",
        "completed_at",
        "error_msg",
    ):
        assert col in body, f"orders missing column {col}"


def test_orders_signal_id_is_plain_column_not_fk_to_hypertable(init_sql: str) -> None:
    body = _table_block(init_sql, "orders")
    # orders.signal_id links to signals by value but must NOT be a SQL foreign key:
    # TimescaleDB 2.x rejects "foreign keys to hypertables", which aborts init.sql
    # and drops every table declared after orders. The link is enforced in app code.
    assert re.search(r"signal_id\s+UUID", body, re.IGNORECASE), \
        "orders must keep a signal_id UUID column"
    assert not re.search(
        r"signal_id\s+UUID[^,]*REFERENCES\s+signals",
        body,
        re.IGNORECASE,
    ), "orders.signal_id must NOT be a FK to the signals hypertable (TimescaleDB rejects it)"


def test_orders_is_hypertable(init_sql: str) -> None:
    assert _has_hypertable(init_sql, "orders")


def test_fills_table_has_required_columns(init_sql: str) -> None:
    body = _table_block(init_sql, "fills")
    assert body, "fills CREATE TABLE missing"
    for col in (
        "fill_id",
        "fill_time",
        "order_id",
        "signal_id",
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


def test_fills_is_hypertable(init_sql: str) -> None:
    assert _has_hypertable(init_sql, "fills")


def test_signals_defined_before_orders_in_file(init_sql: str) -> None:
    """FK targets must be declared before referencing tables."""
    sig_pos = init_sql.lower().find("create table") if False else 0
    sig_match = re.search(r"create\s+table[^;]*signals\s*\(", init_sql, re.IGNORECASE)
    ord_match = re.search(r"create\s+table[^;]*orders\s*\(", init_sql, re.IGNORECASE)
    assert sig_match is not None and ord_match is not None
    assert sig_match.start() < ord_match.start(), (
        "signals CREATE TABLE must precede orders (orders has FK to signals)"
    )
    _ = sig_pos  # silence unused


# ---------------------------------------------------------------------------
# 3.D.4.5 — risk_metrics + validation_runs
# ---------------------------------------------------------------------------
def test_risk_metrics_has_required_columns(init_sql: str) -> None:
    body = _table_block(init_sql, "risk_metrics")
    assert body, "risk_metrics CREATE TABLE missing"
    for col in (
        "metric_time",
        "strategy_id",
        "run_id",
        "current_dd",
        "var_95",
        "cvar_95",
        "portfolio_heat",
        "concentration_top1",
        "concentration_top3",
        "hhi",
        "sharpe_30d",
        "sortino_30d",
        "event_type",
        "event_context",
    ):
        assert col in body, f"risk_metrics missing column {col}"


def test_risk_metrics_is_hypertable(init_sql: str) -> None:
    assert _has_hypertable(init_sql, "risk_metrics")


def test_validation_runs_has_required_columns(init_sql: str) -> None:
    body = _table_block(init_sql, "validation_runs")
    assert body, "validation_runs CREATE TABLE missing"
    for col in (
        "run_id",
        "run_time",
        "method",
        "strategy_id",
        "params_json",
        "result_json",
        "summary_metric",
        "pass_threshold",
    ):
        assert col in body, f"validation_runs missing column {col}"
    assert re.search(
        r"run_id\s+UUID\s+PRIMARY\s+KEY", body, re.IGNORECASE
    ), "validation_runs must have UUID PRIMARY KEY"


def test_validation_runs_is_regular_table(init_sql: str) -> None:
    # 21 §4.1 row 11 — validation_runs = regular
    assert not _has_hypertable(init_sql, "validation_runs")


# ---------------------------------------------------------------------------
# 3.D.4.6 — alerts hypertable + data_quality_log enhancement
# ---------------------------------------------------------------------------
def test_alerts_has_required_columns(init_sql: str) -> None:
    body = _table_block(init_sql, "alerts")
    assert body, "alerts CREATE TABLE missing"
    for col in (
        "alert_id",
        "alert_time",
        "rule_id",
        "level",
        "title",
        "message",
        "context_json",
        "sent_to_discord",
        "sent_at",
    ):
        assert col in body, f"alerts missing column {col}"


def test_alerts_is_hypertable(init_sql: str) -> None:
    assert _has_hypertable(init_sql, "alerts")


def test_data_quality_log_has_enhanced_columns(init_sql: str) -> None:
    """21 §4.10 upgrades data_quality_log with source/check_type/severity/resolved."""
    body = _table_block(init_sql, "data_quality_log")
    assert body, "data_quality_log CREATE TABLE missing"
    for col in (
        "check_id",
        "check_time",
        "source",
        "check_type",
        "stock_id",
        "trade_date",
        "severity",
        "detail_json",
        "resolved",
        "resolved_at",
    ):
        assert col in body, f"data_quality_log missing column {col}"


# ---------------------------------------------------------------------------
# Total table count guard — 13 tables per spec
# ---------------------------------------------------------------------------
def test_all_thirteen_tables_present(init_sql: str) -> None:
    expected = {
        "daily_bars",
        "institutional_flows",
        "broker_chips",
        "universe",
        "trades",
        "equity_snapshots",
        "positions",
        "signals",
        "orders",
        "fills",
        "risk_metrics",
        "validation_runs",
        "alerts",
        "data_quality_log",
    }
    found = set(
        m.group(1).lower()
        for m in re.finditer(
            r"CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+(\w+)",
            init_sql,
            re.IGNORECASE,
        )
    )
    missing = expected - found
    assert not missing, f"missing tables in init.sql: {missing}"
