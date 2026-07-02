"""Live market reader + forward-paper wiring (③ / 7.A.4 forward / 8.H.8 live).

The paper daemon's replay core (`runtime.paper_daemon.run_paper_replay`) is
clock-agnostic: it runs the daily-flow chain once per as-of date. **Replay** reads
cached parquet; **forward live** reads a *fresh* panel through "today". This module
is that live data path + the wiring that turns it into a `config_for_date` the
daemon consumes unchanged.

`read_live_panel` fetches the EOD panel (adjusted close / foreign net-buy / volume)
from **FinLab** (① `finlab_source`) sliced to ``[as_of - lookback, as_of]`` — the
same shape the replay loader produces, so the *same* inst_flow ``signal_fn`` runs
forward. `live_config_for_date` binds it into `build_paper_collaborators`.

`make_position_signal_fn` is a **generic** adapter: any strategy that yields a list
of target holdings (e.g. the FinLab `stock_strategy/` references) drives the real
chain (ETL→signals→risk→orders→log) through the platform's gate + broker.

The **after-close scheduler** that fires `run_forward_session(today)` once per
session close now lives in `orchestration.after_close` (+ the `after-close` CLI
subcommand): trading-day / after-close-time / idempotency guards over real calendar
time, wired to cron / systemd timer (`deploy/`). Its decision path is fully
injectable + unit-tested; this module stays the proven per-session execution core.
"""
from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from datetime import date
from typing import Any

import pandas as pd

from backtest_platform.data import finlab_source as fl
from backtest_platform.orchestration.collaborators import build_paper_collaborators
from backtest_platform.runtime.market_data_errors import NoMarketDataError
from backtest_platform.strategies.inst_flow.signal_fn import (
    DEFAULT_MAX_NAMES,
    DEFAULT_PER_NAME_CAP,
    STOP_LOSS_FRAC,
    make_inst_flow_signal_fn,
)
from backtest_platform.strategies.inst_flow.strategy import InstFlowConfig

PanelGetter = Callable[[str], pd.DataFrame]


