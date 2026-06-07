"""DOE first-read of the institutional-flow factor (new edge family) on real data.

Loads close / volume / 三大法人 net-buy panels from the ingested parquet
(DEFAULT_UNIVERSE) and runs an InstFlowConfig sweep through the unified
``full_validation_report``. First honest read of whether following institutional
flow is a real edge in this market — judged on the SAME plumbing momentum was.

Run:  uv run python scripts/inst_flow_doe.py
"""
from __future__ import annotations

import itertools
from datetime import date

import numpy as np
import pandas as pd

from backtest_platform.engines.zipline_adapter.bundles.finmind_bundle import DEFAULT_UNIVERSE
from backtest_platform.research.is_harness import load_merged_parquet
from backtest_platform.research.runs_store import append_run
from backtest_platform.strategies.inst_flow.strategy import InstFlowConfig, backtest_inst_flow
from backtest_platform.validation.full_report import full_validation_report

IS_START, IS_END = date(2016, 1, 1), date(2020, 12, 31)
GRID = {
    "rebalance": ["monthly", "quarterly"],
    "lookback_days": [20, 60],
    "flow_source": ["foreign", "foreign_trust"],
    "vol_target_annual": [None, 0.15],
}


def _load() -> tuple[pd.DataFrame, dict[str, pd.DataFrame], pd.DataFrame]:
    """close + per-source flow + volume wide panels from the parquet cache."""
    close, vol = {}, {}
    raw: dict[str, pd.DataFrame] = {}
    for sid in DEFAULT_UNIVERSE:
        try:
            df = load_merged_parquet(sid)
        except Exception:  # noqa: BLE001
            continue
        df = df.assign(trade_date=pd.to_datetime(df["trade_date"])).set_index("trade_date").sort_index()
        close[sid], vol[sid], raw[sid] = df["close"].astype(float), df["volume"].astype(float), df
    close_p, vol_p = pd.DataFrame(close), pd.DataFrame(vol)
    return close_p, raw, vol_p


def _flow_panel(raw: dict[str, pd.DataFrame], cols: tuple[str, ...]) -> pd.DataFrame:
    return pd.DataFrame({sid: df[list(cols)].sum(axis=1).astype(float) for sid, df in raw.items()})


def main() -> None:
    close, raw, vol = _load()
    print(f"panel: {close.shape[1]} symbols × {close.shape[0]} bars "
          f"[{close.index.min().date()}..{close.index.max().date()}]")

    keys = list(GRID)
    configs = [InstFlowConfig(**dict(zip(keys, c))) for c in itertools.product(*(GRID[k] for k in keys))]
    n_trials = len(configs)

    runs = []
    for cfg in configs:
        flow = _flow_panel(raw, cfg.flow_cols)
        res = backtest_inst_flow(close, flow, vol, cfg, IS_START, IS_END)
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
            "reb": cfg.rebalance, "lb": cfg.lookback_days, "src": cfg.flow_source,
            "vt": cfg.vol_target_annual, "cagr": m["cagr"], "sharpe": m["sharpe"],
            "maxdd": m["max_drawdown"], "dsr": rob["deflated_sharpe"], "deploy": rep["deployable"],
        })
    rows.sort(key=lambda r: r["sharpe"], reverse=True)

    print(f"\n=== DOE institutional-flow factor ({n_trials} configs, honest DSR) ===")
    print(f"{'reb':<10}{'lb':<5}{'src':<14}{'vt':<6}{'CAGR':>8}{'Sharpe':>8}{'MaxDD':>8}{'DSR':>7}{'deploy':>8}")
    for r in rows:
        print(f"{r['reb']:<10}{r['lb']:<5}{r['src']:<14}{str(r['vt']):<6}"
              f"{r['cagr']*100:>7.1f}%{r['sharpe']:>8.2f}{r['maxdd']*100:>7.1f}%{r['dsr']:>7.2f}{str(r['deploy']):>8}")

    best = rows[0]
    print(f"\nBest by Sharpe: {best['reb']}/lb={best['lb']}/{best['src']}/vt={best['vt']} "
          f"→ CAGR {best['cagr']*100:.1f}% Sharpe {best['sharpe']:.2f} DSR {best['dsr']:.2f} "
          f"→ {'GO (widen+OOS+survivorship!)' if best['deploy'] else 'NO-GO'}")
    append_run({
        "run_id": f"instflow-{best['reb']}-lb{best['lb']}-{best['src']}",
        "preset": "inst_flow", "hypothesis": "institutional-flow factor DOE on DEFAULT_UNIVERSE 2016-2020",
        "gate_status": "PASS" if best["deploy"] else "FAIL",
        "metrics": {k: best[k] for k in ("cagr", "sharpe", "maxdd", "dsr")},
        "is_start": IS_START.isoformat(), "is_end": IS_END.isoformat(),
        "window": [IS_START.isoformat(), IS_END.isoformat()], "n_trials": n_trials,
    })


if __name__ == "__main__":
    main()
