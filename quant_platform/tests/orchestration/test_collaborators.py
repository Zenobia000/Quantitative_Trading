"""Real daily-flow collaborators (7.D) — RiskGate / PaperBroker / DB sink / ingest.

The risk + place factories drive a real RiskGate + PaperBroker; the db sink is
tested with an injected fake writer (no DB) and a fixed clock, so persistence is
asserted without a live TimescaleDB.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import MagicMock

import pytest

from quant_platform.services.execution_gateway.paper_broker import OrderSide, PaperBroker
from quant_platform.services.execution_gateway.collaborators import (
    build_paper_collaborators,
    make_db_sink,
    make_ingest,
    make_place,
    make_risk_check,
)
from quant_platform.services.strategy_runtime.daily_flow import FlowContext, build_daily_stages, run_flow
from quant_platform.services.risk_gate.risk_gate import RiskGate, RiskGateConfig

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


# --------------------------------------------------------------------------- #
# Risk-check integrity: the gate must see the broker's real portfolio state.   #
# --------------------------------------------------------------------------- #
def test_risk_check_sees_held_position_and_blocks_over_single_name_limit() -> None:
    """EX-002: a held position + a new buy that would push the single name over
    8% of equity is rejected. Regression for the empty-snapshot bug where the
    gate always saw ``positions=()`` and every portfolio-level rule passed."""
    broker = PaperBroker(initial_cash=_EQUITY)
    # Establish a 7%-of-equity holding in 2330 (below the 8% single-name cap).
    broker.submit_order("2330", "buy", 700, 100.0)
    check = make_risk_check(broker)  # equity derived from the broker's real state
    # A further 2%-of-equity buy of the SAME name → projected ~9% ≥ 8% → EX-002.
    more = [{"stock_id": "2330", "side": "buy", "qty": 200, "price": 100.0,
             "stop_loss": 96.0, "prev_close": 100.0, "avg_volume_20d": 1_000_000.0,
             "industry": "semi"}]
    ok, reason = check(more)
    assert not ok
    assert "EX-002" in reason


def test_risk_check_decrements_cash_within_batch_blocks_second_buy() -> None:
    """Two buys that each clear against full cash but jointly breach the 10% cash
    floor: the second must be rejected because the batch decrements running cash.
    Regression for re-checking every signal against the same untouched snapshot."""
    broker = PaperBroker(initial_cash=_EQUITY)
    # Relax the per-order / exposure caps so EX-005 (cash floor) is the binding rule.
    gate = RiskGate(RiskGateConfig(
        single_order_max_notional=10_000_000.0,
        single_order_max_equity_pct=0.9,
        single_name_max_pct=0.9,
        industry_max_pct=0.99,
        portfolio_heat_max=0.99,
        cash_floor_pct=0.10,
    ))
    check = make_risk_check(broker, gate)
    batch = [
        {"stock_id": "AAA", "side": "buy", "qty": 5000, "price": 100.0,
         "stop_loss": 96.0, "prev_close": 100.0, "avg_volume_20d": 10_000_000.0},
        {"stock_id": "BBB", "side": "buy", "qty": 4500, "price": 100.0,
         "stop_loss": 96.0, "prev_close": 100.0, "avg_volume_20d": 10_000_000.0},
    ]
    ok, reason = check(batch)
    assert not ok
    assert "BBB rejected" in reason and "EX-005" in reason
    # The first buy alone clears — proves it is the *joint* cash draw that trips.
    ok_single, _ = check([batch[0]])
    assert ok_single


# --------------------------------------------------------------------------- #
# Side-vocabulary translation: strategy sides → broker buy/sell.               #
# --------------------------------------------------------------------------- #
def test_place_translates_add_side_to_broker_buy() -> None:
    """A strategy 'add' side is routed to the broker as a buy; the approved order
    books instead of raising on the broker's buy/sell-only API."""
    broker = PaperBroker(initial_cash=_EQUITY)
    fills = make_place(broker)([
        {"stock_id": "2330", "side": "add", "qty": 300, "price": 100.0},
    ])
    assert len(fills) == 1
    assert fills[0].side is OrderSide.BUY
    assert broker.positions["2330"].qty == 300


def test_place_translates_exit_side_to_broker_sell() -> None:
    """'exit' (and 'reduce' / 'stoploss') route to a broker sell."""
    broker = PaperBroker(initial_cash=_EQUITY)
    broker.submit_order("2330", "buy", 300, 100.0)
    fills = make_place(broker)([
        {"stock_id": "2330", "side": "exit", "qty": 300, "price": 105.0},
    ])
    assert fills[0].side is OrderSide.SELL
    assert "2330" not in broker.positions


def test_place_rejects_unknown_side_loudly() -> None:
    """An unknown side raises (never silently swallowed / mis-routed)."""
    broker = PaperBroker(initial_cash=_EQUITY)
    with pytest.raises(ValueError, match="unknown signal side"):
        make_place(broker)([{"stock_id": "2330", "side": "hold", "qty": 1, "price": 10.0}])


def test_side_vocab_covers_every_risk_gate_side() -> None:
    """The place-layer side map must cover every side the risk gate accepts, so an
    approved order can never fail to translate to a broker side (drift guard)."""
    from quant_platform.services.execution_gateway.collaborators import (
        _SIGNAL_SIDE_TO_BROKER,
    )
    from quant_platform.services.risk_gate.risk_gate import _VALID_SIDES

    assert set(_VALID_SIDES) <= set(_SIGNAL_SIDE_TO_BROKER)


def test_make_ingest_finmind_fallback_maps_failed_symbols(monkeypatch) -> None:
    fake_result = MagicMock(failed_symbols=["9999"])
    monkeypatch.setattr(
        "quant_platform.services.data_platform.finmind_bundle.ingest_universe",
        lambda *a, **k: fake_result,
    )
    ingest = make_ingest(start=date(2024, 1, 1), end=date(2024, 12, 31), source="finmind")
    assert ingest(["2330", "9999"]) == {"2330": True, "9999": False}


def test_make_ingest_defaults_to_finlab(monkeypatch) -> None:
    fake_result = MagicMock(failed_symbols=["9999"])
    monkeypatch.setattr(
        "quant_platform.services.data_platform.finlab_source.ingest_universe_finlab",
        lambda *a, **k: fake_result,
    )
    ingest = make_ingest(start=date(2024, 1, 1), end=date(2024, 12, 31))  # default source
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
    # fills carry normalized side (Buy/Sell), the fixed clock, and strategy_id
    # threaded in for per-sleeve P&L (ADR-038 fills.strategy_id is NOT NULL)
    fill_rows = writer.upsert_fills.call_args.args[0]
    assert fill_rows[0]["side"] == "Buy" and fill_rows[0]["filled_at"] == _FIXED_NOW
    assert fill_rows[0]["strategy_id"] == "momentum"
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
