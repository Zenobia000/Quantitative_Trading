"""Long-short composite — survivorship-clean GO gates (the structural lever).

Three long-only structures hit the same wall (Sharpe~0.90 / CAGR~13% / high PBO):
long-only large/mid-cap ≈ market return, can't clear the 18% bar. Long-short
neutralizes beta and isolates the cross-sectional spread (whose fixed-config OOS
was already 1.0-1.6). Tested on the 116-name survivorship-clean universe.

⚠️ Shorting frictions (借券 availability/cost, hard-to-borrow small/delisted names)
are real; ``borrow_rate_annual`` models a flat borrow cost but not availability.
A pass here is "the spread has edge", not yet "executable as-is".

Run:  uv run python scripts/long_short_gates.py
"""
from __future__ import annotations

import itertools
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from backtest_platform.research.is_harness import load_merged_parquet
from backtest_platform.strategies.multi_factor.strategy import MultiFactorConfig, backtest_multi_factor
from backtest_platform.validation.metrics import cagr, max_drawdown, sharpe
from backtest_platform.validation.pbo import probability_of_backtest_overfitting
from backtest_platform.validation.wfa import walk_forward_splits

FIXED = MultiFactorConfig(rebalance="quarterly", flow_lookback=60, vol_lookback_signal=60,
                          long_short=True, top_fraction=1/3, short_fraction=1/3)
SPAN_START, SPAN_END = date(2015, 1, 1), date(2024, 12, 31)


def _load():
    close, vol, flow = {}, {}, {}
    for p in sorted(Path("data/parquet").glob("daily_bars__*.parquet")):
        sid = p.name.replace("daily_bars__", "").replace(".parquet", "")
        try:
            df = load_merged_parquet(sid)
        except Exception:  # noqa: BLE001
            continue
        if "foreign_buy" not in df or df["foreign_buy"].abs().sum() == 0:
            continue
        df = df.assign(trade_date=pd.to_datetime(df["trade_date"])).set_index("trade_date").sort_index()
        close[sid], vol[sid], flow[sid] = df["close"].astype(float), df["volume"].astype(float), df["foreign_buy"].astype(float)
    return pd.DataFrame(close), pd.DataFrame(flow), pd.DataFrame(vol)


def main() -> None:
    close, flow, vol = _load()
    print(f"survivorship-clean universe: {close.shape[1]} names × {close.shape[0]} bars (LONG-SHORT)")

    folds = walk_forward_splits(SPAN_START, SPAN_END, is_days=504, oos_days=252, step_days=252)
    oos = [sharpe(r) for f in folds
           if len(r := backtest_multi_factor(close, flow, vol, FIXED, f.oos_start, f.oos_end).daily_returns) > 20]
    oos = np.array(oos)
    med, fp, fb = float(np.median(oos)), float((oos > 0).mean()), float((oos > 1.0).mean())
    wfa_pass = med > 1.0 and fp >= 0.6
    print(f"\nGate 1 WFA ({len(oos)} folds): median OOS {med:.2f} | OOS>0 {fp:.0%} | OOS>1.0 {fb:.0%} "
          f"→ {'PASS' if wfa_pass else 'FAIL'}")
    print("  folds:", " ".join(f"{x:.2f}" for x in oos))

    GRID = {"rebalance": ["monthly", "quarterly"], "flow_lookback": [20, 60],
            "vol_lookback_signal": [40, 120], "top_fraction": [0.2, 1/3], "short_fraction": [0.2, 1/3]}
    keys = list(GRID)
    cols = {}
    for combo in itertools.product(*(GRID[k] for k in keys)):
        cfg = MultiFactorConfig(long_short=True, **dict(zip(keys, combo)))
        r = backtest_multi_factor(close, flow, vol, cfg, SPAN_START, SPAN_END).daily_returns
        if len(r) > 100:
            cols["/".join(map(str, combo))] = r
    mat = pd.DataFrame(cols).dropna()
    pbo = probability_of_backtest_overfitting(mat.to_numpy(), n_splits=8)
    print(f"\nGate 2 PBO ({mat.shape[1]} configs × {mat.shape[0]} bars): {pbo:.1%} "
          f"→ {'PASS' if pbo < 0.30 else 'FAIL'}")

    full = backtest_multi_factor(close, flow, vol, FIXED, SPAN_START, SPAN_END).daily_returns
    print(f"\nfull-span fixed config: CAGR {cagr(full)*100:.1f}% / Sharpe {sharpe(full):.2f} / MaxDD {max_drawdown(full)*100:.1f}%")
    ok = wfa_pass and pbo < 0.30 and cagr(full) > 0.18 and sharpe(full) > 1.0
    print(f"\nLONG-SHORT (survivorship-clean) verdict: "
          f"{'🟢 PASS all gates (still: shorting feasibility + paper)' if ok else '🔴 NO-GO'}")


if __name__ == "__main__":
    main()
