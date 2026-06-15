"""Real daily-flow collaborators (7.D real wiring).

Promotes the proven RiskGate + PaperBroker collaborator factories from the chain
integration test into reusable production code, and adds the real persistence
sink (7.A.2: signals / fills / equity → TimescaleDB) and the FinMind ingest.

``signal_fn`` (which strategy produces the day's signals) stays an *injected*
seam — which strategy to run is a deployment / edge decision, not orchestration
infra (and no deployable edge exists yet). ``build_paper_collaborators`` wires a
ready ``FlowContext.config`` of real collaborators given a broker + a signal_fn.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import date, datetime, timedelta, timezone
from typing import Any

from backtest_platform.adapters.brokers.paper_broker import Fill, OrderSide, PaperBroker
from backtest_platform.risk.risk_gate import AccountState, Order, RiskGate

_TWT = timezone(timedelta(hours=8))
_SIDE_DB = {OrderSide.BUY: "Buy", OrderSide.SELL: "Sell"}


def _now_twt() -> datetime:
    return datetime.now(_TWT)


# --------------------------------------------------------------------------- #
# risk + orders — real RiskGate / PaperBroker (promoted from the chain test)   #
# --------------------------------------------------------------------------- #
def make_risk_check(
    broker: PaperBroker, gate: RiskGate | None = None, *, equity: float | None = None
) -> Callable[[list[dict]], tuple[bool, str]]:
    """Real ex-ante risk collaborator: approve only if every signal clears all 12 rules."""
    gate = gate or RiskGate()

    def check(signals: list[dict]) -> tuple[bool, str]:
        account = AccountState(
            equity=equity if equity is not None else broker.cash, cash=broker.cash, positions=()
        )
        for s in signals:
            order = Order(
                stock_id=s["stock_id"], side=s["side"], qty=s["qty"], price=s["price"],
                industry=s.get("industry", ""), stop_loss=s.get("stop_loss", 0.0),
                prev_close=s.get("prev_close", 0.0), avg_volume_20d=s.get("avg_volume_20d", 0.0),
            )
            result = gate.check(order, account)
            if not result.allowed:
                return False, f"{s['stock_id']} rejected: {result.rejections}"
        return True, f"{len(signals)} orders approved"

    return check


def make_place(broker: PaperBroker) -> Callable[[list[dict]], list[Fill]]:
    """Real order collaborator: submit each approved signal, return the fills."""

    def place(signals: list[dict]) -> list[Fill]:
        return [broker.submit_order(s["stock_id"], s["side"], s["qty"], s["price"]) for s in signals]

    return place


# --------------------------------------------------------------------------- #
# ETL — FinMind universe ingest → per-symbol ok map                            #
# --------------------------------------------------------------------------- #
def make_ingest(
    *,
    start: date,
    end: date,
    ingest_fn: Callable[[list[str]], dict[str, bool]] | None = None,
    cache_dir: Any = None,
    source: str = "finlab",
) -> Callable[[list[str]], dict[str, bool]]:
    """Real ETL collaborator → per-symbol ok map.

    ``source`` selects the data source: ``"finlab"`` (default, ADR-006 primary —
    full history + survivorship-clean) or ``"finmind"`` (fallback). A custom
    ``ingest_fn`` may be injected (e.g. a cached-parquet check) and wins over both.
    """
    if ingest_fn is not None:
        return ingest_fn

    def ingest(symbols: list[str]) -> dict[str, bool]:
        if source == "finlab":
            from backtest_platform.data.finlab_source import ingest_universe_finlab

            result = ingest_universe_finlab(list(symbols), start, end, cache_dir=cache_dir)
        else:
            from backtest_platform.engines.zipline_adapter.bundles.finmind_bundle import (
                ingest_universe,
            )

            result = ingest_universe(list(symbols), start=start, end=end, cache_dir=cache_dir)
        failed = set(result.failed_symbols)
        return {s: s not in failed for s in symbols}

    return ingest


# --------------------------------------------------------------------------- #
# log sink — persist the run to TimescaleDB (7.A.2 wiring)                      #
# --------------------------------------------------------------------------- #
def _signal_row(s: Mapping[str, Any], run_id: str, strategy_id: str, now: datetime) -> dict[str, Any]:
    return {
        "signal_time": s.get("signal_time", now),
        "strategy_id": strategy_id,
        "run_id": run_id,
        "stock_id": s.get("stock_id"),
        "action": s.get("action", s.get("side", "hold")),
        "priority": int(s.get("priority", 7)),
        "reason_json": s.get("reason", {}),
        "submitted": True,
        "submitted_at": now,
    }


def _fill_row(f: Fill, now: datetime) -> dict[str, Any]:
    return {
        "stock_id": f.stock_id,
        "side": _SIDE_DB.get(f.side, str(f.side)),
        "qty": f.qty,
        "price": f.price,
        "filled_at": now,
    }


def _equity_row(broker: PaperBroker, run_id: str, strategy_id: str, mode: str, now: datetime) -> dict[str, Any]:
    snap = broker.portfolio_snapshot()
    return {
        "snapshot_time": now,
        "strategy_id": strategy_id,
        "mode": mode,
        "run_id": run_id,
        "equity": snap["equity"],
        "cash": snap["cash"],
        "positions_value": snap["equity"] - snap["cash"],
        "open_positions": len(snap["positions"]),
        "portfolio_heat": snap["heat"],
    }


def make_db_sink(
    run_id: str,
    strategy_id: str,
    *,
    mode: str = "paper",
    broker: PaperBroker | None = None,
    writer: Any = None,
    clock: Callable[[], datetime] = _now_twt,
) -> Callable[[Any], str]:
    """Real log stage: persist the run's signals + fills (+ an equity snapshot when
    a broker is given) via ``db_writer`` (7.A.2). ``writer``/``clock`` are injectable
    for tests. Returns a human-readable record id."""

    def sink(ctx: Any) -> str:
        from backtest_platform.data import db_writer as _dbw

        w = writer or _dbw
        now = clock()
        signals = ctx.outputs.get("signals", []) or []
        fills = ctx.outputs.get("orders", []) or []
        n_sig = w.upsert_signals([_signal_row(s, run_id, strategy_id, now) for s in signals])
        n_fill = w.upsert_fills([_fill_row(f, now) for f in fills])
        n_eq = w.upsert_equity_snapshots([_equity_row(broker, run_id, strategy_id, mode, now)]) if broker else 0
        return f"persisted run={run_id}: signals={n_sig} fills={n_fill} equity={n_eq}"

    return sink


# --------------------------------------------------------------------------- #
# assembly                                                                     #
# --------------------------------------------------------------------------- #
def build_paper_collaborators(
    *,
    universe: Sequence[str],
    signal_fn: Callable[[Any], list[dict]],
    broker: PaperBroker,
    run_id: str,
    strategy_id: str,
    start: date,
    end: date,
    mode: str = "paper",
    ingest_fn: Callable[[list[str]], dict[str, bool]] | None = None,
) -> dict[str, Any]:
    """Assemble a ``FlowContext.config`` of REAL collaborators for a paper run.

    ``signal_fn`` (the strategy) is injected — *which* strategy to run is the gated
    decision; everything else (ingest / risk / orders / persistence) is real infra.
    """
    return {
        "universe": list(universe),
        "ingest": make_ingest(start=start, end=end, ingest_fn=ingest_fn),
        "signal_fn": signal_fn,
        "risk_check": make_risk_check(broker),
        "place": make_place(broker),
        "sink": make_db_sink(run_id, strategy_id, mode=mode, broker=broker),
    }
