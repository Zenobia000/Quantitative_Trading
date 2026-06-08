"""Institutional-flow factor — survivorship-clean re-verification (last GO gate).

#87 passed WFA + PBO on 40 living large-caps. The remaining tax is survivorship:
add the DELISTED losers (ingested via delisted_universe_ingest.py) so the universe
is point-in-time complete. ``backtest_inst_flow`` ranks ``dropna()`` per rebalance,
so a delisted name is ranked while it traded and drops out after — no backtest
change. If WFA + PBO still pass with delisted included, the survivorship caveat is
cleared and inst-flow graduates from conditional GO to a paper-ready candidate.

Run (after delisted_universe_ingest):  uv run python scripts/inst_flow_survivorship.py
"""
from __future__ import annotations

import itertools
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from backtest_platform.research.is_harness import load_merged_parquet
from backtest_platform.strategies.inst_flow.strategy import InstFlowConfig, backtest_inst_flow
from backtest_platform.validation.metrics import cagr, sharpe
from backtest_platform.validation.pbo import probability_of_backtest_overfitting
from backtest_platform.validation.wfa import walk_forward_splits

FIXED = InstFlowConfig(rebalance="quarterly", lookback_days=60, flow_source="foreign")
SPAN_START, SPAN_END = date(2015, 1, 1), date(2024, 12, 31)


def _all_symbols() -> list[str]:
    return sorted(
        p.name.replace("daily_bars__", "").replace(".parquet", "")
        for p in Path("data/parquet").glob("daily_bars__*.parquet")
    )


def _load(symbols):
    close, vol, raw = {}, {}, {}
    for sid in symbols:
        try:
            df = load_merged_parquet(sid)
        except Exception:  # noqa: BLE001 — delisted may lack a dataset; skip cleanly
            continue
        if "foreign_buy" not in df or df["foreign_buy"].abs().sum() == 0:
            continue  # no institutional flow → can't rank by it
        df = df.assign(trade_date=pd.to_datetime(df["trade_date"])).set_index("trade_date").sort_index()
        close[sid], vol[sid], raw[sid] = df["close"].astype(float), df["volume"].astype(float), df
    return pd.DataFrame(close), pd.DataFrame(vol), raw


def _flow(raw, cols):
    return pd.DataFrame({s: raw[s][list(cols)].sum(axis=1).astype(float) for s in raw})


def main() -> None:
    syms = _all_symbols()
    close, vol, raw = _load(syms)
    flow = _flow(raw, FIXED.flow_cols)
    print(f"survivorship-clean universe: {close.shape[1]} names (survivors + delisted) "
          f"× {close.shape[0]} bars")

    # Gate 1 — rolling WFA
    folds = walk_forward_splits(SPAN_START, SPAN_END, is_days=504, oos_days=252, step_days=252)
    oos = []
    for f in folds:
        oos_r = backtest_inst_flow(close, flow, vol, FIXED, f.oos_start, f.oos_end).daily_returns
        if len(oos_r) > 20:
            oos.append(sharpe(oos_r))
    oos = np.array(oos)
    med, fp, fb = float(np.median(oos)), float((oos > 0).mean()), float((oos > 1.0).mean())
    wfa_pass = med > 1.0 and fp >= 0.6
    print(f"\nGate 1 WFA ({len(oos)} folds): median OOS {med:.2f} | OOS>0 {fp:.0%} | OOS>1.0 {fb:.0%} "
          f"→ {'PASS' if wfa_pass else 'FAIL'}")
    print("  folds:", " ".join(f"{x:.2f}" for x in oos))

    # Gate 2 — PBO over config landscape
    GRID = {"rebalance": ["monthly", "quarterly"], "lookback_days": [20, 40, 60],
            "flow_source": ["foreign", "foreign_trust"], "vol_target_annual": [None, 0.15]}
    keys = list(GRID)
    cols = {}
    for combo in itertools.product(*(GRID[k] for k in keys)):
        cfg = InstFlowConfig(**dict(zip(keys, combo)))
        r = backtest_inst_flow(close, _flow(raw, cfg.flow_cols), vol, cfg, SPAN_START, SPAN_END).daily_returns
        if len(r) > 100:
            cols["/".join(map(str, combo))] = r
    mat = pd.DataFrame(cols).dropna()
    pbo = probability_of_backtest_overfitting(mat.to_numpy(), n_splits=8)
    print(f"\nGate 2 PBO ({mat.shape[1]} configs × {mat.shape[0]} bars): {pbo:.1%} "
          f"→ {'PASS' if pbo < 0.30 else 'FAIL'}")

    full = backtest_inst_flow(close, flow, vol, FIXED, SPAN_START, SPAN_END).daily_returns
    print(f"\nfull-span fixed config: CAGR {cagr(full)*100:.1f}% / Sharpe {sharpe(full):.2f}")
    ok = wfa_pass and pbo < 0.30
    print(f"\nSURVIVORSHIP-CLEAN verdict: "
          f"{'🟢 PASS — caveat cleared, paper-ready' if ok else '🔴 FAIL — survivorship tax kills it (like momentum)'}")


if __name__ == "__main__":
    main()
