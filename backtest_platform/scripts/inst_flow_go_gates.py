"""Institutional-flow factor — GO gates: wider universe + WFA + PBO.

#86 showed the foreign-net-buy factor passes IS (1.30) + single-window OOS (1.04)
on 10 large-caps. Before any GO it must clear the deployment gates on a WIDER
universe: rolling Walk-Forward Analysis (not one OOS split) and Probability of
Backtest Overfitting (CSCV over the config landscape).

⚠️ SURVIVORSHIP: wider universe is still living symbols (no delisted) — large-cap
survivorship bias is small but a true GO needs a survivorship-clean re-run.

Run (after the wide ingest):  uv run python scripts/inst_flow_go_gates.py
"""
from __future__ import annotations

import itertools
from datetime import date

import numpy as np
import pandas as pd

from backtest_platform.research.is_harness import load_merged_parquet
from backtest_platform.strategies.inst_flow.strategy import InstFlowConfig, backtest_inst_flow
from backtest_platform.validation.metrics import cagr, sharpe
from backtest_platform.validation.pbo import probability_of_backtest_overfitting
from backtest_platform.validation.wfa import walk_forward_splits

WIDE = ['2330','2317','2454','2308','2382','2412','2303','2881','2882','2891',
        '2886','2884','1303','1301','1326','2002','2207','3008','3711','2357',
        '2379','2409','2474','4938','2603','2609','2615','1216','1101','2912',
        '2880','2885','2887','2890','9910','2105','1402','2618','2353','3045']

FIXED = InstFlowConfig(rebalance="quarterly", lookback_days=60, flow_source="foreign")
SPAN_START, SPAN_END = date(2015, 1, 1), date(2024, 12, 31)


def _load():
    close, vol, raw = {}, {}, {}
    for sid in WIDE:
        try:
            df = load_merged_parquet(sid)
        except Exception:  # noqa: BLE001
            continue
        df = df.assign(trade_date=pd.to_datetime(df["trade_date"])).set_index("trade_date").sort_index()
        close[sid], vol[sid], raw[sid] = df["close"].astype(float), df["volume"].astype(float), df
    return pd.DataFrame(close), pd.DataFrame(vol), raw


def _flow(raw, cols):
    return pd.DataFrame({s: raw[s][list(cols)].sum(axis=1).astype(float) for s in raw})


def main() -> None:
    close, vol, raw = _load()
    flow = _flow(raw, FIXED.flow_cols)
    print(f"panel: {close.shape[1]} symbols × {close.shape[0]} bars "
          f"[{close.index.min().date()}..{close.index.max().date()}]")

    # ---- Gate 1: rolling WFA (fixed config, OOS Sharpe per fold) ----------
    folds = walk_forward_splits(SPAN_START, SPAN_END, is_days=504, oos_days=252, step_days=252)
    oos_sharpes, is_sharpes = [], []
    for f in folds:
        is_r = backtest_inst_flow(close, flow, vol, FIXED, f.is_start, f.is_end).daily_returns
        oos_r = backtest_inst_flow(close, flow, vol, FIXED, f.oos_start, f.oos_end).daily_returns
        if len(oos_r) > 20 and len(is_r) > 20:
            is_sharpes.append(sharpe(is_r))
            oos_sharpes.append(sharpe(oos_r))
    oos = np.array(oos_sharpes)
    print(f"\n=== Gate 1 WFA ({len(oos)} folds, fixed config) ===")
    for i, (isr, oosr) in enumerate(zip(is_sharpes, oos_sharpes)):
        print(f"  fold {i}: IS {isr:.2f}  OOS {oosr:.2f}")
    med = float(np.median(oos)) if len(oos) else 0.0
    frac_pos = float((oos > 0).mean()) if len(oos) else 0.0
    frac_bar = float((oos > 1.0).mean()) if len(oos) else 0.0
    wfa_pass = med > 1.0 and frac_pos >= 0.6
    print(f"  median OOS Sharpe {med:.2f} | OOS>0 {frac_pos:.0%} | OOS>1.0 {frac_bar:.0%} "
          f"→ {'PASS' if wfa_pass else 'FAIL'} (need median>1.0 + >0 in >=60%)")

    # ---- Gate 2: PBO (CSCV over the config landscape, full span) ----------
    GRID = {"rebalance": ["monthly", "quarterly"], "lookback_days": [20, 40, 60],
            "flow_source": ["foreign", "foreign_trust"], "vol_target_annual": [None, 0.15]}
    keys = list(GRID)
    cols = {}
    for combo in itertools.product(*(GRID[k] for k in keys)):
        cfg = InstFlowConfig(**dict(zip(keys, combo)))
        fl = _flow(raw, cfg.flow_cols)
        r = backtest_inst_flow(close, fl, vol, cfg, SPAN_START, SPAN_END).daily_returns
        if len(r) > 100:
            cols["/".join(map(str, combo))] = r
    mat = pd.DataFrame(cols).dropna()
    pbo = probability_of_backtest_overfitting(mat.to_numpy(), n_splits=8)
    print(f"\n=== Gate 2 PBO ({mat.shape[1]} configs × {mat.shape[0]} bars, CSCV S=8) ===")
    print(f"  PBO {pbo:.1%} → {'PASS' if pbo < 0.30 else 'FAIL'} (need < 30%)")

    # ---- full-span fixed-config headline -----------------------------------
    full = backtest_inst_flow(close, flow, vol, FIXED, SPAN_START, SPAN_END).daily_returns
    print(f"\n=== full-span fixed config ===")
    print(f"  CAGR {cagr(full)*100:.1f}%  Sharpe {sharpe(full):.2f}")
    print(f"\nGO verdict: {'🟢 PASS all gates (still needs survivorship-clean)' if (wfa_pass and pbo < 0.30) else '🔴 NOT yet — a gate failed'}")


if __name__ == "__main__":
    main()
