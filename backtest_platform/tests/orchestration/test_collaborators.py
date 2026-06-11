"""Real daily-flow collaborators (7.D) — RiskGate / PaperBroker / DB sink / ingest.

The risk + place factories drive a real RiskGate + PaperBroker; the db sink is
tested with an injected fake writer (no DB) and a fixed clock, so persistence is
asserted without a live TimescaleDB.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import MagicMock

from backtest_platform.adapters.brokers.paper_broker import PaperBroker
from backtest_platform.orchestration.collaborators import (
    build_paper_collaborators,
    make_db_sink,
    make_ingest,
    make_place,
    make_risk_check,
)
from backtest_platform.orchestration.daily_flow import FlowContext, build_daily_stages, run_flow

_EQUITY = 1_000_000.0
_FIXED_NOW = datetime(2026, 6, 11, 13, 30, tzinfo=timezone.utc)


def _signals() -> list[dict]:
    return [
        {"stock_id": "2330", "side": "buy", "qty": 500, "price": 50.0, "action": "buy",
         "stop_loss": 48.0, "prev_close": 50.0, "avg_volume_20d": 100_000.0, "industry": "semi"},
        {"stock_id": "2317", "side": "buy", "qty": 400, "price": 60.0, "action": "buy",
         "stop_loss": 57.5, "prev_close": 60.0, "avg_volume_20d": 100_000.0, "industry": "ee"},
    ]


def test_make_risk_check_approves_clean_signals_and_rejects_oversize() -> None:
    broker = PaperBroker(initial_cash=_EQUITY)
    check = make_risk_check(broker, equity=_EQUITY)
    ok, reason = check(_signals())
    assert ok and "approved" in reason
    # an order far over the single-name cap is rejected
    bad = [{"stock_id": "2330", "side": "buy", "qty": 1_000_000, "price": 600.0}]
    rejected, why = check(bad)
    assert not rejected and "rejected" in why


def test_make_place_books_real_fills() -> None:
    broker = PaperBroker(initial_cash=_EQUITY)
    fills = make_place(broker)(_signals())
    assert len(fills) == 2
    assert {f.stock_id for f in fills} == {"2330", "2317"}
    assert len(broker.trade_log) == 2


def test_make_ingest_maps_failed_symbols(monkeypatch) -> None:
    fake_result = MagicMock(failed_symbols=["9999"])
    monkeypatch.setattr(
        "backtest_platform.engines.zipline_adapter.bundles.finmind_bundle.ingest_universe",
        lambda *a, **k: fake_result,
    )
    ingest = make_ingest(start=date(2024, 1, 1), end=date(2024, 12, 31))
    assert ingest(["2330", "9999"]) == {"2330": True, "9999": False}


def test_make_db_sink_persists_signals_fills_and_equity() -> None:
    broker = PaperBroker(initial_cash=_EQUITY)
    fills = make_place(broker)(_signals())
    writer = MagicMock()
    writer.upsert_signals.return_value = 2
    writer.upsert_fills.return_value = 2
    writer.upsert_equity_snapshots.return_value = 1

    sink = make_db_sink("run-1", "momentum", broker=broker, writer=writer, clock=lambda: _FIXED_NOW)
    ctx = FlowContext(config={})
    ctx.outputs["signals"] = _signals()
    ctx.outputs["orders"] = fills
    ref = sink(ctx)

    assert "run=run-1" in ref and "fills=2" in ref
    # signals carry strategy/run + the fixed clock
    sig_rows = writer.upsert_signals.call_args.args[0]
    assert sig_rows[0]["strategy_id"] == "momentum" and sig_rows[0]["submitted_at"] == _FIXED_NOW
    # fills mapped to filled-order shape (side normalized Buy/Sell)
    fill_rows = writer.upsert_fills.call_args.args[0]
    assert fill_rows[0]["side"] == "Buy" and fill_rows[0]["filled_at"] == _FIXED_NOW
    # one equity snapshot for the run
    eq_rows = writer.upsert_equity_snapshots.call_args.args[0]
    assert eq_rows[0]["run_id"] == "run-1" and eq_rows[0]["mode"] == "paper"


def test_make_db_sink_without_broker_skips_equity() -> None:
    writer = MagicMock()
    writer.upsert_signals.return_value = 0
    writer.upsert_fills.return_value = 0
    sink = make_db_sink("run-2", "momentum", writer=writer, clock=lambda: _FIXED_NOW)
    sink(FlowContext(config={}))
    writer.upsert_equity_snapshots.assert_not_called()


def test_paper_collaborators_drive_full_flow_end_to_end() -> None:
    broker = PaperBroker(initial_cash=_EQUITY)
    writer = MagicMock(upsert_signals=MagicMock(return_value=2),
                       upsert_fills=MagicMock(return_value=2),
                       upsert_equity_snapshots=MagicMock(return_value=1))
    config = build_paper_collaborators(
        universe=["2330", "2317"], signal_fn=lambda ctx: _signals(), broker=broker,
        run_id="run-3", strategy_id="momentum", start=date(2024, 1, 1), end=date(2024, 12, 31),
        ingest_fn=lambda syms: {s: True for s in syms},  # avoid network in the test
    )
    # swap the sink's writer for the fake (build wires the real db_writer otherwise)
    config["sink"] = make_db_sink("run-3", "momentum", broker=broker, writer=writer, clock=lambda: _FIXED_NOW)

    run = run_flow(build_daily_stages(), FlowContext(config=config))
    assert run.ok, run.summary()
    assert [s.name for s in run.stages] == ["etl", "signals", "risk_gate", "orders", "log"]
    assert len(broker.trade_log) == 2
    writer.upsert_fills.assert_called_once()
