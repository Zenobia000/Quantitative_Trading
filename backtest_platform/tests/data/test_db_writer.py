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