def read_live_panel(
    universe: Sequence[str],
    as_of: date,
    *,
    lookback_days: int = 400,
    getter: PanelGetter | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fetch the EOD ``(close, flow, volume)`` panel for ``universe`` through ``as_of``.

    ``flow`` is foreign net-buy (the inst_flow factor input). Same wide shape the
    replay loader yields, so the backtest ``signal_fn`` runs forward unchanged.
    Strictly historical: only rows on/before ``as_of`` are returned.
    """
    getter = getter or fl._default_getter()
    lo = pd.Timestamp(as_of) - pd.Timedelta(days=lookback_days)
    hi = pd.Timestamp(as_of)
    cols = list(universe)

    def slab(wide: pd.DataFrame) -> pd.DataFrame:
        w = wide.sort_index()
        keep = [c for c in cols if c in w.columns]
        return w.loc[lo:hi, keep]

    close = slab(getter(fl._ADJ["close"]))
    volume = slab(getter(fl._VOLUME))
    flow = slab(fl._sum_wide(getter, fl._FOREIGN))
    return close, flow, volume


def check_panel_freshness(close: pd.DataFrame, as_of: date, *, strategy: str) -> None:
    """Raise :class:`NoMarketDataError` if the live panel has no row dated ``as_of``.

    This is the explicit no-data seam the after-close scheduler degrades on. On a
    weekday Taiwan public holiday the approximate Mon–Fri calendar mis-fires: FinLab
    returns only rows *before* ``as_of`` (its latest is the prior session). Feeding
    that to the chain would silently run on stale data — ``compute_inst_flow_signals``
    falls back to the last available row — so instead we surface the condition. The
    scheduler turns it into a benign skip; a genuine failure raises a different error
    and still alerts.
    """
    if close is None or close.empty:
        raise NoMarketDataError(strategy, as_of, "empty panel")
    last = close.index.max()
    last_date = last.date() if hasattr(last, "date") else last
    if last_date < as_of:
        raise NoMarketDataError(
            strategy, as_of, f"latest panel row {last_date} < as_of {as_of}"
        )


def live_config_for_date(
    universe: Sequence[str],
    cfg: InstFlowConfig,
    broker: Any,
    *,
    run_id: str,
    strategy_id: str,
    getter: PanelGetter | None = None,
    lookback_days: int = 400,
    equity: float | None = None,
    sink: Callable[[Any], str] | None = None,
) -> Callable[[date], dict[str, Any]]:
    """Build a ``config_for_date`` for ``run_paper_replay`` that reads a *live* panel
    per session and runs the inst_flow chain forward.

    The ETL stage is a no-op ok-map (data is read live into the panel, not ingested).
    ``sink`` overrides the persistence collaborator (e.g. an in-memory sink in tests);
    default is the real TimescaleDB sink from ``build_paper_collaborators``.
    """

    def config_for_date(d: date) -> dict[str, Any]:
        close, flow, volume = read_live_panel(universe, d, lookback_days=lookback_days, getter=getter)
        eq = equity if equity is not None else broker.cash
        signal_fn = make_inst_flow_signal_fn(close, flow, volume, cfg, d, equity=eq)
        config = build_paper_collaborators(
            universe=list(universe),
            signal_fn=signal_fn,
            broker=broker,
            run_id=f"{run_id}_{d}",
            strategy_id=strategy_id,
            start=d,
            end=d,
            ingest_fn=lambda symbols: {s: True for s in symbols},  # data read live
        )
        if sink is not None:
            config["sink"] = sink
        return config

    return config_for_date


def make_position_signal_fn(
    holdings: Sequence[str],
    prices: pd.Series,
    avg_volume: pd.Series,
    *,
    equity: float,
    max_names: int = DEFAULT_MAX_NAMES,
    per_name_cap: float = DEFAULT_PER_NAME_CAP,
    stop_loss_frac: float = STOP_LOSS_FRAC,
) -> Callable[[Any], list[dict[str, Any]]]:
    """Generic strategy → daily-flow ``signal_fn`` adapter.

    Turns a list of target ``holdings`` (the buy list any strategy produces — e.g. a
    FinLab `stock_strategy/` position's True columns on a date) into equal-weight,
    gate-safe BUY signal dicts in the chain's schema, so *any* strategy can be run
    end-to-end through the platform's RiskGate + PaperBroker + sink.
    """

    def signal_fn(_ctx: Any) -> list[dict[str, Any]]:
        held = list(holdings)[:max_names]
        if not held:
            return []
        per_name = min(equity / len(held), per_name_cap)
        signals: list[dict[str, Any]] = []
        for rank, sid in enumerate(held, start=1):
            price = float(prices.get(sid, float("nan")))
            if not math.isfinite(price) or price <= 0:
                continue
            qty = int(per_name // price)
            if qty <= 0:
                continue
            signals.append({
                "stock_id": sid,
                "side": "buy",
                "qty": qty,
                "price": round(price, 4),
                "action": "buy",
                "priority": 3,
                "reason": {"source": "position_adapter", "rank": rank},
                "stop_loss": round(price * (1.0 - stop_loss_frac), 4),
                "prev_close": round(price, 4),
                "avg_volume_20d": float(avg_volume.get(sid, 0.0)),
                "industry": "",
            })
        return signals

    return signal_fn


def run_forward_session(as_of: date, config_for_date: Callable[[date], dict[str, Any]]) -> Any:
    """Run ONE forward session (after-close). Thin entry over the proven replay core.

    The recurring after-close trigger (the real-calendar cron / systemd timer that
    fires this once per session close) lives in `orchestration.after_close`, not
    here — this function stays the single-session execution primitive it schedules.
    The per-date execution + persistence is identical to replay (②), so this reuses it.
    """
    from backtest_platform.runtime.paper_daemon import run_paper_replay

    return run_paper_replay([as_of], config_for_date)
