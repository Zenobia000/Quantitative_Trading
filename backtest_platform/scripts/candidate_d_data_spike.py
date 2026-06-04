"""Candidate D §3 data-availability spike (design spec §3 — GATING).

Verifies, against the LIVE FinMind v4 API, whether the small/mid-cap pool has the
data the four-layer mechanism needs, 2015-01 → 2024-12:

  - OHLCV                 (TaiwanStockPrice)                          — L1/L4
  - 三大法人 institutional (TaiwanStockInstitutionalInvestorsBuySell)  — L2
  - 市值 / 上市狀態         (TaiwanStockInfo + a market-cap probe)       — universe builder input
  - 券商分點籌碼 chips      (FinLab paid — NOT checkable here)           — L3, user-gated

Samples N small/mid-cap stocks (TWSE, excluding known mega caps) and reports per
group: rows, first/last date, % of the ~10y span covered. Pure read; prints a
coverage table + a 🟢/🟡/🔴 conclusion for the FinMind-available groups.

Run: `uv run python scripts/candidate_d_data_spike.py`
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import requests

API = "https://api.finmindtrade.com/api/v4/data"
START, END = "2015-01-01", "2024-12-31"
SPAN_DAYS = 3652  # ~10 calendar years
N_SAMPLE = 12
RATE_SLEEP = 0.5  # FinMind free tier courtesy gap

# Known mega/large caps to EXCLUDE so the sample lands in the small/mid band
# (these are the already-tested no-edge large caps + other obvious top-50 names).
_MEGA = {
    "2330", "2317", "2454", "2412", "2882", "2891", "2308", "1303", "1101",
    "3008", "2881", "2886", "2884", "2303", "3711", "2002", "1216", "2207",
    "2357", "2382", "2395", "2890", "2892", "5880", "2880", "2885", "2887",
    "1301", "1326", "2603", "2609", "2615", "6505", "3045", "4904", "2474",
}


def _load_token() -> str:
    env = Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("FINMIND_TOKEN="):
                return line.split("=", 1)[1].strip()
    return os.environ.get("FINMIND_TOKEN", "")


def _get(token: str, dataset: str, data_id: str | None = None,
         start: str | None = None, end: str | None = None) -> dict:
    params = {"dataset": dataset, "token": token}
    if data_id:
        params["data_id"] = data_id
    if start:
        params["start_date"] = start
    if end:
        params["end_date"] = end
    try:
        r = requests.get(API, params=params, timeout=30)
        return r.json() if r.status_code == 200 else {"msg": f"HTTP {r.status_code}", "data": []}
    except Exception as exc:  # noqa: BLE001 — spike: report, don't crash
        return {"msg": f"ERR {type(exc).__name__}", "data": []}


def _coverage(rows: list[dict], date_key: str = "date") -> tuple[int, str, str, float]:
    if not rows:
        return 0, "-", "-", 0.0
    dates = sorted(r[date_key] for r in rows if r.get(date_key))
    if not dates:
        return len(rows), "-", "-", 0.0
    first, last = dates[0], dates[-1]
    # crude span coverage: trading days ~ 245/yr → expected ~2450 over 10y
    pct = min(100.0, 100.0 * len(rows) / 2450.0)
    return len(rows), first, last, pct


def main() -> None:
    token = _load_token()
    if not token:
        print("❌ no FINMIND_TOKEN — cannot run spike")
        raise SystemExit(1)

    print(f"=== Candidate D §3 data spike ({START}..{END}) ===\n")

    # 1) universe existence + sample small/mid-caps
    info = _get(token, "TaiwanStockInfo")
    all_rows = info.get("data", [])
    twse = [r for r in all_rows if r.get("type") == "twse"
            and str(r.get("stock_id", "")).isdigit() and len(str(r.get("stock_id"))) == 4]
    pool = [r for r in twse if r["stock_id"] not in _MEGA]
    print(f"TaiwanStockInfo: {len(all_rows)} rows | twse 4-digit {len(twse)} | "
          f"small/mid pool (excl mega) {len(pool)}")
    # deterministic spread across the pool (no RNG): every k-th by sorted id
    pool_sorted = sorted({r["stock_id"] for r in pool})
    if not pool_sorted:
        print("❌ empty pool — cannot sample"); raise SystemExit(1)
    step = max(1, len(pool_sorted) // N_SAMPLE)
    sample = pool_sorted[::step][:N_SAMPLE]
    print(f"sample ({len(sample)}): {', '.join(sample)}\n")

    # 2) market-cap probe (universe builder input) — try known dataset names
    cap_ok = None
    for ds in ("TaiwanStockMarketValue", "TaiwanStockMarketValueWeight", "TaiwanStockPER"):
        time.sleep(RATE_SLEEP)
        j = _get(token, ds, data_id=sample[0], start="2024-01-01", end="2024-03-31")
        if j.get("data"):
            cols = list(j["data"][0].keys())
            cap_ok = (ds, cols)
            break
    print(f"market-cap probe: {'✅ ' + cap_ok[0] + ' cols=' + str(cap_ok[1]) if cap_ok else '⚠ none of the tried datasets returned data'}\n")

    # 3) per-sample OHLCV + institutional coverage
    print(f"{'stock':<7} {'OHLCV rows':>10} {'span':>23} {'%cov':>6} | "
          f"{'INST rows':>9} {'span':>23} {'%cov':>6}")
    print("-" * 100)
    ohlcv_pcts, inst_pcts, both_ok = [], [], 0
    for sid in sample:
        time.sleep(RATE_SLEEP)
        px = _get(token, "TaiwanStockPrice", sid, START, END).get("data", [])
        time.sleep(RATE_SLEEP)
        inst = _get(token, "TaiwanStockInstitutionalInvestorsBuySell", sid, START, END).get("data", [])
        n_px, f_px, l_px, p_px = _coverage(px)
        n_in, f_in, l_in, p_in = _coverage(inst)
        ohlcv_pcts.append(p_px); inst_pcts.append(p_in)
        if p_px >= 50 and p_in >= 50:
            both_ok += 1
        print(f"{sid:<7} {n_px:>10} {f_px+'..'+l_px:>23} {p_px:>5.0f}% | "
              f"{n_in:>9} {f_in+'..'+l_in:>23} {p_in:>5.0f}%")

    # 4) conclusion
    avg_px = sum(ohlcv_pcts) / len(ohlcv_pcts)
    avg_in = sum(inst_pcts) / len(inst_pcts)
    print("\n=== CONCLUSION (FinMind-available groups) ===")
    print(f"OHLCV avg coverage:        {avg_px:.0f}%")
    print(f"Institutional avg coverage:{avg_in:.0f}%")
    print(f"both>=50% on {both_ok}/{len(sample)} sampled small/mid-caps")
    print(f"market-cap source:         {'available (' + cap_ok[0] + ')' if cap_ok else 'NOT found via tried datasets'}")
    verdict = "🟢 GREEN" if (avg_px >= 70 and avg_in >= 50 and both_ok >= len(sample) * 0.7) \
        else ("🟡 PARTIAL" if avg_px >= 50 else "🔴 RED")
    print(f"\nFinMind groups verdict: {verdict}")
    print("⚠ chip layer (券商分點 top_broker_buy/key_broker_buy) NOT covered — needs "
          "FinLab paid plan (design §3 最大風險, user-gated). Existing parquet already "
          "carries chips=0 (FinMind free limitation), so a FinMind-only Candidate D run "
          "tests L1/L2/L4 with L3 degraded — same caveat as the large-cap no-edge result.")


if __name__ == "__main__":
    main()
