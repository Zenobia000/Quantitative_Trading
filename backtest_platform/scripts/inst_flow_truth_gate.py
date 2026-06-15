"""Institutional-flow factor — ADR-025 TWO-STAGE GATE evaluation.

The binary survivorship-clean re-run (inst_flow_survivorship.py) FAILed inst_flow
under ADR-016 because landscape PBO 42.9% > 30%. ADR-025 says: for a
*pre-registered* fixed config, landscape PBO measures config-SELECTION overfit and
does NOT disqualify it — the truth question is OOS breadth + a trials-deflated DSR.

This script feeds the *real* survivorship-clean numbers of the pre-registered
FIXED config (quarterly / lookback 60 / foreign) into validation.two_stage_gate:

  * survivorship_clean = True  (116 names incl. delisted)
  * pre_registered     = True  (a priori config, never re-selected)
  * pbo                = landscape PBO (carried, but ignored for pre-registered)
  * wfa_oos_positive_frac = fraction of WFA folds with OOS Sharpe > 0
  * dsr                = deflated Sharpe (n_trials = the 24-config landscape)
  * slippage_sharpe    = full-span Sharpe under +0.3% per-leg slippage (K3)

If the TruthGate returns REAL, the SizingGate prints the target weight — making
inst_flow the first paper-ready candidate. If REJECTED, even the best candidate
dies at the truth gate and the answer is a new edge family (external).

Run:  uv run python scripts/inst_flow_truth_gate.py
"""
from __future__ import annotations

import itertools
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from backtest_platform.research.is_harness import load_merged_parquet
from backtest_platform.strategies.inst_flow.strategy import InstFlowConfig, backtest_inst_flow
from backtest_platform.validation.full_report import full_validation_report
from backtest_platform.validation.metrics import cagr, sharpe
from backtest_platform.validation.pbo import probability_of_backtest_overfitting
from backtest_platform.validation.two_stage_gate import (
    SizingInput,
    TruthGateInput,
    compute_position_size,
    evaluate_truth_gate,
)
from backtest_platform.validation.wfa import walk_forward_splits

FIXED = InstFlowConfig(rebalance="quarterly", lookback_days=60, flow_source="foreign")
SPAN_START, SPAN_END = date(2015, 1, 1), date(2024, 12, 31)
K3_SLIPPAGE_PER_LEG = 0.003  # ADR-016 K3 robustness probe

# The config landscape the research actually searched — drives honest DSR/PBO.
GRID = {
    "rebalance": ["monthly", "quarterly"],
    "lookback_days": [20, 40, 60],
    "flow_source": ["foreign", "foreign_trust"],
    "vol_target_annual": [None, 0.15],
}


def _all_symbols(parquet_dir: str = "data/parquet") -> list[str]:
    return sorted(
        p.name.replace("daily_bars__", "").replace(".parquet", "")
        for p in Path(parquet_dir).glob("daily_bars__*.parquet")
    )


def _load(symbols, parquet_dir: str = "data/parquet"):
    close, vol, raw = {}, {}, {}
    for sid in symbols:
        try:
            df = load_merged_parquet(sid, parquet_dir=parquet_dir)
        except Exception:  # noqa: BLE001 — delisted may lack a dataset; skip cleanly
            continue
        if "foreign_buy" not in df or df["foreign_buy"].abs().sum() == 0:
            continue
        df = df.assign(trade_date=pd.to_datetime(df["trade_date"])).set_index("trade_date").sort_index()
        close[sid], vol[sid], raw[sid] = df["close"].astype(float), df["volume"].astype(float), df
    return pd.DataFrame(close), pd.DataFrame(vol), raw


def _flow(raw, cols):
    return pd.DataFrame({s: raw[s][list(cols)].sum(axis=1).astype(float) for s in raw})


def _per_period_sharpe(r: pd.Series) -> float:
    arr = np.asarray(r, dtype=float)
    arr = arr[np.isfinite(arr)]
    sd = arr.std(ddof=1)
    return float(arr.mean() / sd) if sd > 0 else 0.0


