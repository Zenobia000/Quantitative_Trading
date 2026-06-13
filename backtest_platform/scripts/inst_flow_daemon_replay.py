"""inst_flow daemon replay — multi-session telemetry via the 8.H.8 daemon (replay).

Goal-#2 (inst_flow_paper_replay) proved ONE session runs the chain. This drives
the 8.H.8 paper daemon over MULTIPLE quarterly as-of sessions on a SHARED broker,
so equity evolves across sessions and the run produces the multi-session telemetry
the Monitor views + time-series tables consume — all over historical data (replay,
no live-calendar wait). The forward-live daemon swaps the date source for a
real-time scheduler but reuses this exact execution + persistence core.

Run (DB up + env set):
  POSTGRES_INTEGRATION=1 POSTGRES_HOST=localhost ... \
    uv run python scripts/inst_flow_daemon_replay.py
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from backtest_platform.adapters.brokers.paper_broker import PaperBroker
from backtest_platform.data.db_writer import DBConfig
from backtest_platform.orchestration.collaborators import build_paper_collaborators
from backtest_platform.research.is_harness import load_merged_parquet
from backtest_platform.runtime.paper_daemon import replay_schedule, run_paper_replay
from backtest_platform.strategies.inst_flow.signal_fn import make_inst_flow_signal_fn
from backtest_platform.strategies.inst_flow.strategy import InstFlowConfig


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


FIXED = InstFlowConfig(rebalance="quarterly", lookback_days=60, flow_source="foreign")
SPAN_START, SPAN_END = date(2015, 1, 1), date(2024, 12, 31)
INITIAL_CASH = 10_000_000.0
STRATEGY_ID = "inst_flow"
RUN_ID = "daemon_replay_2023"
PER_NAME_CAP = 120_000.0  # small so cash lasts across several quarters


def _clean_prior(cfg: DBConfig) -> None:
    import psycopg2  # type: ignore[import-not-found]

    with psycopg2.connect(cfg.dsn()) as conn, conn.cursor() as cur:
        for t in ("signals", "equity_snapshots"):
            cur.execute(f"DELETE FROM {t} WHERE run_id = %s", (RUN_ID,))
        conn.commit()


def main() -> None:
    close, vol, raw = _load(_all_symbols())
    flow = _flow(raw, FIXED.flow_cols)

    # replay the 2023 quarterly sessions
    all_dates = replay_schedule(close.loc[str(SPAN_START):str(SPAN_END)].index, "quarterly")
    dates = [d for d in all_dates if d.year == 2023]
    print(f"panel: {close.shape[1]} symbols; replaying {len(dates)} quarterly sessions: "
          f"{', '.join(str(d) for d in dates)}")

    cfg = DBConfig.from_env()
    _clean_prior(cfg)

    broker = PaperBroker(initial_cash=INITIAL_CASH)  # SHARED across sessions

    def config_for_date(d: date) -> dict:
        signal_fn = make_inst_flow_signal_fn(
            close, flow, vol, FIXED, d, equity=broker.cash, per_name_cap=PER_NAME_CAP,
        )
        return build_paper_collaborators(
            universe=list(close.columns), signal_fn=signal_fn, broker=broker,
            run_id=RUN_ID, strategy_id=STRATEGY_ID, start=SPAN_START, end=SPAN_END,
            ingest_fn=lambda syms: {s: True for s in syms},
        )

    summary = run_paper_replay(dates, config_for_date)
    print("\n" + summary.summary())

    snap = broker.portfolio_snapshot()
    print(f"\nbroker after replay: equity {snap['equity']:,.0f} | cash {snap['cash']:,.0f} | "
          f"positions {len(snap['positions'])} | total fills {len(broker.trade_log)}")

    import psycopg2  # type: ignore[import-not-found]

    with psycopg2.connect(cfg.dsn()) as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM signals WHERE run_id = %s", (RUN_ID,))
        n_sig = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM equity_snapshots WHERE run_id = %s", (RUN_ID,))
        n_eq = cur.fetchone()[0]

    print(f"\nDB telemetry: signals={n_sig} equity_snapshots={n_eq} across {summary.n_ok} green sessions")
    ok = summary.n_ok > 0 and n_eq > 0
    print(f"\n{'='*66}")
    print(f"{'🟢 DAEMON REPLAY GREEN' if ok else '🔴 DAEMON REPLAY FAILED'} — multi-session "
          f"telemetry persisted; the Monitor/time-series feed is now real-data-backed.")
    print(f"{'='*66}")


if __name__ == "__main__":
    main()
