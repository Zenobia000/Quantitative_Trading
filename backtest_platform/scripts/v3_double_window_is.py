"""v3 entry double-window IS read — Sprint 6 (ADR-019 §11 honest exit gate).

OFFLINE: reads data/parquet/{daily_bars,institutional,broker_chips}__<id>.parquet
(replicates ETLBundle.merged). Runs three FIXED configs only:
  - v2      : StrategyConfig()           (baseline; must reproduce ~stale behavior)
  - v3      : DEFAULT_CONFIG_V3          (relaxed entry + flameout 2-bar confirm)
  - v3_f1   : v3 with exit_flameout_confirm_bars=1  (control: isolates exit pairing)

STRICT NO-SWEEP (ADR-019 §2.4): only these three configs, no parameter grid.
Entry count is a sample-health floor (30-80/股/5y), NOT an edge signal.
In-sample green != edge — this is a "worth advancing to OOS?" read, nothing more.

Run: cd backtest_platform && uv run python scripts/v3_double_window_is.py
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from backtest_platform.config.strategy_config import DEFAULT_CONFIG_V3, StrategyConfig
from backtest_platform.strategies.four_layer_resonance.scoring import compute_scores
from backtest_platform.strategies.four_layer_resonance.signals import compute_signals

PARQUET = os.path.join(os.path.dirname(__file__), "..", "data", "parquet")
FLOW_COLS = [
    "foreign_buy", "trust_buy", "dealer_buy", "top_broker_buy", "key_broker_buy",
    "gov_broker_buy", "geo_broker_buy", "day_trade_volume", "margin_offset_volume",
]
# 2330 + mid-cap constituents (exclude 2454/2882 large-cap per v0.1 focus).
STOCKS = ["2330", "1101", "1303", "2308", "2317", "2891", "3008", "2412"]
WINDOWS = {
    "2015-2020": ("2015-01-01", "2019-12-31"),
    "2020-2024": ("2020-01-01", "2024-12-31"),
}
TRADING_DAYS = 252

V2 = StrategyConfig()
V3 = DEFAULT_CONFIG_V3
V3_F1 = DEFAULT_CONFIG_V3.model_copy(update={"exit_flameout_confirm_bars": 1})
CONFIGS = {"v2": V2, "v3": V3, "v3_f1": V3_F1}


def load_merged(sid: str) -> pd.DataFrame:
    db = pd.read_parquet(f"{PARQUET}/daily_bars__{sid}.parquet")
    inst = pd.read_parquet(f"{PARQUET}/institutional__{sid}.parquet")
    chips = pd.read_parquet(f"{PARQUET}/broker_chips__{sid}.parquet")
    m = db.merge(inst, on=["stock_id", "trade_date"], how="left").merge(
        chips, on=["stock_id", "trade_date"], how="left"
    )
    for c in FLOW_COLS:
        if c in m.columns:
            m[c] = m[c].fillna(0).astype("int64")
    m["trade_date"] = pd.to_datetime(m["trade_date"])
    return m.sort_values("trade_date").reset_index(drop=True)


def signaled_window(merged: pd.DataFrame, cfg: StrategyConfig, start: str, end: str) -> pd.DataFrame:
    """Score+signal on history up to `end` (so warmup is valid at `start`), then
    slice to the [start, end] window for metric computation."""
    hist = merged[merged["trade_date"] <= pd.Timestamp(end)].reset_index(drop=True)
    sig = compute_signals(compute_scores(hist, cfg), cfg)
    win = sig[(sig["trade_date"] >= pd.Timestamp(start)) & (sig["trade_date"] <= pd.Timestamp(end))]
    return win.reset_index(drop=True)


def daily_strategy_returns(sig: pd.DataFrame, cfg: StrategyConfig) -> pd.Series:
    """Close-to-close long-only return with costs charged on entry/exit bars."""
    close = sig["close"].astype(float)
    ret = close.pct_change().fillna(0.0)
    pos_prev = sig["in_position"].shift(1).fillna(0).astype(float)
    strat = pos_prev * ret
    is_buy = (sig["action"] == "buy").astype(float)
    is_exit = sig["action"].isin(["stoploss", "exit"]).astype(float)
    strat = strat - is_buy * cfg.cost_buy_rate - is_exit * cfg.cost_sell_rate
    return strat.reset_index(drop=True)


def trades_from(sig: pd.DataFrame, cfg: StrategyConfig) -> list[dict]:
    """Reconstruct closed trades (entry buy -> exit) from the action sequence."""
    out: list[dict] = []
    entry_i = None
    for i, row in sig.reset_index(drop=True).iterrows():
        if entry_i is None and row["action"] == "buy":
            entry_i = i
        elif entry_i is not None and row["action"] in ("stoploss", "exit"):
            e = sig.iloc[entry_i]
            x = sig.iloc[i]
            entry_px = float(e["close"]) * (1 + cfg.cost_buy_rate)
            exit_px = float(x["close"]) * (1 - cfg.cost_sell_rate)
            out.append({
                "ret": exit_px / entry_px - 1.0,
                "hold": i - entry_i,
                "entry_structure": int(e["structure_score"]),
            })
            entry_i = None
    return out


def metrics(strat: pd.Series, trades: list[dict], n_buys: int) -> dict:
    n = len(strat)
    eq = (1 + strat).cumprod()
    total = float(eq.iloc[-1] - 1) if n else 0.0
    cagr = float(eq.iloc[-1] ** (TRADING_DAYS / n) - 1) if n else 0.0
    sd = float(strat.std())
    sharpe = float(strat.mean() / sd * np.sqrt(TRADING_DAYS)) if sd > 0 else 0.0
    dd = float((eq / eq.cummax() - 1).min()) if n else 0.0
    rets = [t["ret"] for t in trades]
    wins = [r for r in rets if r > 0]
    losses = [r for r in rets if r <= 0]
    win_rate = len(wins) / len(rets) if rets else 0.0
    pf = (sum(wins) / -sum(losses)) if losses and sum(losses) < 0 else float("inf") if wins else 0.0
    avg_hold = float(np.mean([t["hold"] for t in trades])) if trades else 0.0
    struct1 = (sum(1 for t in trades if t["entry_structure"] == 1) / len(trades)) if trades else 0.0
    churn = (sum(1 for t in trades if t["hold"] < 3) / len(trades)) if trades else 0.0
    return {
        "trades": n_buys, "closed": len(trades), "total_ret": total, "cagr": cagr,
        "sharpe": sharpe, "maxdd": dd, "win": win_rate, "pf": pf,
        "avg_hold": avg_hold, "struct1_pct": struct1, "churn_pct": churn,
    }


def run() -> None:
    rows = []
    # per-stock daily returns for portfolio aggregation: {(win,cfg): {sid: strat_series}}
    daily = {}
    for win, (start, end) in WINDOWS.items():
        for cname, cfg in CONFIGS.items():
            daily[(win, cname)] = {}
            for sid in STOCKS:
                try:
                    merged = load_merged(sid)
                except FileNotFoundError:
                    print(f"  SKIP {sid} ({win}): parquet missing")
                    continue
                sig = signaled_window(merged, cfg, start, end)
                if len(sig) < 30:
                    print(f"  SKIP {sid} ({win}/{cname}): only {len(sig)} bars")
                    continue
                strat = daily_strategy_returns(sig, cfg)
                trades = trades_from(sig, cfg)
                n_buys = int((sig["action"] == "buy").sum())
                m = metrics(strat, trades, n_buys)
                m.update({"window": win, "config": cname, "stock": sid})
                rows.append(m)
                daily[(win, cname)][sid] = strat.reset_index(drop=True)

    # equal-weight portfolio (average daily strat returns across stocks)
    for (win, cname), series_map in daily.items():
        if not series_map:
            continue
        mat = pd.concat(series_map.values(), axis=1)
        port = mat.mean(axis=1)  # equal weight, daily rebalanced
        # portfolio trade-level metrics not meaningful; use per-stock aggregates
        all_trades = []
        n_buys = 0
        for sid in series_map:
            sub = [r for r in rows if r["window"] == win and r["config"] == cname and r["stock"] == sid]
            if sub:
                n_buys += sub[0]["trades"]
        m = metrics(port, [], n_buys)
        m.update({"window": win, "config": cname, "stock": "PORTFOLIO"})
        # recompute trade-quality aggregates from per-stock rows
        ps = [r for r in rows if r["window"] == win and r["config"] == cname and r["stock"] != "PORTFOLIO"]
        if ps:
            closed = [r["closed"] for r in ps]
            m["closed"] = sum(closed)
            m["avg_hold"] = float(np.average([r["avg_hold"] for r in ps], weights=[c or 1 for c in closed]))
            m["win"] = float(np.average([r["win"] for r in ps], weights=[c or 1 for c in closed]))
            m["struct1_pct"] = float(np.average([r["struct1_pct"] for r in ps], weights=[c or 1 for c in closed]))
            m["churn_pct"] = float(np.average([r["churn_pct"] for r in ps], weights=[c or 1 for c in closed]))
        rows.append(m)

    df = pd.DataFrame(rows)
    # ---- print PORTFOLIO summary (primary read) ----
    print("\n" + "=" * 100)
    print("PORTFOLIO (equal-weight) — primary IS read   [STRICT NO-SWEEP; entry count = sample floor, NOT edge]")
    print("=" * 100)
    port = df[df["stock"] == "PORTFOLIO"].copy()
    fmt = port[["window", "config", "trades", "cagr", "sharpe", "maxdd", "win", "avg_hold", "struct1_pct", "churn_pct"]].copy()
    for c in ["cagr", "maxdd"]:
        fmt[c] = (fmt[c] * 100).round(2).astype(str) + "%"
    for c in ["win", "struct1_pct", "churn_pct"]:
        fmt[c] = (fmt[c] * 100).round(1).astype(str) + "%"
    fmt["sharpe"] = fmt["sharpe"].round(2)
    fmt["avg_hold"] = fmt["avg_hold"].round(1)
    print(fmt.to_string(index=False))

    # ---- per-stock v3 detail ----
    print("\n" + "=" * 100)
    print("PER-STOCK (config=v3)")
    print("=" * 100)
    v3d = df[(df["config"] == "v3") & (df["stock"] != "PORTFOLIO")].copy()
    pv = v3d.pivot_table(index="stock", columns="window", values=["trades", "cagr", "sharpe"], aggfunc="first")
    print(pv.round(3).to_string())

    df.to_csv(os.path.join(os.path.dirname(__file__), "..", "reports", "v3_double_window_is.csv"), index=False)
    print("\nfull matrix -> reports/v3_double_window_is.csv")


if __name__ == "__main__":
    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "reports"), exist_ok=True)
    run()
