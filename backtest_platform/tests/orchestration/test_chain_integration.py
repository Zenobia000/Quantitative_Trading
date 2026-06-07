"""End-to-end chain integration (7.D.3, S11).

Drives the canonical daily pipeline (``build_daily_stages``) with **real
collaborators** — RiskGate (12 ex-ante rules) + PaperBroker (simulated matching)
— not stubs, exercising signals → risk gate → order placement → fill log as one
flow. This is the live-wiring rehearsal that proves the modules built across the
waves compose; only the data feed is synthetic (no parquet / no real broker).
"""
from __future__ import annotations

from backtest_platform.adapters.brokers.paper_broker import PaperBroker
from backtest_platform.orchestration.daily_flow import build_daily_stages, run_flow
from backtest_platform.orchestration.daily_flow import FlowContext
from backtest_platform.risk.risk_gate import (
    AccountState,
    Order,
    RiskGate,
)

_EQUITY = 1_000_000.0


def _signals() -> list[dict]:
    """Two clean buy signals, sized well within every risk limit."""
    return [
        {"stock_id": "2330", "side": "buy", "qty": 500, "price": 50.0,
         "stop_loss": 48.0, "prev_close": 50.0, "avg_volume_20d": 100_000.0, "industry": "semi"},
        {"stock_id": "2317", "side": "buy", "qty": 400, "price": 60.0,
         "stop_loss": 57.5, "prev_close": 60.0, "avg_volume_20d": 100_000.0, "industry": "ee"},
    ]


def _risk_check_factory(broker: PaperBroker):
    """Real RiskGate: approve only if every signal clears all 12 rules."""
    gate = RiskGate()

    def check(signals: list[dict]) -> tuple[bool, str]:
        account = AccountState(equity=_EQUITY, cash=broker.cash, positions=())
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


def _place_factory(broker: PaperBroker):
    """Real PaperBroker: submit each approved signal, return the fills."""
    def place(signals: list[dict]) -> list:
        return [broker.submit_order(s["stock_id"], s["side"], s["qty"], s["price"]) for s in signals]

    return place


def _chain_context(broker: PaperBroker, signals: list[dict]) -> FlowContext:
    placed: list = []
    return FlowContext(config={
        "universe": ["2330", "2317"],
        "ingest": lambda syms: {s: True for s in syms},
        "signal_fn": lambda ctx: signals,
        "risk_check": _risk_check_factory(broker),
        "place": _place_factory(broker),
        "sink": lambda ctx: f"chain-run:{len(ctx.outputs.get('orders', placed))}",
    })


def test_full_chain_passes_and_places_real_fills() -> None:
    broker = PaperBroker(initial_cash=_EQUITY)
    signals = _signals()
    run = run_flow(build_daily_stages(), _chain_context(broker, signals))

    assert run.ok, run.summary()
    assert [s.name for s in run.stages] == ["etl", "signals", "risk_gate", "orders", "log"]
    # real broker booked both fills
    assert len(broker.trade_log) == 2
    assert {f.stock_id for f in broker.trade_log} == {"2330", "2317"}
    # cash actually decreased (notional + fees paid)
    assert broker.cash < _EQUITY


def test_risk_rejection_halts_before_orders() -> None:
    broker = PaperBroker(initial_cash=_EQUITY)
    # oversize order: notional 100k * 50 = 5M ≫ EX-001 limit → gate rejects
    bad = [{"stock_id": "2330", "side": "buy", "qty": 100_000, "price": 50.0,
            "stop_loss": 48.0, "prev_close": 50.0, "avg_volume_20d": 100_000.0}]
    run = run_flow(build_daily_stages(), _chain_context(broker, bad))

    assert not run.ok
    assert run.failed_stage == "risk_gate"
    # the flow halted before the orders stage → broker never touched
    assert broker.trade_log == []
    assert {s.name for s in run.stages} == {"etl", "signals", "risk_gate"}


def test_missing_collaborator_fails_cleanly() -> None:
    # no 'place' collaborator → orders stage fails without raising
    ctx = FlowContext(config={
        "universe": ["2330"],
        "ingest": lambda syms: {s: True for s in syms},
        "signal_fn": lambda ctx: _signals(),
        "risk_check": lambda sigs: (True, "ok"),
        # 'place' intentionally absent
    })
    run = run_flow(build_daily_stages(), ctx)
    assert not run.ok
    assert run.failed_stage == "orders"
