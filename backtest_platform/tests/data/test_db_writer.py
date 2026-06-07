"""DB writer tests — uses mock cursor; no real DB needed for unit tests.

A separate integration test runs against a live TimescaleDB when
``POSTGRES_HOST`` env var is set (or via docker compose locally).
"""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from backtest_platform.data.db_writer import (
    DBConfig,
    _upsert_frame,
)
from backtest_platform.data.schemas import ETLBundle


def test_db_config_from_env_reads_overrides(monkeypatch) -> None:
    monkeypatch.setenv("POSTGRES_HOST", "db.example")
    monkeypatch.setenv("POSTGRES_PORT", "6543")
    monkeypatch.setenv("POSTGRES_DB", "qt_test")
    monkeypatch.setenv("POSTGRES_USER", "u")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p")
    cfg = DBConfig.from_env()
    assert cfg.host == "db.example"
    assert cfg.port == 6543
    assert cfg.database == "qt_test"
    assert "host=db.example" in cfg.dsn()


def test_upsert_frame_empty_returns_zero() -> None:
    cur = MagicMock()
    n = _upsert_frame(cur, "daily_bars", ("stock_id", "trade_date"), pd.DataFrame())
    assert n == 0
    cur.execute.assert_not_called()


def test_upsert_frame_missing_column_raises() -> None:
    cur = MagicMock()
    df = pd.DataFrame({"stock_id": ["2330"]})  # missing trade_date and others
    with pytest.raises(ValueError, match="missing columns"):
        _upsert_frame(cur, "daily_bars", ("stock_id", "trade_date", "open"), df)


def test_upsert_frame_calls_execute_values_with_on_conflict() -> None:
    """Verify the generated SQL has correct INSERT ... ON CONFLICT DO UPDATE shape."""
    cur = MagicMock()
    df = pd.DataFrame(
        {
            "stock_id": ["2330", "2330"],
            "trade_date": [date(2024, 11, 1), date(2024, 11, 4)],
            "foreign_buy": [-8312, -992],
            "trust_buy": [452, 417],
            "dealer_buy": [-45, -184],
        }
    )
    with patch("psycopg2.extras.execute_values") as mock_exec:
        n = _upsert_frame(
            cur,
            "institutional_flows",
            ("stock_id", "trade_date", "foreign_buy", "trust_buy", "dealer_buy"),
            df,
        )
    assert n == 2
    assert mock_exec.call_count == 1
    call_args = mock_exec.call_args
    sql = call_args.args[1]
    rows = call_args.args[2]
    assert sql.startswith("INSERT INTO institutional_flows")
    assert "ON CONFLICT (stock_id, trade_date) DO UPDATE SET" in sql
    assert "foreign_buy = EXCLUDED.foreign_buy" in sql
    assert "trust_buy = EXCLUDED.trust_buy" in sql
    assert "dealer_buy = EXCLUDED.dealer_buy" in sql
    # Primary key columns must NOT appear in SET clause
    assert "stock_id = EXCLUDED.stock_id" not in sql
    assert "trade_date = EXCLUDED.trade_date" not in sql
    assert len(rows) == 2
    assert rows[0] == ("2330", date(2024, 11, 1), -8312, 452, -45)


# ---------------------------------------------------------------------------
# M2 additions — positions upsert (real impl) + signals/orders/fills stubs
# ---------------------------------------------------------------------------


def test_upsert_positions_calls_execute_values_with_unique_constraint() -> None:
    """positions uses ON CONFLICT against UNIQUE(strategy_id, run_id, stock_id, opened_at)."""
    from backtest_platform.data.db_writer import upsert_positions

    cur = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur

    rows = [
        {
            "strategy_id": "four_layer_resonance",
            "run_id": "run-001",
            "stock_id": "2330",
            "opened_at": "2026-05-30T09:01:23+08:00",
            "entry_price": 542.0,
            "quantity": 1000,
            "stop_loss": 520.0,
            "take_profit": 600.0,
            "status": "OPEN",
        }
    ]

    with patch(
        "backtest_platform.data.db_writer._connection"
    ) as mock_conn_ctx, patch(
        "psycopg2.extras.execute_values"
    ) as mock_exec:
        mock_conn_ctx.return_value.__enter__.return_value = conn
        n = upsert_positions(rows)

    assert n == 1
    assert mock_exec.call_count == 1
    sql = mock_exec.call_args.args[1]
    assert sql.startswith("INSERT INTO positions")
    assert (
        "ON CONFLICT (strategy_id, run_id, stock_id, opened_at) DO UPDATE SET" in sql
    ), "positions upsert must target UNIQUE constraint"
    # PK / unique columns must not be in SET clause
    for forbidden in ("strategy_id = EXCLUDED.strategy_id",
                      "opened_at = EXCLUDED.opened_at"):
        assert forbidden not in sql, f"forbidden SET clause: {forbidden}"
    # Mutable columns must be in SET clause
    for required in ("status = EXCLUDED.status", "exit_price = EXCLUDED.exit_price"):
        assert required in sql, f"missing SET clause: {required}"


def test_upsert_positions_empty_returns_zero() -> None:
    from backtest_platform.data.db_writer import upsert_positions

    with patch("backtest_platform.data.db_writer._connection") as mock_conn_ctx:
        n = upsert_positions([])
    assert n == 0
    mock_conn_ctx.assert_not_called()


