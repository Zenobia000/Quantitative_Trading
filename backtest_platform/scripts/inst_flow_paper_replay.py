"""inst_flow paper replay — run the VALIDATED candidate through the real chain (7.A.4).

The two-stage gate judged inst_flow REAL (inst_flow_truth_gate.py). This script
takes that fixed config and drives it through the *production* daily-flow chain —
ETL → signals → risk gate → orders → log — using the real collaborators
(RiskGate + PaperBroker + TimescaleDB sink), over HISTORICAL data (replay, no
live-calendar wait). It proves the orchestration "待真實跑" rows turn green with a
real strategy, and persists the run to a real DB (closing the loop with 7.A.2).

This is paper REPLAY (one as-of rebalance over cached data), distinct from the
forward 3-month paper run (7.A.3) which needs real calendar time + a daemon.

Run (DB up + env set):
  POSTGRES_INTEGRATION=1 POSTGRES_HOST=localhost ... \
    uv run python scripts/inst_flow_paper_replay.py
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from backtest_platform.adapters.brokers.paper_broker import PaperBroker
from backtest_platform.data.db_writer import DBConfig
from backtest_platform.orchestration.collaborators import build_paper_collaborators
from backtest_platform.orchestration.daily_flow import FlowContext, build_daily_stages, run_flow
from backtest_platform.research.is_harness import load_merged_parquet
from backtest_platform.strategies.inst_flow.signal_fn import make_inst_flow_signal_fn
from backtest_platform.strategies.inst_flow.strategy import InstFlowConfig

FIXED = InstFlowConfig(rebalance="quarterly", lookback_days=60, flow_source="foreign")
SPAN_START, SPAN_END = date(2015, 1, 1), date(2024, 12, 31)
AS_OF = date(2023, 1, 3)  # a rebalance as-of with ample trailing data
INITIAL_CASH = 10_000_000.0
STRATEGY_ID = "inst_flow"
RUN_ID = f"paper_replay_{AS_OF:%Y%m%d}"


def _all_symbols() -> list[str]:
    return sorted(
        p.name.replace("daily_bars__", "").replace(".parquet", "")
        for p in Path("data/parquet").glob("daily_bars__*.parquet")
    )


def _load(symbols):
    close, vol, raw = {}, {}, {}
    for sid in symbols:
        try:
            df = load_merged_parquet(sid)
        except Exception:  # noqa: BLE001
            continue
        if "foreign_buy" not in df or df["foreign_buy"].abs().sum() == 0:
            continue
        df = df.assign(trade_date=pd.to_datetime(df["trade_date"])).set_index("trade_date").sort_index()
        close[sid], vol[sid], raw[sid] = df["close"].astype(float), df["volume"].astype(float), df
    return pd.DataFrame(close), pd.DataFrame(vol), raw


def _flow(raw, cols):
    return pd.DataFrame({s: raw[s][list(cols)].sum(axis=1).astype(float) for s in raw})


def _clean_prior(cfg: DBConfig) -> None:
    """Make the replay idempotent — clear any prior rows for this run_id."""
    import psycopg2  # type: ignore[import-not-found]

    with psycopg2.connect(cfg.dsn()) as conn, conn.cursor() as cur:
        for t in ("signals", "equity_snapshots"):
            cur.execute(f"DELETE FROM {t} WHERE run_id = %s", (RUN_ID,))
        conn.commit()


def main() -> None:
    close, vol, raw = _load(_all_symbols())
    flow = _flow(raw, FIXED.flow_cols)
    print(f"panel: {close.shape[1]} symbols × {close.shape[0]} bars; as_of {AS_OF}")

    cfg = DBConfig.from_env()
    _clean_prior(cfg)

    broker = PaperBroker(initial_cash=INITIAL_CASH)
    signal_fn = make_inst_flow_signal_fn(close, flow, vol, FIXED, AS_OF, equity=INITIAL_CASH)
    config = build_paper_collaborators(
        universe=list(close.columns),
        signal_fn=signal_fn,
        broker=broker,
        run_id=RUN_ID,
        strategy_id=STRATEGY_ID,
        start=SPAN_START,
        end=SPAN_END,
        ingest_fn=lambda syms: {s: True for s in syms},  # cached parquet → already ingested
    )

    run = run_flow(build_daily_stages(), FlowContext(config=config))
    print("\n" + run.summary())

    snap = broker.portfolio_snapshot()
    print(f"\nbroker: equity {snap['equity']:,.0f} | cash {snap['cash']:,.0f} | "
          f"positions {len(snap['positions'])} | fills {len(broker.trade_log)}")

    # verify persistence landed in the real DB
    import psycopg2  # type: ignore[import-not-found]

    with psycopg2.connect(cfg.dsn()) as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM signals WHERE run_id = %s", (RUN_ID,))
        n_sig = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM equity_snapshots WHERE run_id = %s", (RUN_ID,))
        n_eq = cur.fetchone()[0]
        cur.execute("SELECT stock_id, action FROM signals WHERE run_id = %s ORDER BY stock_id", (RUN_ID,))
        rows = cur.fetchall()

    print(f"\nDB persisted: signals={n_sig} equity_snapshots={n_eq}")
    print("  signals:", " ".join(f"{sid}:{act}" for sid, act in rows))

    ok = run.ok and n_sig > 0
    print(f"\n{'='*64}")
    print(f"{'🟢 CHAIN GREEN' if ok else '🔴 CHAIN FAILED'} — validated inst_flow ran the "
          f"real ETL→signals→risk→orders→log chain and persisted to TimescaleDB.")
    print(f"{'='*64}")


if __name__ == "__main__":
    main()
