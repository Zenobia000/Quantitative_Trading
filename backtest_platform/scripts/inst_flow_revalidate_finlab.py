"""inst_flow re-validation on a FinLab survivorship-clean universe (sub-project ②).

The earlier truth-gate run used only the 10 large-cap survivors I had cached
(rosy CAGR ~33%). With paid FinLab (① `finlab_source`) we now have full history +
delisted stocks, so this driver:

  1. builds a **survivorship-clean** factor universe from FinLab (point-in-time,
     liquid, incl. delisted — `research.finlab_universe.select_survivorship_universe`);
  2. ingests it into a dedicated parquet dir (`finlab_source.ingest_universe_finlab`);
  3. re-runs the *unchanged* ADR-025 two-stage truth-gate harness over that universe
     + a real OOS span (`scripts.inst_flow_truth_gate.main`).

Methodology is identical to ADR-024/025 — only the data is honest now. Prints the
real verdict + numbers; the result doc + WBS/ADR sync are authored from this output.

Run:  POSTGRES_INTEGRATION not needed (no DB). FINLAB_API_TOKEN in .env.
    uv run --extra data_paid --extra sprint1 --extra dev python scripts/inst_flow_revalidate_finlab.py
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from backtest_platform.data import finlab_source as fl
from backtest_platform.research.finlab_universe import select_survivorship_universe

SPAN_START, SPAN_END = date(2010, 1, 1), date(2024, 12, 31)
TOP_N_PER_QUARTER = 200
MIN_TURNOVER = 2e7  # 2,000萬 TWD trailing-20d avg (same floor as universe_builder)
CACHE_DIR = Path("data/parquet_finlab_universe")


def main() -> None:
    fl.login()
    get = fl._default_getter()  # our own module's getter

    print("fetching FinLab wide frames (market_value / adj_close / turnover) …")
    mv = get(fl._MARKET_VALUE)
    close = get(fl._ADJ["close"])
    turnover = get(fl._TURNOVER)

    rebal = list(pd.date_range(SPAN_START, SPAN_END, freq="QE").date)
    universe = select_survivorship_universe(
        mv, close, turnover, rebal, top_n=TOP_N_PER_QUARTER, min_turnover=MIN_TURNOVER
    )
    n_alive_today = int(close[universe].iloc[-1].notna().sum()) if universe else 0
    print(f"survivorship-clean universe: {len(universe)} names "
          f"({n_alive_today} alive today, {len(universe) - n_alive_today} delisted/suspended) "
          f"over {len(rebal)} quarterly rebalances {SPAN_START}..{SPAN_END}")

    print(f"\ningesting {len(universe)} names into {CACHE_DIR} …")
    res = fl.ingest_universe_finlab(universe, SPAN_START, SPAN_END, cache_dir=CACHE_DIR, getter=get)
    print(f"ingest ok={len(res.ok_symbols)} failed={len(res.failed_symbols)}")

    print(f"\n{'#'*70}\n# Re-running ADR-025 two-stage truth gate on survivorship-clean universe\n{'#'*70}")
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from inst_flow_truth_gate import main as truth_gate_main

    result = truth_gate_main(parquet_dir=str(CACHE_DIR), span=(SPAN_START, SPAN_END))

    print("\n=== RESULT (machine-readable) ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
