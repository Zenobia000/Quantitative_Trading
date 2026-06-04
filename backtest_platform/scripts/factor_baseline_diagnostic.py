"""Control-factor diagnostic — localize WHERE the no-edge lives.

Four-layer resonance failed 3 ways. This runs *known-simple* baselines through the
SAME data + cost model + metrics, to separate three hypotheses:

  H1 "the universe/period just went down"  → even buy-and-hold is negative
  H2 "no factor edge is extractable here"  → 12-1 momentum ≈ buy-and-hold (no spread)
  H3 "four-layer specifically destroys value" → momentum/B&H positive, four-layer negative

Strategies (long-only, monthly rebalance for momentum), per window:
  - 0050 buy-hold        — the broad-market benchmark (did the market go up?)
  - EW buy-hold          — equal-weight the universe (did these names drift up?)
  - 12-1 momentum top⅓   — the canonical factor (can a simple edge be extracted?)

Reuses the platform's own cost model (StrategyConfig.cost_round_rate ~1.27%) and
metrics (validation.metrics), so the comparison to four-layer is apples-to-apples.

Run: `uv run python scripts/factor_baseline_diagnostic.py`  (uses cached parquet only)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from backtest_platform.config.strategy_config import StrategyConfig
from backtest_platform.research.is_harness import load_merged_parquet
from backtest_platform.validation.metrics import cagr, max_drawdown, sharpe

WINDOWS = [("2015-2020", "2015-01-01", "2020-12-31"),
           ("2020-2024", "2020-01-01", "2024-12-31")]
BENCHMARK = "0050"
_MEGA = {"2330", "2317", "2454", "2412", "2882", "2891", "2308", "1303", "1101", "3008"}
COST_ROUND = StrategyConfig().cost_round_rate  # ~one round-trip cost, per turnover
MOM_LOOKBACK, MOM_SKIP, TOP_FRAC = 252, 21, 1 / 3


def _close(sid: str) -> pd.Series:
    df = load_merged_parquet(sid)
    s = df[["trade_date", "close"]].copy()
    s["trade_date"] = pd.to_datetime(s["trade_date"])
    px = s.set_index("trade_date")["close"].astype(float).sort_index()
    return px[px > 0]  # drop zero/blank closes (halt placeholders) before pct_change


def _rets(px: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    """Daily returns, with inf and >50%/day data-error jumps winsorized to NaN."""
    r = px.pct_change().replace([np.inf, -np.inf], np.nan)
    return r.where(r.abs() <= 0.5)


def _metrics(daily: pd.Series, label: str) -> dict:
    daily = daily.dropna()
    if len(daily) < 60:
        return {"label": label, "n": len(daily), "cagr": float("nan"),
                "sharpe": float("nan"), "maxdd": float("nan")}
    return {"label": label, "n": len(daily), "cagr": cagr(daily),
            "sharpe": sharpe(daily), "maxdd": max_drawdown(daily)}


def _buy_hold(prices: pd.DataFrame, universe: list[str], start: str, end: str) -> pd.Series:
    return _rets(prices[universe]).loc[start:end].mean(axis=1)


def _momentum(prices: pd.DataFrame, universe: list[str], start: str, end: str) -> pd.Series:
    """Monthly-rebalanced 12-1 cross-sectional momentum, long top ⅓, equal weight,
    cost charged on rebalance turnover."""
    px = prices[universe]
    rets = _rets(px)
    mom = px.shift(MOM_SKIP) / px.shift(MOM_LOOKBACK) - 1.0  # 12-1, per date
    win_days = rets.loc[start:end].index
    if len(win_days) == 0:
        return pd.Series(dtype=float)
    # first trading day of each month = rebalance days
    rebal = [grp.index[0] for _, grp in pd.Series(win_days, index=win_days).groupby(
        [win_days.year, win_days.month])]

    out, held_prev = [], set()
    for i, rb in enumerate(rebal):
        nxt = rebal[i + 1] if i + 1 < len(rebal) else win_days[-1]
        ranked = mom.loc[rb].dropna().sort_values(ascending=False)
        k = max(1, int(len(ranked) * TOP_FRAC))
        held = list(ranked.index[:k])
        if not held:
            continue
        seg = rets.loc[rb:nxt, held].mean(axis=1).copy()
        turnover = len(set(held) ^ held_prev) / max(len(held), 1)
        if len(seg):
            seg.iloc[0] = seg.iloc[0] - COST_ROUND * turnover  # charge cost at rebalance
        out.append(seg)
        held_prev = set(held)
    return pd.concat(out).groupby(level=0).first() if out else pd.Series(dtype=float)


def main() -> None:
    avail = sorted({
        p.name.replace("daily_bars__", "").replace(".parquet", "")
        for p in __import__("pathlib").Path("data/parquet").glob("daily_bars__*.parquet")
    })
    large = [s for s in avail if s in _MEGA]
    smid = [s for s in avail if s not in _MEGA and s != BENCHMARK]
    prices = pd.DataFrame({s: _close(s) for s in avail})
    span = lambda u: f"{prices[u].dropna(how='all').index.min().date()}..{prices[u].dropna(how='all').index.max().date()}"
    print(f"universes — LARGE({len(large)}) {span(large)} | SMID({len(smid)}) {span(smid)} | bench {BENCHMARK}\n")
    print(f"cost_round={COST_ROUND:.4%}  (gate: Sharpe>1.0, CAGR>18%)\n")

    print(f"{'universe':<7} {'strategy':<14} {'window':<11} {'n':>4} {'CAGR':>8} {'Sharpe':>7} {'MaxDD':>7} {'gate':>5}")
    print("-" * 72)
    rows = []
    for wlabel, ws, we in WINDOWS:
        rows.append(("bench", "0050 buy-hold", wlabel, _metrics(_rets(prices[BENCHMARK]).loc[ws:we], "")))
        for uname, u in (("LARGE", large), ("SMID", smid)):
            if not u:
                continue
            rows.append((uname, "EW buy-hold", wlabel, _metrics(_buy_hold(prices, u, ws, we), "")))
            rows.append((uname, "12-1 mom ⅓", wlabel, _metrics(_momentum(prices, u, ws, we), "")))
    for uni, strat, wlabel, m in rows:
        g = "PASS" if (m["sharpe"] > 1.0 and m["cagr"] > 0.18) else "fail"
        print(f"{uni:<7} {strat:<14} {wlabel:<11} {m['n']:>4} "
              f"{m['cagr']:>8.4f} {m['sharpe']:>7.3f} {m['maxdd']:>7.3f} {g:>5}")

    print("\n=== 對照 four-layer（中小型探針 PR #51）===")
    print("  v2    SMID  2015-2020 CAGR -0.38% Sharpe -0.16 | 2020-2024 -1.11% -0.33")
    print("  v3.1b SMID  2015-2020 CAGR -1.61% Sharpe -0.37 | 2020-2024 -3.05% -0.63")
    print("\n判讀：對照上表的 EW buy-hold 與 12-1 momentum——")
    print("  · buy-hold 也負 → universe/期間本身下行（問題在標的池，非策略）")
    print("  · momentum 明顯 > buy-hold/正 → 平台能偵測 edge，四層本身才是問題")
    print("  · momentum ≈ buy-hold 且皆弱 → 此資料/成本下難萃 edge（成本牆或盤本身）")


if __name__ == "__main__":
    main()
