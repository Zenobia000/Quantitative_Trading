"""Momentum IS runner — formal gate run + a knob for robustness stress tests.

    uv run python scripts/momentum_is.py --universe smid --start 2015-01-01 --end 2020-12-31

Robustness use (for the adversarial-verification workflow): vary
--lookback/--skip/--top-frac/--cost-mult to test whether the momentum edge is a
robust plateau or a fragile point. Uses cached parquet only (no network).
"""
from __future__ import annotations

import argparse
from pathlib import Path

from backtest_platform.research.momentum_harness import run_momentum_is
from backtest_platform.strategies.momentum.strategy import MomentumConfig
from backtest_platform.validation.gate_state import MOMENTUM_GATE, evaluate_gate

_BASE_COST = 0.00671
_MEGA = {"2330", "2317", "2454", "2412", "2882", "2891", "2308", "1303", "1101", "3008"}


def _universe(name: str) -> list[str]:
    avail = sorted(
        p.name.replace("daily_bars__", "").replace(".parquet", "")
        for p in Path("data/parquet").glob("daily_bars__*.parquet")
    )
    if name == "large":
        return [s for s in avail if s in _MEGA]
    if name == "smid":
        return [s for s in avail if s not in _MEGA and s != "0050"]
    return [s for s in avail if s != "0050"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", default="smid", choices=["large", "smid", "all"])
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--lookback", type=int, default=252)
    ap.add_argument("--skip", type=int, default=21)
    ap.add_argument("--top-frac", type=float, default=1 / 3)
    ap.add_argument("--cost-mult", type=float, default=1.0, help="multiply base cost_round (0.671%)")
    a = ap.parse_args()

    cfg = MomentumConfig(
        lookback_days=a.lookback, skip_days=a.skip, top_fraction=a.top_frac,
        cost_round_rate=_BASE_COST * a.cost_mult,
    )
    uni = _universe(a.universe)
    m = run_momentum_is(uni, a.start, a.end, cfg)
    g = evaluate_gate(m, MOMENTUM_GATE)
    print(f"universe={a.universe}({len(uni)}) {a.start}..{a.end} "
          f"lookback={a.lookback} skip={a.skip} top={a.top_frac:.2f} cost×{a.cost_mult}")
    print(f"  cagr={m.get('cagr', 0):.4f} sharpe={m.get('sharpe', 0):.3f} "
          f"slipSh={m.get('slippage_sharpe', 0):.3f} maxdd={m.get('maxdd', 0):.3f} "
          f"holdings={m.get('avg_holdings', 0):.1f} turnover={m.get('avg_turnover', 0):.2f} "
          f"rebal={m.get('n_rebalances', 0)}")
    print(f"  GATE[{g.status.value}]: " + "  ".join(
        f"{r.criterion.key}={'✓' if r.passed else '✗'}" for r in g.results))


if __name__ == "__main__":
    main()
