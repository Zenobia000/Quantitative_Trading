"""Ingest the DELISTED stocks of 2014-2024 — the survivorship-clean correction.

The 130-stock momentum universe is current-listed survivors → optimistically biased.
The bias's source is the *losers that delisted and disappeared*. FinMind's
``TaiwanStockDelisting`` dataset lists them (id + delisting date); their truncated
price history is still retrievable. Ingesting them makes the universe
**survivorship-aware**: ``backtest_momentum`` already ranks point-in-time
(``mom.dropna()`` per rebalance), so a delisted name is ranked while it traded and
drops out automatically after delisting — no backtest change needed.

Run (long; ~10-15 min): uv run python scripts/delisted_universe_ingest.py
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import requests

from backtest_platform.data.finmind_etl import fetch_bundle, write_parquet

API = "https://api.finmindtrade.com/api/v4/data"
PARQUET_DIR = Path("data/parquet")
INGEST_START, INGEST_END = date(2014, 6, 1), date(2024, 12, 31)


def _token() -> str:
    env = Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("FINMIND_TOKEN="):
                return line.split("=", 1)[1].strip()
    return os.environ.get("FINMIND_TOKEN", "")


def _delisted_targets(token: str) -> list[str]:
    d = requests.get(API, params={"dataset": "TaiwanStockDelisting", "token": token},
                     timeout=30).json().get("data", [])
    return sorted({
        str(r["stock_id"]) for r in d
        if str(r.get("stock_id", "")).isdigit() and len(str(r["stock_id"])) == 4
        and not str(r["stock_id"]).startswith("00")  # exclude ETFs/funds
        and r.get("date", "") >= "2014-06-01"          # delisted during our window
    })


def main() -> None:
    token = _token()
    if not token:
        print("❌ no FINMIND_TOKEN"); raise SystemExit(1)
    targets = _delisted_targets(token)
    print(f"ingesting {len(targets)} delisted stocks (truncated OHLCV, {INGEST_START}..{INGEST_END})")
    ok = 0
    for sid in targets:
        if (PARQUET_DIR / f"daily_bars__{sid}.parquet").exists():
            continue
        try:
            bundle = fetch_bundle(sid, INGEST_START, INGEST_END, token=token)
            write_parquet(bundle, PARQUET_DIR)
            ok += 1
            if ok % 10 == 0:
                print(f"  ...{ok} ingested (last {sid})")
        except Exception as exc:  # noqa: BLE001 — many delisted have thin/no data; skip
            print(f"  skip {sid}: {type(exc).__name__} {str(exc)[:50]}")
    total = len(list(PARQUET_DIR.glob("daily_bars__*.parquet")))
    print(f"✅ done: +{ok} delisted ingested; universe now {total} daily_bars parquet")


if __name__ == "__main__":
    main()
