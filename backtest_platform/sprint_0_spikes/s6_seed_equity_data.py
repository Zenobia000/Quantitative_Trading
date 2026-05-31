"""Sprint 0 Spike S6 (helper) — seed synthetic equity_snapshots data to TimescaleDB.

Creates the table (if missing) and inserts 1 year of synthetic daily equity values.
Run BEFORE s6_streamlit_dashboard.py.

Requirements:
- Docker TimescaleDB running (docker compose up -d)
- POSTGRES_* env vars in .env
"""
from __future__ import annotations

import os
import sys
import traceback
from datetime import date, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def get_conn():
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    import psycopg2

    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "quant_trading"),
        user=os.environ.get("POSTGRES_USER", "quant"),
        password=os.environ.get("POSTGRES_PASSWORD", "change_me_in_production"),
    )


DDL = """
CREATE TABLE IF NOT EXISTS equity_snapshots (
    snapshot_time TIMESTAMPTZ NOT NULL,
    strategy_id   TEXT        NOT NULL,
    equity        NUMERIC     NOT NULL,
    cash          NUMERIC     NOT NULL,
    positions_value NUMERIC   NOT NULL,
    open_positions INT        NOT NULL,
    portfolio_heat NUMERIC,
    drawdown      NUMERIC,
    PRIMARY KEY (snapshot_time, strategy_id)
);

-- Hypertable (idempotent: try, ignore if exists)
SELECT create_hypertable('equity_snapshots', 'snapshot_time',
                          if_not_exists => TRUE);
"""


def seed_synthetic_data(conn, strategy_id: str = "four_layer_resonance_v2.1", days: int = 365):
    rng = np.random.default_rng(42)
    start = date.today() - timedelta(days=days)
    init_equity = 1_000_000.0
    daily_returns = rng.normal(0.0005, 0.012, days)  # mean 0.05% / day, vol 1.2%
    equity_series = init_equity * np.cumprod(1 + daily_returns)
    running_max = np.maximum.accumulate(equity_series)
    drawdowns = (equity_series - running_max) / running_max

    rows = []
    for i, (eq, dd) in enumerate(zip(equity_series, drawdowns)):
        d = start + timedelta(days=i)
        cash = eq * rng.uniform(0.1, 0.4)
        pos_value = eq - cash
        n_pos = rng.integers(5, 20)
        heat = rng.uniform(0.02, 0.06)
        rows.append(
            (d, strategy_id, float(eq), float(cash), float(pos_value), int(n_pos),
             float(heat), float(dd))
        )

    with conn.cursor() as cur:
        cur.execute("DELETE FROM equity_snapshots WHERE strategy_id = %s", (strategy_id,))
        cur.executemany(
            """INSERT INTO equity_snapshots
               (snapshot_time, strategy_id, equity, cash, positions_value,
                open_positions, portfolio_heat, drawdown)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            rows,
        )
        conn.commit()
    return len(rows)


def main():
    print("Connecting to TimescaleDB...")
    try:
        conn = get_conn()
    except Exception as e:
        print(f"[ERROR] connection failed: {e}")
        print("Hint: docker compose up -d  (and verify .env credentials)")
        return 1

    try:
        with conn.cursor() as cur:
            cur.execute(DDL)
        conn.commit()
        print("Schema OK (equity_snapshots).")

        n = seed_synthetic_data(conn)
        print(f"Seeded {n} synthetic equity snapshots.")
        print("Now run: uv run streamlit run sprint_0_spikes/s6_streamlit_dashboard.py")
        return 0
    except Exception:
        traceback.print_exc()
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
