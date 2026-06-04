"""Candidate D — preliminary L3-degraded edge probe (NOT the survivorship-clean verdict).

Operator decision (delegated): run the FREE, no-FinLab probe first. This ingests a
CURRENT small/mid-cap sample (survivorship-biased = *optimistically* one-sided) and
runs v2 baseline vs v3.1b (dirB, best entry preset) over the two windows
(2015-2020, 2020-2024), chips=0 (same L3 condition as the large-cap no-edge result).

Read as a ONE-SIDED test:
  - NO edge even on a survivor sample → robust NEGATIVE (four-layer likely no edge in
    small/mid either; survivorship bias works *for* finding edge, so its absence is strong).
  - Edge appears → INCONCLUSIVE → triggers the survivorship-clean point-in-time run
    (turnover-proxy universe_builder + full ingest).

Run: `uv run python scripts/candidate_d_probe.py`
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import requests

from backtest_platform.data.finmind_etl import fetch_bundle, write_parquet
from backtest_platform.research.is_harness import load_merged_parquet, run_is
from backtest_platform.research.run_config import RunConfig
from backtest_platform.validation.gate_state import evaluate_gate

API = "https://api.finmindtrade.com/api/v4/data"
PARQUET_DIR = "data/parquet"
INGEST_START, INGEST_END = date(2014, 6, 1), date(2024, 12, 31)  # warmup before 2015
WINDOWS = [(date(2015, 1, 1), date(2020, 12, 31)), (date(2020, 1, 1), date(2024, 12, 31))]
PRESETS = ["v2", "v3.1b"]
N_SAMPLE = 20

_MEGA = {
    "2330", "2317", "2454", "2412", "2882", "2891", "2308", "1303", "1101",
    "3008", "2881", "2886", "2884", "2303", "3711", "2002", "1216", "2207",
    "2357", "2382", "2395", "2890", "2892", "5880", "2880", "2885", "2887",
    "1301", "1326", "2603", "2609", "2615", "6505", "3045", "4904", "2474",
}


def _token() -> str:
    env = Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("FINMIND_TOKEN="):
                return line.split("=", 1)[1].strip()
    return os.environ.get("FINMIND_TOKEN", "")


def _sample(token: str) -> list[str]:
    info = requests.get(API, params={"dataset": "TaiwanStockInfo", "token": token}, timeout=30).json()
    twse = sorted({
        str(r["stock_id"]) for r in info.get("data", [])
        if r.get("type") == "twse" and str(r.get("stock_id", "")).isdigit()
        and len(str(r["stock_id"])) == 4 and str(r["stock_id"]) not in _MEGA
    })
    step = max(1, len(twse) // N_SAMPLE)
    return twse[::step][:N_SAMPLE]


def _ingest(symbols: list[str], token: str) -> list[str]:
    ok: list[str] = []
    for sid in symbols:
        try:
            bundle = fetch_bundle(sid, INGEST_START, INGEST_END, token=token)
            write_parquet(bundle, Path(PARQUET_DIR))
            ok.append(sid)
            print(f"  ingested {sid}")
        except Exception as exc:  # noqa: BLE001 — skip unavailable symbols
            print(f"  skip {sid}: {type(exc).__name__} {str(exc)[:60]}")
    return ok


def _usable(symbols: list[str]) -> list[str]:
    """Symbols whose merged parquet actually loads with enough rows."""
    out = []
    for sid in symbols:
        try:
            if len(load_merged_parquet(sid)) >= 120:
                out.append(sid)
        except Exception:  # noqa: BLE001
            pass
    return out


def main() -> None:
    token = _token()
    if not token:
        print("❌ no FINMIND_TOKEN"); raise SystemExit(1)

    print("=== Candidate D preliminary probe (L3-degraded, survivorship-biased one-sided) ===\n")
    sample = _sample(token)
    print(f"sample ({len(sample)}): {', '.join(sample)}\ningesting (FinMind, ~1-2 min)...")
    ingested = _ingest(sample, token)
    universe = _usable(ingested)
    print(f"\nusable universe ({len(universe)}): {', '.join(universe)}\n")
    if len(universe) < 5:
        print("❌ too few usable symbols for a portfolio read"); raise SystemExit(1)

    print(f"{'preset':<7} {'window':<23} {'trades':>6} {'cagr':>8} {'sharpe':>7} "
          f"{'slipSh':>7} {'struct1%':>9} {'gate':>11}")
    print("-" * 90)
    rows = []
    for preset in PRESETS:
        for start, end in WINDOWS:
            cfg = RunConfig(hypothesis=f"四層 {preset} 在中小型 universe 是否有 edge",
                            preset=preset, stocks=tuple(universe), is_start=start, is_end=end)
            m = run_is(cfg)
            g = evaluate_gate(m)
            rows.append((preset, start, end, m, g))
            print(f"{preset:<7} {start.isoformat()+'..'+end.isoformat():<23} "
                  f"{m.get('trades', 0):>6} {m.get('cagr', 0):>8.4f} {m.get('sharpe', 0):>7.3f} "
                  f"{m.get('slippage_sharpe', 0):>7.3f} {m.get('struct1_pct', 0)*100:>8.1f}% "
                  f"{g.status.value:>11}")

    # verdict
    v31 = [r for r in rows if r[0] == "v3.1b"]
    any_pass = any(r[4].passed for r in rows)
    both_pos = all(r[3].get("cagr", 0) > 0 for r in v31)
    print("\n=== READ (one-sided, optimistically biased) ===")
    print(f"any gate PASS:        {any_pass}")
    print(f"v3.1b both windows cagr>0: {both_pos}")
    if not any_pass and not both_pos:
        print("→ 🔴 ROBUST NEGATIVE：連 survivorship-biased 中小型樣本都無 edge（偏誤本應助長 edge）"
              " → 四層在中小型大概率也無 edge。建議不買 FinLab、評估去 chip 變體或砍策略。")
    else:
        print("→ 🟡 INCONCLUSIVE：偏誤樣本出現 edge 跡象 → 需跑 survivorship-clean 點時序 universe"
              "（turnover-proxy universe_builder + 全 ingest）才能定論。")
    print("\n⚠ 限制：樣本=現存上市股（survivorship-biased）、chips=0（L3 退化）、N 小。"
          "非最終判決——僅 free 一面倒探針。")


if __name__ == "__main__":
    main()
