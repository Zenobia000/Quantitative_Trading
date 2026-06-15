"""Momentum full anti-overfit validation — PBO + DSR + WFA on the platform's own modules.

The rigorous, QUANTIFIED complement to the adversarial verification: take the same
12-1 momentum, sweep a 30-config parameter grid, and run the strategy through the
platform's overfit machinery for the first time on a real strategy —

  - PBO (CSCV, Bailey et al. 2017): how often does the IS-best config land below
    the OOS median? > 0.30 ⇒ overfit (ADR-016 bar).
  - DSR (Bailey & López de Prado 2014): does the best Sharpe survive deflation by
    the 30 trials searched? Pass = DSR > 0.95.
  - WFA (purge+embargo): pick the IS-best config per fold, score it OOS. Does the
    OOS Sharpe collapse vs IS? (the true held-out test.)

Uses cached parquet only. Run:
    uv run python scripts/momentum_validate.py --universe all
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from backtest_platform.research.momentum_harness import price_panel
from backtest_platform.strategies.momentum.strategy import MomentumConfig, backtest_momentum
from backtest_platform.validation.metrics import sharpe as ann_sharpe
from backtest_platform.validation.pbo import probability_of_backtest_overfitting
from backtest_platform.validation.trials import trials_deflated_criterion
from backtest_platform.validation.wfa import walk_forward_splits

SPAN = (date(2015, 1, 1), date(2025, 1, 1))  # end exclusive for WFA
LOOKBACKS, SKIPS, TOP_FRACS = (126, 189, 252, 315, 378), (0, 21), (0.2, 0.33, 0.5)
_MEGA = {"2330", "2317", "2454", "2412", "2882", "2891", "2308", "1303", "1101", "3008"}


def _grid(vol_target: float | None = None) -> list[MomentumConfig]:
    return [
        MomentumConfig(lookback_days=lb, skip_days=sk, top_fraction=tf, vol_target_annual=vol_target)
        for lb in LOOKBACKS for sk in SKIPS for tf in TOP_FRACS
    ]


def _universe(name: str) -> list[str]:
    avail = sorted(p.name.replace("daily_bars__", "").replace(".parquet", "")
                   for p in Path("data/parquet").glob("daily_bars__*.parquet"))
    if name == "large":
        return [s for s in avail if s in _MEGA]
    if name == "smid":
        return [s for s in avail if s not in _MEGA and s != "0050"]
    return [s for s in avail if s != "0050"]


def _returns_frame(prices, configs) -> pd.DataFrame:
    cols = {}
    for i, cfg in enumerate(configs):
        res = backtest_momentum(prices, cfg, SPAN[0], SPAN[1])
        if len(res.daily_returns):
            cols[f"c{i}"] = res.daily_returns
    return pd.DataFrame(cols).fillna(0.0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", default="all", choices=["large", "smid", "all"])
    ap.add_argument("--vol-target", type=float, default=None,
                    help="年化目標波動 (crash control)；e.g. 0.15。省略=vanilla")
    a = ap.parse_args()

    uni = _universe(a.universe)
    prices = price_panel(uni)
    configs = _grid(a.vol_target)
    if a.vol_target:
        print(f"[crash control] vol-target = {a.vol_target:.0%} annual\n")
    df = _returns_frame(prices, configs)
    matrix = df.to_numpy()
    sharpes = np.array([ann_sharpe(df[c]) for c in df.columns])
    print(f"universe={a.universe}({len(uni)})  grid={len(configs)} configs  "
          f"returns matrix={matrix.shape}  span={SPAN[0]}..{SPAN[1]}")
    print(f"per-config full-span Sharpe: min={sharpes.min():.3f} median={np.median(sharpes):.3f} "
          f"max={sharpes.max():.3f}\n")

    # --- PBO (CSCV) ---
    pbo = probability_of_backtest_overfitting(matrix, n_splits=16)
    print(f"PBO (CSCV, 16 splits): {pbo:.1%}   [bar: <30% pass]  → "
          f"{'❌ OVERFIT' if pbo > 0.30 else '✅ ok'}")

    # --- DSR (deflate best Sharpe by #trials) ---
    best_i = int(sharpes.argmax())
    best = df[df.columns[best_i]]
    cfg = configs[best_i]
    dres = trials_deflated_criterion(
        sr=float(sharpes[best_i]), n_trials=len(sharpes), n_obs=int(len(best)),
        skew=float(stats.skew(best)), kurtosis=float(stats.kurtosis(best, fisher=False)),
        sharpe_variance=float(np.var(sharpes, ddof=1)),
    )
    print(f"DSR: best Sharpe={sharpes[best_i]:.3f} (lb={cfg.lookback_days} skip={cfg.skip_days} "
          f"top={cfg.top_fraction:.2f}), n_trials={len(sharpes)} → DSR={dres.dsr_value:.3f}  "
          f"[bar: >0.95]  → {'✅ pass' if dres.passed else '❌ FAIL'}")

    # --- WFA (purge+embargo, select-IS / score-OOS) ---
    folds = walk_forward_splits(SPAN[0], SPAN[1], is_days=504, oos_days=252,
                                purge_days=5, embargo_days=5)
    print(f"\nWFA: {len(folds)} folds (IS 504d / OOS 252d, purge+embargo 5d)")
    is_sh, oos_sh = [], []
    for f in folds:
        is_block = df.loc[str(f.is_start):str(f.is_end)]
        oos_block = df.loc[str(f.oos_start):str(f.oos_end)]
        if len(is_block) < 60 or len(oos_block) < 30:
            continue
        sel = int(np.array([ann_sharpe(is_block[c]) for c in df.columns]).argmax())
        s_is = ann_sharpe(is_block[df.columns[sel]])
        s_oos = ann_sharpe(oos_block[df.columns[sel]])
        is_sh.append(s_is); oos_sh.append(s_oos)
        print(f"  {f.is_start}→{f.is_end} IS-best Sharpe={s_is:.3f}  |  "
              f"{f.oos_start}→{f.oos_end} OOS Sharpe={s_oos:.3f}")
    if oos_sh:
        m_is, m_oos = float(np.mean(is_sh)), float(np.mean(oos_sh))
        print(f"  mean IS Sharpe={m_is:.3f}  mean OOS Sharpe={m_oos:.3f}  "
              f"OOS/IS={m_oos / m_is if m_is else float('nan'):.2f}")

    print("\n=== VERDICT (rigorous, quantified) ===")
    pbo_fail = pbo > 0.30
    dsr_fail = not dres.passed
    oos_fail = bool(oos_sh) and float(np.mean(oos_sh)) < 1.0
    print(f"  PBO {'❌' if pbo_fail else '✅'} ({pbo:.0%})  |  "
          f"DSR {'❌' if dsr_fail else '✅'} ({dres.dsr_value:.2f})  |  "
          f"WFA OOS Sharpe>1 {'❌' if oos_fail else '✅'}"
          + (f" (mean {np.mean(oos_sh):.2f})" if oos_sh else ""))
    if pbo_fail or dsr_fail or oos_fail:
        print("  → 🔴 動能天真實作未過防過擬合 gate（與對抗式驗證一致，現在被量化）。")
    else:
        print("  → 🟢 動能撐過 PBO+DSR+WFA——意外，需 point-in-time universe 複核。")


if __name__ == "__main__":
    main()
