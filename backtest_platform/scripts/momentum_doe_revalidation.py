"""DOE re-validation of momentum through the unified full_validation_report harness.

"跑通" Phase 1 收尾: run a real momentum config sweep over the ingested
DEFAULT_UNIVERSE (10 large-caps, 2015-2024) and push each config's returns through
``validation.full_report`` — the same end-to-end审判庭 (metrics + §4.3.1 health +
bootstrap/MC + Deflated Sharpe). This exercises the platform's validation pipeline
on real data and records the run to the ledger.

The DSR deflation counts the FULL sweep (n_trials = number of configs) so the
"best" config is judged honestly against selection bias — not cherry-picked.

Run:  uv run python scripts/momentum_doe_revalidation.py
"""
from __future__ import annotations

import itertools
import json
from datetime import date

import numpy as np

from backtest_platform.research.momentum_harness import price_panel
from backtest_platform.research.runs_store import append_run
from backtest_platform.strategies.momentum.strategy import MomentumConfig, backtest_momentum
from backtest_platform.engines.zipline_adapter.bundles.finmind_bundle import DEFAULT_UNIVERSE
from backtest_platform.validation.full_report import full_validation_report

IS_START, IS_END = date(2016, 1, 1), date(2020, 12, 31)

# DOE grid — rebalance freq × crash-control × lookback (8 configs = 8 trials).
GRID = {
    "rebalance": ["monthly", "quarterly"],
    "vol_target_annual": [None, 0.15],
    "lookback_days": [126, 252],
}


def _configs() -> list[MomentumConfig]:
    keys = list(GRID)
    return [
        MomentumConfig(**dict(zip(keys, combo)))
        for combo in itertools.product(*(GRID[k] for k in keys))
    ]


def main() -> None:
    panel = price_panel(list(DEFAULT_UNIVERSE))
    print(f"panel: {panel.shape[1]} symbols × {panel.shape[0]} bars "
          f"[{panel.index.min().date()}..{panel.index.max().date()}]")

    configs = _configs()
    n_trials = len(configs)

    # Pass 1 — backtest every config; collect returns + per-period Sharpe so the
    # DSR deflation benchmark uses the REAL cross-trial Sharpe variance (per-period).
    runs = []
    for cfg in configs:
        res = backtest_momentum(panel, cfg, start=IS_START, end=IS_END)
        if len(res.daily_returns) >= 50:
            r = np.asarray(res.daily_returns, float)
            pp_sharpe = float(r.mean() / r.std()) if r.std() > 0 else 0.0
            runs.append((cfg, res.daily_returns, pp_sharpe))
    sharpe_var = float(np.var([pp for _, _, pp in runs], ddof=0)) if len(runs) > 1 else 0.0

    # Pass 2 — full validation report per config with the honest cross-trial variance.
    rows = []
    for cfg, returns, _pp in runs:
        rep = full_validation_report(
            returns, n_trials=n_trials, sharpe_variance=sharpe_var, n_iter=1000, seed=0
        )
        m, rob = rep["metrics"], rep["robustness"]
        rows.append({
            "rebalance": cfg.rebalance, "vol_target": cfg.vol_target_annual,
            "lookback": cfg.lookback_days,
            "cagr": m["cagr"], "sharpe": m["sharpe"], "maxdd": m["max_drawdown"],
            "dsr": rob["deflated_sharpe"], "mc_p": rob["mc_edge_pvalue"],
            "greens": rep["health"]["counts"]["green"], "deployable": rep["deployable"],
        })

    rows.sort(key=lambda r: r["sharpe"], reverse=True)
    print(f"\n=== DOE momentum re-validation ({n_trials} configs, honest DSR) ===")
    print(f"{'reb':<10}{'vt':<6}{'lb':<5}{'CAGR':>8}{'Sharpe':>8}{'MaxDD':>8}{'DSR':>7}{'green':>7}{'deploy':>8}")
    for r in rows:
        print(f"{r['rebalance']:<10}{str(r['vol_target']):<6}{r['lookback']:<5}"
              f"{r['cagr']*100:>7.1f}%{r['sharpe']:>8.2f}{r['maxdd']*100:>7.1f}%"
              f"{r['dsr']:>7.2f}{r['greens']:>7}{str(r['deployable']):>8}")

    best = rows[0]
    verdict = "GO" if best["deployable"] else "NO-GO"
    print(f"\nBest by Sharpe: {best['rebalance']}/vt={best['vol_target']}/lb={best['lookback']} "
          f"→ Sharpe {best['sharpe']:.2f}, DSR {best['dsr']:.2f} → {verdict}")

    # record the best config to the runs ledger (lineage)
    append_run({
        "run_id": f"momentum-doe-{best['rebalance']}-vt{best['vol_target']}-lb{best['lookback']}",
        "preset": "momentum",
        "hypothesis": "DOE sweep over DEFAULT_UNIVERSE 2016-2020 via full_validation_report",
        "gate_status": "PASS" if best["deployable"] else "FAIL",
        "metrics": {k: best[k] for k in ("cagr", "sharpe", "maxdd", "dsr")},
        "is_start": IS_START.isoformat(), "is_end": IS_END.isoformat(),
        "window": [IS_START.isoformat(), IS_END.isoformat()],
        "n_trials": n_trials,
    })
    print(f"\nrecorded best to runs ledger; full DOE table ({len(rows)} rows):")
    print(json.dumps(rows, indent=0, default=str))


if __name__ == "__main__":
    main()
