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
    def __init__(self, *, equity=None, positions=None, signals=None, fills=None, fleet=None, fail=False):
        self._equity = equity or []
        self._positions = positions or []
        self._signals = signals or []
        self._fills = fills or []
        self._fleet = fleet or []
        self._fail = fail

    def fleet_summary(self, **_kw):
        if self._fail:
            raise RuntimeError("no DB connection")
        return self._fleet

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


def test_perf_kpi_computes_from_equity():
    eq = [
        {"t": f"2023-01-{d:02d}T00:00:00", "equity": v, "drawdown": 0.0}
        for d, v in [(3, 10_000_000.0), (4, 10_100_000.0), (5, 10_050_000.0), (6, 10_200_000.0)]
    ]
    body = _client(_FakeReader(equity=eq)).get("/monitor/performance/kpi").json()
    d = body["data"]
    assert body["meta"]["data_source"] == "timescaledb"
    assert d["current_equity"] == 10_200_000.0
    assert d["n_points"] == 4
    assert d["total_return"] == pytest.approx((10_200_000.0 / 10_000_000.0) - 1, rel=1e-6)
    for k in ("cagr", "sharpe", "max_drawdown", "calmar"):
        assert k in d


def test_perf_kpi_short_series_returns_zeros():
    eq = [{"t": "2023-01-03T00:00:00", "equity": 10_000_000.0, "drawdown": 0.0}]
    d = _client(_FakeReader(equity=eq)).get("/monitor/performance/kpi").json()["data"]
    assert d["current_equity"] == 10_000_000.0
    assert d["cagr"] == 0.0 and d["n_points"] == 1


def test_perf_kpi_pending_without_db():
    body = _client(_FakeReader(fail=True)).get("/monitor/performance/kpi").json()
    assert body["meta"]["data_source"] == "pending_m4"
    assert body["data"] == {}


# ---- fleet aggregate (8.H.8) --------------------------------------------

_FLEET = [
    {"strategy_id": "inst_flow", "equity": 10_130_000.0, "cash": 8_600_000.0, "open_positions": 3, "portfolio_heat": 0.12, "last_update": "2023-10-02T00:00:00"},
    {"strategy_id": "momentum", "equity": 9_800_000.0, "cash": 9_000_000.0, "open_positions": 2, "portfolio_heat": 0.08, "last_update": "2023-10-02T00:00:00"},
]


def test_fleet_serves_latest_per_strategy():
    body = _client(_FakeReader(fleet=_FLEET)).get("/monitor/fleet").json()
    assert body["meta"]["data_source"] == "timescaledb"
    assert {r["strategy_id"] for r in body["data"]} == {"inst_flow", "momentum"}
    assert body["meta"]["total"] == 2


def test_portfolio_summary_rolls_up_fleet():
    data = _client(_FakeReader(fleet=_FLEET)).get("/monitor/portfolio-summary").json()["data"]
    assert data["n_strategies"] == 2
    assert data["total_equity"] == 19_930_000.0
    assert data["total_open_positions"] == 5


def test_fleet_pending_without_db():
    body = _client(_FakeReader(fail=True)).get("/monitor/fleet").json()
    assert body["data"] == []
    assert body["meta"]["data_source"] == "pending_m4"


def test_strategies_lists_registry_catalog():
    # registry is populated by best-effort runner import → real production strategies
    body = _client(_FakeReader()).get("/monitor/strategies").json()
    names = {r["strategy_id"] for r in body["data"]}
    assert "inst_flow" in names  # registered via @register_strategy


# ---------------------------------------------------------------------------
# A2 — /monitor/board: run board from the runs table (lifecycle + verdict)
# ---------------------------------------------------------------------------
class _BoardReader:
    def __init__(self, rows=None, fail=False):
        self._rows = rows or []
        self._fail = fail
        self.seen_limit = None

    def runs_board(self, *, limit=50):
        if self._fail:
            raise RuntimeError("no DB connection")
        self.seen_limit = limit
        return self._rows


def _board_client(reader) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_telemetry_reader] = lambda: reader
    return TestClient(app)


def test_board_serves_runs_rows() -> None:
    rows = [{
        "run_id": "a1b2c3d4e5f6", "strategy": "inst_flow", "engine": "sim",
        "stocks": ["2330", "2317"], "is_start": "2026-01-05", "is_end": "2026-04-10",
        "status": "done", "gate_status": "PASS", "gate_summary": "IS gate: 4/4",
        "metrics": {"sharpe": 1.1}, "created_at": "2026-07-02T12:00:00+00:00",
    }]
    res = _board_client(_BoardReader(rows=rows)).get("/monitor/board")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"] == rows
    assert body["meta"]["total"] == 1
    assert body["meta"]["data_source"] != "pending"


def test_board_degrades_to_pending_without_db() -> None:
    res = _board_client(_BoardReader(fail=True)).get("/monitor/board")
    assert res.status_code == 200
    body = res.json()
    assert body["data"] == []
    assert body["meta"]["data_source"].startswith("pending")  # _PENDING marker


def test_board_passes_limit_and_validates() -> None:
    reader = _BoardReader(rows=[])
    client = _board_client(reader)
    assert client.get("/monitor/board?limit=7").status_code == 200
    assert reader.seen_limit == 7
    assert client.get("/monitor/board?limit=0").status_code == 422
