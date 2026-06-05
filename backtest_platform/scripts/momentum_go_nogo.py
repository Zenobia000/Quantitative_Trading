"""Momentum FINAL go/no-go — fixed config + realistic cost + survivorship-clean universe.

The deployment decision, stripped of every researcher degree of freedom:
- **Fixed config** (lb=252/skip=21/top=0.33) — committed up front, NO per-fold
  selection (so the PBO selection-overfit can't inflate the OOS read).
- **Realistic cost** (~1.2% round-trip small-cap, spread/amortized) vs the 0.67% base.
- **Survivorship-clean universe** (survivors + delisted losers).

GO iff: full-period CAGR ≥ 18% (K1) AND the committed config's mean WFA OOS Sharpe
≥ 1.0 AND the 30-config landscape PBO < 30%. Uses cached parquet only.

Run: uv run python scripts/momentum_go_nogo.py
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from backtest_platform.research.momentum_harness import price_panel
from backtest_platform.strategies.momentum.strategy import MomentumConfig, backtest_momentum
from backtest_platform.validation.metrics import cagr as ann_cagr
from backtest_platform.validation.metrics import max_drawdown
from backtest_platform.validation.metrics import sharpe as ann_sharpe
from backtest_platform.validation.pbo import probability_of_backtest_overfitting
from backtest_platform.validation.wfa import walk_forward_splits

SPAN = (date(2015, 1, 1), date(2025, 1, 1))
FIXED = dict(lookback_days=252, skip_days=21, top_fraction=1 / 3)  # committed config
REALISTIC_COST = 0.012  # ~1.2% round-trip small-cap (vs 0.67% base)
LOOKBACKS, SKIPS, TOP_FRACS = (126, 189, 252, 315, 378), (0, 21), (0.2, 0.33, 0.5)


def _universe() -> list[str]:
    return sorted(
        p.name.replace("daily_bars__", "").replace(".parquet", "")
        for p in Path("data/parquet").glob("daily_bars__*.parquet")
        if "0050" not in p.name
    )


def main() -> None:
    uni = _universe()
    prices = price_panel(uni)
    print(f"universe={len(uni)} (survivorship-aware: survivors + delisted)")
    print(f"FIXED config lb=252 skip=21 top=0.33 | cost={REALISTIC_COST:.1%} round-trip (spread) | "
          f"span {SPAN[0]}..{SPAN[1]}\n")

    cfg = MomentumConfig(**FIXED, cost_round_rate=REALISTIC_COST, cost_mode="spread")
    res = backtest_momentum(prices, cfg, SPAN[0], SPAN[1])
    d = res.daily_returns
    slip = backtest_momentum(prices, cfg.with_extra_slippage(0.003), SPAN[0], SPAN[1]).daily_returns
    full_cagr, full_sh = ann_cagr(d), ann_sharpe(d)
    print("FULL-SPAN (committed config, realistic cost):")
    print(f"  CAGR={full_cagr:.4f}  Sharpe={full_sh:.3f}  slipSharpe={ann_sharpe(slip):.3f}  "
          f"maxDD={max_drawdown(d):.3f}  holdings={res.avg_holdings:.0f}")

    folds = walk_forward_splits(SPAN[0], SPAN[1], is_days=504, oos_days=252, purge_days=5, embargo_days=5)
    oos: list[float] = []
    print(f"\nWFA OOS (committed config, {len(folds)} folds, NO re-selection):")
    for f in folds:
        ob = d.loc[str(f.oos_start):str(f.oos_end)]
        if len(ob) < 30:
            continue
        s = ann_sharpe(ob)
        oos.append(s)
        print(f"  {f.oos_start}→{f.oos_end} OOS Sharpe={s:.3f}")
    mean_oos = float(np.mean(oos)) if oos else float("nan")
    print(f"  mean OOS Sharpe={mean_oos:.3f}  ({sum(s > 1.0 for s in oos)}/{len(oos)} folds > 1.0)")

    configs = [MomentumConfig(lookback_days=lb, skip_days=sk, top_fraction=tf,
                              cost_round_rate=REALISTIC_COST, cost_mode="spread")
               for lb in LOOKBACKS for sk in SKIPS for tf in TOP_FRACS]
    mat = pd.DataFrame(
        {f"c{i}": backtest_momentum(prices, c, SPAN[0], SPAN[1]).daily_returns
         for i, c in enumerate(configs)}
    ).fillna(0.0).to_numpy()
    pbo = probability_of_backtest_overfitting(mat, n_splits=16)
    print(f"\nPBO (30-config landscape, realistic cost): {pbo:.1%}")

    go_cagr, go_oos, go_pbo = full_cagr >= 0.18, mean_oos >= 1.0, pbo < 0.30
    print("\n=== 🚦 GO / NO-GO（survivorship-clean + 實際成本 + 固定 config）===")
    print(f"  K1 CAGR ≥ 18%:        {'✅' if go_cagr else '❌'}  ({full_cagr:.1%})")
    print(f"  WFA OOS Sharpe ≥ 1.0: {'✅' if go_oos else '❌'}  ({mean_oos:.2f})")
    print(f"  PBO < 30%:            {'✅' if go_pbo else '❌'}  ({pbo:.0%})")
    if go_cagr and go_oos and go_pbo:
        print("  → 🟢 GO：固定 config 在 survivorship-clean universe + 實際成本下三條全過 → 可進 paper trading（7.A/7.C/7.D 已備）。")
    else:
        fails = [n for n, ok in [("CAGR", go_cagr), ("OOS Sharpe", go_oos), ("PBO", go_pbo)] if not ok]
        print(f"  → 🔴 NO-GO / conditional：未過 = {', '.join(fails)}。momentum 仍最強候選，但這些是上線前的硬 blocker。")


if __name__ == "__main__":
    main()