def main(*, parquet_dir: str = "data/parquet", span: tuple[date, date] | None = None) -> dict:
    span_start, span_end = span or (SPAN_START, SPAN_END)
    syms = _all_symbols(parquet_dir)
    close, vol, raw = _load(syms, parquet_dir)
    flow = _flow(raw, FIXED.flow_cols)
    print(f"survivorship-clean universe: {close.shape[1]} names (survivors + delisted) "
          f"× {close.shape[0]} bars\n")

    # ---- WFA OOS breadth (fixed config) ----------------------------------- #
    folds = walk_forward_splits(span_start, span_end, is_days=504, oos_days=252, step_days=252)
    oos = []
    for f in folds:
        r = backtest_inst_flow(close, flow, vol, FIXED, f.oos_start, f.oos_end).daily_returns
        if len(r) > 20:
            oos.append(sharpe(r))
    oos = np.array(oos)
    median_oos = float(np.median(oos))
    oos_positive_frac = float((oos > 0).mean())
    print(f"WFA: {len(oos)} folds | median OOS Sharpe {median_oos:.2f} | "
          f"OOS>0 {oos_positive_frac:.0%}")
    print("  folds:", " ".join(f"{x:.2f}" for x in oos))

    # ---- config landscape → PBO + cross-trial Sharpe variance (for DSR) --- #
    keys = list(GRID)
    per_period_sharpes, landscape_cols = [], {}
    for combo in itertools.product(*(GRID[k] for k in keys)):
        cfg = InstFlowConfig(**dict(zip(keys, combo)))
        r = backtest_inst_flow(close, _flow(raw, cfg.flow_cols), vol, cfg, span_start, span_end).daily_returns
        if len(r) > 100:
            landscape_cols["/".join(map(str, combo))] = r
            per_period_sharpes.append(_per_period_sharpe(r))
    mat = pd.DataFrame(landscape_cols).dropna()
    n_trials = mat.shape[1]
    landscape_pbo = probability_of_backtest_overfitting(mat.to_numpy(), n_splits=8)
    sharpe_variance = float(np.var(per_period_sharpes, ddof=1))
    print(f"\nlandscape: {n_trials} configs | PBO {landscape_pbo:.1%} "
          f"(selection-overfit — ignored for pre-registered) | "
          f"cross-trial per-period SR var {sharpe_variance:.4g}")

    # ---- DSR on the pre-registered fixed config (deflated by n_trials) ---- #
    full = backtest_inst_flow(close, flow, vol, FIXED, span_start, span_end).daily_returns
    report = full_validation_report(full, n_trials=n_trials, sharpe_variance=sharpe_variance)
    dsr = report["robustness"]["deflated_sharpe"]
    print(f"\nfixed config full-span: CAGR {cagr(full)*100:.1f}% / Sharpe {sharpe(full):.2f} "
          f"| DSR(deflated, n_trials={n_trials}) {dsr:.3f}")

    # ---- K3 slippage robustness ------------------------------------------- #
    slip_cfg = FIXED.with_extra_slippage(K3_SLIPPAGE_PER_LEG)
    slip_r = backtest_inst_flow(close, flow, vol, slip_cfg, span_start, span_end).daily_returns
    slip_sharpe = sharpe(slip_r)
    print(f"K3 (+{K3_SLIPPAGE_PER_LEG:.1%}/leg slippage): Sharpe {slip_sharpe:.2f}")

    # ---- TruthGate (ADR-025 §3.1) ----------------------------------------- #
    truth_in = TruthGateInput(
        survivorship_clean=True,
        pre_registered=True,
        pbo=landscape_pbo,
        wfa_oos_positive_frac=oos_positive_frac,
        dsr=dsr,
        slippage_sharpe=slip_sharpe,
    )
    truth = evaluate_truth_gate(truth_in)
    print(f"\n{'='*68}\nTRUTH GATE: {truth.verdict.value}")
    for reason in truth.reasons:
        print(f"  - {reason}")

    # ---- SizingGate (only if REAL) ---------------------------------------- #
    size = 0.0
    if truth.is_real:
        size = compute_position_size(
            SizingInput(oos_sharpe=median_oos, correlation_to_fleet=0.0, capacity_fraction=1.0, cagr=cagr(full))
        )
        print(f"\nSIZING GATE: target weight {size:.1%} "
              f"(OOS Sharpe {median_oos:.2f}, zero-corr first sleeve, full capacity)")
        print(f"\n🟢 inst_flow fixed config is PAPER-READY → 7.A.4 (target {size:.1%}, "
              f"ramp via §8.1 G1 Paper→Live 5%)")
    else:
        print("\n🔴 inst_flow dies at the truth gate — even the best candidate is "
              "not real under ADR-025. Next = new edge family (external).")
    print("=" * 68)

    return {
        "verdict": truth.verdict.value,
        "n_names": int(close.shape[1]),
        "n_bars": int(close.shape[0]),
        "span": (str(span_start), str(span_end)),
        "median_oos_sharpe": median_oos,
        "oos_positive_frac": oos_positive_frac,
        "landscape_pbo": landscape_pbo,
        "dsr": dsr,
        "full_cagr": float(cagr(full)),
        "full_sharpe": float(sharpe(full)),
        "slippage_sharpe": float(slip_sharpe),
        "target_weight": float(size),
    }


if __name__ == "__main__":
    main()
