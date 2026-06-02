"""IS harness — `run_is(RunConfig) → metrics`, the productized form of the
one-off scripts/v3_double_window_is.py read.

Reuses the same offline close-to-close portfolio sim. `run_is` takes an injectable
`loader` so logic is unit-testable without the parquet cache (the default loader
reads data/parquet). `run_and_judge` wires it to the gate_state審判庭 so a run
yields an objective PASS/FAIL/INCOMPLETE in one call — turning '手寫 script 半天'
into 'run_is(cfg) → gate 逐條綠紅'.

NOTE: the sim is a lightweight close-to-close approximation (not zipline). The
v3 verdict was calibrated against the real engine (gate review §6); use the
relative read + health checks, not absolute CAGR.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import numpy as np
import pandas as pd

from backtest_platform.config.strategy_config import StrategyConfig, get_preset
from backtest_platform.research.run_config import RunConfig
from backtest_platform.strategies.four_layer_resonance.scoring import compute_scores
from backtest_platform.strategies.four_layer_resonance.signals import compute_signals
from backtest_platform.validation.gate_state import GateResult, evaluate_gate

PARQUET_DIR = "data/parquet"
_FLOW_COLS = [
    "foreign_buy", "trust_buy", "dealer_buy", "top_broker_buy", "key_broker_buy",
    "gov_broker_buy", "geo_broker_buy", "day_trade_volume", "margin_offset_volume",
]
TRADING_DAYS = 252
_SLIP_STRESS = 0.003  # 0.3% slippage for the K3 robustness Sharpe


def load_merged_parquet(sid: str, parquet_dir: str = PARQUET_DIR) -> pd.DataFrame:
    """Default loader: read + merge the 3 parquet for one stock (ETLBundle.merged)."""
    db = pd.read_parquet(f"{parquet_dir}/daily_bars__{sid}.parquet")
    inst = pd.read_parquet(f"{parquet_dir}/institutional__{sid}.parquet")
    chips = pd.read_parquet(f"{parquet_dir}/broker_chips__{sid}.parquet")
    m = db.merge(inst, on=["stock_id", "trade_date"], how="left").merge(
        chips, on=["stock_id", "trade_date"], how="left"
    )
    for c in _FLOW_COLS:
        if c in m.columns:
            m[c] = m[c].fillna(0).astype("int64")
    return m


def _signaled_window(merged: pd.DataFrame, cfg: StrategyConfig, start, end) -> pd.DataFrame:
    m = merged.copy()
    m["trade_date"] = pd.to_datetime(m["trade_date"])
    m = m.sort_values("trade_date").reset_index(drop=True)
    hist = m[m["trade_date"] <= pd.Timestamp(end)].reset_index(drop=True)
    sig = compute_signals(compute_scores(hist, cfg), cfg)
    win = sig[(sig["trade_date"] >= pd.Timestamp(start)) & (sig["trade_date"] <= pd.Timestamp(end))]
    return win.reset_index(drop=True)


def _daily_returns(sig: pd.DataFrame, cfg: StrategyConfig) -> pd.Series:
    ret = sig["close"].astype(float).pct_change().fillna(0.0)
    pos_prev = sig["in_position"].shift(1).fillna(0).astype(float)
    strat = pos_prev * ret
    is_buy = (sig["action"] == "buy").astype(float)
    is_exit = sig["action"].isin(["stoploss", "exit"]).astype(float)
    strat = strat - is_buy * cfg.cost_buy_rate - is_exit * cfg.cost_sell_rate
    return strat.reset_index(drop=True)


def _trades(sig: pd.DataFrame, cfg: StrategyConfig) -> list[dict]:
    out: list[dict] = []
    entry_i = None
    s = sig.reset_index(drop=True)
    for i, row in s.iterrows():
        if entry_i is None and row["action"] == "buy":
            entry_i = i
        elif entry_i is not None and row["action"] in ("stoploss", "exit"):
            e, x = s.iloc[entry_i], s.iloc[i]
            entry_px = float(e["close"]) * (1 + cfg.cost_buy_rate)
            exit_px = float(x["close"]) * (1 - cfg.cost_sell_rate)
            out.append({"ret": exit_px / entry_px - 1.0, "hold": i - entry_i,
                        "entry_structure": int(e["structure_score"])})
            entry_i = None
    return out


def _sharpe(strat: pd.Series) -> float:
    sd = float(strat.std())
    return float(strat.mean() / sd * np.sqrt(TRADING_DAYS)) if sd > 0 else 0.0


def _metrics(strat: pd.Series, strat_slip: pd.Series, trades: list[dict], n_buys: int) -> dict:
    n = len(strat)
    eq = (1 + strat).cumprod()
    cagr = float(eq.iloc[-1] ** (TRADING_DAYS / n) - 1) if n else 0.0
    dd = float((eq / eq.cummax() - 1).min()) if n else 0.0
    rets = [t["ret"] for t in trades]
    wins = [r for r in rets if r > 0]
    losses = [r for r in rets if r <= 0]
    return {
        "trades": n_buys,
        "closed": len(trades),
        "cagr": cagr,
        "sharpe": _sharpe(strat),
        "slippage_sharpe": _sharpe(strat_slip),
        "maxdd": dd,
        "win": (len(wins) / len(rets)) if rets else 0.0,
        "avg_hold": float(np.mean([t["hold"] for t in trades])) if trades else 0.0,
        "struct1_pct": (sum(t["entry_structure"] == 1 for t in trades) / len(trades)) if trades else 0.0,
        "churn_pct": (sum(t["hold"] < 3 for t in trades) / len(trades)) if trades else 0.0,
    }


def run_is(
    cfg: RunConfig,
    loader: Callable[[str], pd.DataFrame] = load_merged_parquet,
) -> dict:
    """Run the IS portfolio sim for a RunConfig. Returns a metrics dict."""
    base = get_preset(cfg.preset)
    slip = base.model_copy(update={"slip_rate": _SLIP_STRESS})
    norm_returns, slip_returns, all_trades, n_buys = [], [], [], 0
    for sid in cfg.stocks:
        sig = _signaled_window(loader(sid), base, cfg.is_start, cfg.is_end)
        if len(sig) < 30:
            continue
        norm_returns.append(_daily_returns(sig, base))
        slip_returns.append(_daily_returns(sig, slip))
        all_trades.extend(_trades(sig, base))
        n_buys += int((sig["action"] == "buy").sum())
    if not norm_returns:
        return {"trades": 0, "closed": 0, "bars": 0}
    port = pd.concat(norm_returns, axis=1).mean(axis=1)
    port_slip = pd.concat(slip_returns, axis=1).mean(axis=1)
    out = _metrics(port, port_slip, all_trades, n_buys)
    out["bars"] = len(port)
    return out


def run_and_judge(
    cfg: RunConfig,
    loader: Callable[[str], pd.DataFrame] = load_merged_parquet,
    gate=None,
) -> dict:
    """run_is → evaluate_gate → a complete, ledger-ready run record."""
    metrics = run_is(cfg, loader)
    result: GateResult = evaluate_gate(metrics) if gate is None else evaluate_gate(metrics, gate)
    return {
        "run_id": cfg.run_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "hypothesis": cfg.hypothesis,
        "preset": cfg.preset,
        "engine": cfg.engine,
        "stocks": list(cfg.stocks),
        "window": [cfg.is_start.isoformat(), cfg.is_end.isoformat()],
        "metrics": metrics,
        "gate_status": result.status.value,
        "gate_summary": result.summary(),
    }
