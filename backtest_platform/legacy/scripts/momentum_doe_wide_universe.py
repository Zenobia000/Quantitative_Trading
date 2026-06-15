"""Phase 2 ② — momentum DOE on a wider liquid universe (breadth lever).

#82/#83 showed momentum + abs-momentum on 10 large-caps reaches Sharpe 0.97 — a
hair under the 1.0 bar. Cross-sectional momentum needs *breadth*; this widens to
~40 liquid TWSE names and re-runs the same DOE through the unified
``full_validation_report`` harness.

⚠️ SURVIVORSHIP CAVEAT: this fetches *living* symbols only (no delisted) → an
optimistic ceiling. The rigorous survivorship-clean momentum (209 names incl
delisted) is the prior R9 finding (momentum_survivorship_clean_result). If the
wider universe clears Sharpe 1.0 here, it MUST be re-verified survivorship-clean
before any GO.

Close prices are fetched in-memory via FinMind free tier (no token). Run:
    uv run python scripts/momentum_doe_wide_universe.py
"""
from __future__ import annotations

import itertools
from datetime import date

import numpy as np
import pandas as pd

from backtest_platform.data.finmind_etl import _build_loader
from backtest_platform.research.runs_store import append_run
from backtest_platform.strategies.momentum.strategy import MomentumConfig, backtest_momentum
from backtest_platform.validation.full_report import full_validation_report

# ~40 liquid TWSE names (survivors — see survivorship caveat above).
WIDE_UNIVERSE = [
    "2330", "2317", "2454", "2308", "2382", "2412", "2303", "2881", "2882", "2891",
    "2886", "2884", "1303", "1301", "1326", "2002", "2207", "3008", "3711", "2357",
    "2379", "2409", "2474", "4938", "2603", "2609", "2615", "1216", "1101", "2912",
    "2880", "2885", "2887", "2890", "9910", "2105", "1402", "2618", "2353", "3045",
]
FETCH_START, IS_START, IS_END = "2014-01-01", date(2016, 1, 1), date(2020, 12, 31)

GRID = {
    "rebalance": ["monthly", "quarterly"],
    "vol_target_annual": [None, 0.15],
    "lookback_days": [126, 252],
    "abs_momentum": [False, True],
}


def _fetch_panel() -> pd.DataFrame:
    dl = _build_loader(None)  # free tier
    cols: dict[str, pd.Series] = {}
    for sid in WIDE_UNIVERSE:
        try:
            df = dl.taiwan_stock_daily(stock_id=sid, start_date=FETCH_START, end_date="2024-12-31")
            if df is None or df.empty:
                continue
            s = df[["date", "close"]].copy()
            s["date"] = pd.to_datetime(s["date"])
            cols[sid] = s.set_index("date")["close"].astype(float).sort_index()
        except Exception as exc:  # noqa: BLE001 — one bad symbol must not sink the panel
            print(f"  skip {sid}: {type(exc).__name__}")
    return pd.DataFrame(cols)


def _configs() -> list[MomentumConfig]:
    keys = list(GRID)
    return [MomentumConfig(**dict(zip(keys, c))) for c in itertools.product(*(GRID[k] for k in keys))]


def main() -> None:
    panel = _fetch_panel()
    print(f"panel: {panel.shape[1]} symbols × {panel.shape[0]} bars "
          f"[{panel.index.min().date()}..{panel.index.max().date()}]")

    configs = _configs()
    n_trials = len(configs)
    runs = []
    for cfg in configs:
        res = backtest_momentum(panel, cfg, start=IS_START, end=IS_END)
        if len(res.daily_returns) >= 50:
            r = np.asarray(res.daily_returns, float)
            pp = float(r.mean() / r.std()) if r.std() > 0 else 0.0
            runs.append((cfg, res.daily_returns, pp))
    sharpe_var = float(np.var([pp for _, _, pp in runs], ddof=0)) if len(runs) > 1 else 0.0

    rows = []
    for cfg, returns, _pp in runs:
        rep = full_validation_report(returns, n_trials=n_trials, sharpe_variance=sharpe_var, n_iter=1000, seed=0)
        m, rob = rep["metrics"], rep["robustness"]
        rows.append({
            "reb": cfg.rebalance, "vt": cfg.vol_target_annual, "lb": cfg.lookback_days,
            "abs": cfg.abs_momentum, "cagr": m["cagr"], "sharpe": m["sharpe"],
            "maxdd": m["max_drawdown"], "dsr": rob["deflated_sharpe"], "deploy": rep["deployable"],
        })

    rows.sort(key=lambda r: r["sharpe"], reverse=True)
    print(f"\n=== DOE momentum WIDE universe ({panel.shape[1]} names, {n_trials} configs) ===")
    print(f"{'reb':<10}{'vt':<6}{'lb':<5}{'abs':<6}{'CAGR':>8}{'Sharpe':>8}{'MaxDD':>8}{'DSR':>7}{'deploy':>8}")
    for r in rows[:10]:
        print(f"{r['reb']:<10}{str(r['vt']):<6}{r['lb']:<5}{str(r['abs']):<6}"
              f"{r['cagr']*100:>7.1f}%{r['sharpe']:>8.2f}{r['maxdd']*100:>7.1f}%{r['dsr']:>7.2f}{str(r['deploy']):>8}")

    best = rows[0]
    verdict = "GO (re-verify survivorship-clean!)" if best["deploy"] else "NO-GO"
    print(f"\nBest: {best['reb']}/vt={best['vt']}/lb={best['lb']}/abs={best['abs']} "
          f"→ CAGR {best['cagr']*100:.1f}% Sharpe {best['sharpe']:.2f} DSR {best['dsr']:.2f} → {verdict}")
    append_run({
        "run_id": f"momentum-wide-{panel.shape[1]}n-{best['reb']}-abs{best['abs']}",
        "preset": "momentum", "hypothesis": f"wide {panel.shape[1]}-name survivor universe DOE (Phase 2②)",
        "gate_status": "PASS" if best["deploy"] else "FAIL",
        "metrics": {k: best[k] for k in ("cagr", "sharpe", "maxdd", "dsr")},
        "is_start": IS_START.isoformat(), "is_end": IS_END.isoformat(),
        "window": [IS_START.isoformat(), IS_END.isoformat()], "n_trials": n_trials,
    })


if __name__ == "__main__":
    main()
