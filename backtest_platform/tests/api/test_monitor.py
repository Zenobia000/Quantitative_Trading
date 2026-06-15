"""``/monitor`` — telemetry-backed endpoints (8.H.8) + pending fallback.

A fake :class:`TelemetryReader` is injected via ``get_telemetry_reader`` so these
run without a DB: it returns fixture rows (real-data path) or raises (no-DB path,
→ typed-empty ``pending`` fallback).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backtest_platform.api.app import create_app
from backtest_platform.api.deps import get_telemetry_reader


class _FakeReader:
    def __init__(self, *, equity=None, positions=None, signals=None, fills=None, fail=False):
        self._equity = equity or []
        self._positions = positions or []
        self._signals = signals or []
        self._fills = fills or []
        self._fail = fail

    def equity_series(self, **_kw):
        if self._fail:
            raise RuntimeError("no DB connection")
        return self._equity

    def open_positions(self, **_kw):
        if self._fail:
            raise RuntimeError("no DB connection")
        return self._positions

    def recent_signals(self, **_kw):
        if self._fail:
            raise RuntimeError("no DB connection")
        return self._signals

    def recent_fills(self, **_kw):
        if self._fail:
            raise RuntimeError("no DB connection")
        return self._fills


def _client(reader: _FakeReader) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_telemetry_reader] = lambda: reader
    return TestClient(app)


def test_perf_equity_serves_real_telemetry():
    rows = [{"t": "2023-01-03T00:00:00", "equity": 10_000_000.0, "drawdown": 0.0}]
    body = _client(_FakeReader(equity=rows)).get("/monitor/performance/equity").json()
    assert body["data"] == rows
    assert body["meta"]["data_source"] == "timescaledb"
    assert body["meta"]["total"] == 1


def test_perf_equity_falls_back_to_pending_without_db():
    body = _client(_FakeReader(fail=True)).get("/monitor/performance/equity").json()
    assert body["data"] == []
    assert body["meta"]["data_source"] == "pending_m4"


def test_pos_snapshot_serves_open_positions():
    pos = [{
        "stock_id": "2330", "quantity": 100, "entry_price": 600.0,
        "stop_loss": 576.0, "opened_at": "2023-01-03T00:00:00", "strategy_id": "inst_flow",
    }]
    body = _client(_FakeReader(positions=pos)).get("/monitor/positions/snapshot").json()
    assert body["data"] == pos
    assert body["meta"]["data_source"] == "timescaledb"
    assert body["meta"]["total"] == 1


def test_pos_snapshot_falls_back_to_pending_without_db():
    body = _client(_FakeReader(fail=True)).get("/monitor/positions/snapshot").json()
    assert body["data"] == []
    assert body["meta"]["data_source"] == "pending_m4"


def test_signals_serves_real_telemetry():
    sig = [{
        "signal_time": "2023-01-03T00:00:00", "strategy_id": "inst_flow",
        "stock_id": "2330", "action": "buy", "priority": 2, "submitted": True,
    }]
    body = _client(_FakeReader(signals=sig)).get("/monitor/signals").json()
    assert body["data"] == sig
    assert body["meta"]["data_source"] == "timescaledb"
    assert body["meta"]["total"] == 1


def test_fills_serves_real_telemetry():
    fills = [{
        "created_at": "2023-01-03T00:00:00", "stock_id": "2330", "side": "Buy",
        "quantity": 100, "price": 600.0, "status": "FILLED",
    }]
    body = _client(_FakeReader(fills=fills)).get("/monitor/fills").json()
    assert body["data"] == fills
    assert body["meta"]["data_source"] == "timescaledb"


@pytest.mark.parametrize("path", ["/monitor/signals", "/monitor/fills"])
def test_signals_fills_fall_back_to_pending_without_db(path):
    body = _client(_FakeReader(fail=True)).get(path).json()
    assert body["data"] == []
    assert body["meta"]["data_source"] == "pending_m4"


@pytest.mark.parametrize(
    "path",
    ["/monitor/performance/equity", "/monitor/positions/snapshot", "/monitor/signals", "/monitor/fills"],
)
def test_telemetry_endpoints_envelope_shape(path):
    body = _client(_FakeReader()).get(path).json()
    assert body["success"] is True
    assert body["data"] == []  # empty telemetry → empty list, still 200