def test_upsert_signals_stub_raises_not_implemented() -> None:
    """signals writer is M2 P2 / M4 — stub for forward-compat import."""
    from backtest_platform.data.db_writer import upsert_signals

    with pytest.raises(NotImplementedError, match="M4"):
        upsert_signals([{"signal_id": "x"}])


def test_upsert_orders_stub_raises_not_implemented() -> None:
    from backtest_platform.data.db_writer import upsert_orders

    with pytest.raises(NotImplementedError, match="M4"):
        upsert_orders([{"order_id": "x"}])


def test_upsert_fills_stub_raises_not_implemented() -> None:
    from backtest_platform.data.db_writer import upsert_fills

    with pytest.raises(NotImplementedError, match="M4"):
        upsert_fills([{"fill_id": "x"}])


# ---------------------------------------------------------------------------
# 8.G.1 — runs main table upsert (Run single-source-of-truth)
# ---------------------------------------------------------------------------


def test_upsert_runs_calls_execute_values_with_run_id_conflict() -> None:
    """runs uses ON CONFLICT (run_id) DO UPDATE; run_id/created_at stay immutable."""
    from backtest_platform.data.db_writer import upsert_runs

    cur = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur

    rows = [
        {
            "run_id": "a1b2c3d4e5f6",
            "hypothesis": "v3 entry beats v2 on 2330 IS window",
            "preset": "v3",
            "engine": "sim",
            "stocks": ["2330", "2317"],
            "is_start": date(2020, 1, 1),
            "is_end": date(2024, 12, 31),
            "git_sha": "deadbeef",
            "bundle_ref": "finmind@2024-12-31",
            "cost_assumptions": {"fee": 0.001425, "tax": 0.003},
            "params": {"min_structure": 2},
            "metrics": {"cagr": -0.018, "sharpe": -0.2},
            "status": "done",
            "trials_count": 1,
        }
    ]

    with patch(
        "backtest_platform.data.db_writer._connection"
    ) as mock_conn_ctx, patch(
        "psycopg2.extras.execute_values"
    ) as mock_exec:
        mock_conn_ctx.return_value.__enter__.return_value = conn
        n = upsert_runs(rows)

    assert n == 1
    assert mock_exec.call_count == 1
    sql = mock_exec.call_args.args[1]
    tuples = mock_exec.call_args.args[2]
    assert sql.startswith("INSERT INTO runs")
    assert "ON CONFLICT (run_id) DO UPDATE SET" in sql
    # Immutable columns must NOT be in SET clause
    for forbidden in ("run_id = EXCLUDED.run_id", "created_at = EXCLUDED.created_at"):
        assert forbidden not in sql, f"forbidden SET clause: {forbidden}"
    # Mutable columns must be in SET clause (re-runs update status/metrics/trials)
    for required in (
        "status = EXCLUDED.status",
        "metrics = EXCLUDED.metrics",
        "trials_count = EXCLUDED.trials_count",
    ):
        assert required in sql, f"missing SET clause: {required}"
    # JSONB columns must be serialized to json text (psycopg2 text→jsonb assignment cast)
    row = tuples[0]
    cols = sql[sql.index("(") + 1 : sql.index(")")].split(", ")
    by_col = dict(zip(cols, row))
    assert by_col["stocks"] == '["2330", "2317"]'
    assert by_col["metrics"] == '{"cagr": -0.018, "sharpe": -0.2}'
    assert by_col["hypothesis"] == "v3 entry beats v2 on 2330 IS window"


def test_upsert_runs_empty_returns_zero() -> None:
    from backtest_platform.data.db_writer import upsert_runs

    with patch("backtest_platform.data.db_writer._connection") as mock_conn_ctx:
        n = upsert_runs([])
    assert n == 0
    mock_conn_ctx.assert_not_called()


@pytest.mark.integration
def test_real_upsert_idempotent() -> None:
    """Round-trip against a live TimescaleDB. Skipped unless env says it's up."""
    import os

    if not os.environ.get("POSTGRES_INTEGRATION"):
        pytest.skip("set POSTGRES_INTEGRATION=1 to run against a live DB")

    from backtest_platform.data.db_writer import upsert_bundle

    bundle = ETLBundle(
        stock_id="TEST",
        start_date=date(2024, 11, 1),
        end_date=date(2024, 11, 1),
        daily_bars=pd.DataFrame(
            [
                {
                    "stock_id": "TEST",
                    "trade_date": date(2024, 11, 1),
                    "open": 100.0,
                    "high": 102.0,
                    "low": 99.0,
                    "close": 101.0,
                    "volume": 1000,
                    "adj_factor": 1.0,
                }
            ]
        ),
        institutional=pd.DataFrame(
            [
                {
                    "stock_id": "TEST",
                    "trade_date": date(2024, 11, 1),
                    "foreign_buy": 100,
                    "trust_buy": 50,
                    "dealer_buy": -10,
                }
            ]
        ),
        broker_chips=pd.DataFrame(
            [
                {
                    "stock_id": "TEST",
                    "trade_date": date(2024, 11, 1),
                    "top_broker_buy": 0,
                    "key_broker_buy": 0,
                    "gov_broker_buy": 0,
                    "geo_broker_buy": 0,
                    "day_trade_volume": 200,
                    "margin_offset_volume": 0,
                }
            ]
        ),
    )
    c1 = upsert_bundle(bundle)
    c2 = upsert_bundle(bundle)  # second run must not error
    assert c1 == c2 == {"daily_bars": 1, "institutional_flows": 1, "broker_chips": 1}
