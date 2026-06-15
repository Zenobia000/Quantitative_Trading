"""Enlarge the momentum test universe — ingest ~100 more small/mid-caps (daily-adjusted).

(c) of the a→b→c plan: the binding limitation on the momentum verdict is the tiny
29-stock survivor universe. This ingests a deterministic spread of fresh small/mid-cap
symbols (FinMind, adjusted OHLCV + institutional via fetch_bundle → parquet), so
`momentum_validate` can re-run on a ~4x larger universe and test whether momentum's
edge holds with real diversification. Idempotent: skips already-cached symbols.

Run (long; ~15-20 min): uv run python scripts/momentum_universe_ingest.py
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
N_TARGET = 100
_MEGA = {"2330", "2317", "2454", "2412", "2882", "2891", "2308", "1303", "1101", "3008"}


def _token() -> str:
    env = Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("FINMIND_TOKEN="):
                return line.split("=", 1)[1].strip()
    return os.environ.get("FINMIND_TOKEN", "")


def _fresh_targets(token: str) -> list[str]:
    cached = {p.name.replace("daily_bars__", "").replace(".parquet", "")
              for p in PARQUET_DIR.glob("daily_bars__*.parquet")}
    info = requests.get(API, params={"dataset": "TaiwanStockInfo", "token": token}, timeout=30).json()
    twse = sorted({
        str(r["stock_id"]) for r in info.get("data", [])
        if r.get("type") == "twse" and str(r.get("stock_id", "")).isdigit()
        and len(str(r["stock_id"])) == 4 and str(r["stock_id"]) not in _MEGA
    })
    fresh = [s for s in twse if s not in cached]
    step = max(1, len(fresh) // N_TARGET)
    return fresh[::step][:N_TARGET]


def main() -> None:
    token = _token()
    if not token:
        print("❌ no FINMIND_TOKEN"); raise SystemExit(1)
    targets = _fresh_targets(token)
    print(f"ingesting {len(targets)} fresh small/mid-caps (adjusted OHLCV, {INGEST_START}..{INGEST_END})")
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
        except Exception as exc:  # noqa: BLE001 — skip unavailable, keep going
            print(f"  skip {sid}: {type(exc).__name__} {str(exc)[:60]}")
    total = len(list(PARQUET_DIR.glob("daily_bars__*.parquet")))
    print(f"✅ done: +{ok} ingested; universe now {total} daily_bars parquet")


if __name__ == "__main__":
    main()
