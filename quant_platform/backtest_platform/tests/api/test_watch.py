"""``/monitor/watch`` — Paper-Watch 觀察艙 overview + app-level pause/resume.

The觀察艙 registry read helpers (``all_watches`` / ``status``) and the after-close
marker store are path-injectable, and the clock / calendar are injected deps, so
these tests run with a tmp JSONL pair and a fixed ``as_of`` + weekday calendar — no
real date, no calendar extra, no DB. They pin the overview shape (status / observed
days / expiry / DSR + timer health + session timeline) and the pause/resume
round-trip the GUI drives.
"""
from __future__ import annotations

import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

from backtest_platform.api.app import create_app
from backtest_platform.api.deps import (
    get_after_close_marker_path,
    get_watch_registry_path,
    get_watch_today,
    get_watch_trading_day_fn,
)

_TODAY = date(2026, 7, 6)  # a Monday


def _weekday(d: date) -> bool:
    return d.weekday() < 5


def _write(path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _enroll_event(strategy: str, on: date, dsr: float = 0.908) -> dict:
    return {"strategy": strategy, "event": "enroll", "verdict_dsr": dsr,
            "enrolled_on": on.isoformat(), "re_enroll_evidence": None,
            "at": f"{on.isoformat()}T09:00:00+08:00"}


def _marker(strategy: str, d: date, *, ok: bool = True) -> dict:
    return {"key": f"{strategy}@{d.isoformat()}", "strategy": strategy,
            "date": d.isoformat(), "ok": ok, "detail": "REPLAY: 1/1 green",
            "recorded_at": f"{d.isoformat()}T14:32:05+08:00"}


def _client(tmp_path, *, watch_events=None, markers=None, today=_TODAY) -> TestClient:
    reg = tmp_path / "watch.jsonl"
    mp = tmp_path / "markers.jsonl"
    _write(reg, watch_events or [])
    _write(mp, markers or [])
    app = create_app()
    app.dependency_overrides[get_watch_registry_path] = lambda: reg
    app.dependency_overrides[get_after_close_marker_path] = lambda: mp
    app.dependency_overrides[get_watch_today] = lambda: today
    app.dependency_overrides[get_watch_trading_day_fn] = lambda: _weekday
    return TestClient(app)


# --------------------------------------------------------------------------- #
# GET /monitor/watch — overview envelope                                       #
# --------------------------------------------------------------------------- #
def test_overview_lists_active_berth_with_derived_fields(tmp_path):
    on = date(2026, 6, 1)
    client = _client(
        tmp_path,
        watch_events=[_enroll_event("inst_flow", on)],
        markers=[_marker("inst_flow", date(2026, 7, 3))],  # last Friday
    )
    body = client.get("/monitor/watch").json()
    assert body["success"] is True
    assert body["meta"]["data_source"] == "watch_registry"
    rows = body["data"]
    assert len(rows) == 1
    row = rows[0]
    assert row["strategy"] == "inst_flow"
    assert row["status"] == "active"
    assert row["enrolled_on"] == "2026-06-01"
    assert row["verdict_dsr"] == pytest.approx(0.908)
    assert row["nominal_trading_days"] == 60
    assert row["observed_trading_days"] > 0
    assert row["expiry_date"] == "2026-08-30"  # on + 90 days
    assert row["timer_health"] == "ok"
    assert row["last_session_date"] == "2026-07-03"
    assert [s["date"] for s in row["sessions"]] == ["2026-07-03"]
    assert row["sessions"][0]["status"] == "OK"


def test_overview_timer_health_never_ran_without_markers(tmp_path):
    client = _client(tmp_path, watch_events=[_enroll_event("inst_flow", date(2026, 7, 2))])
    row = client.get("/monitor/watch").json()["data"][0]
    assert row["timer_health"] == "never_ran"
    assert row["last_session_date"] is None
    assert row["sessions"] == []


def test_overview_timer_health_stale_when_marker_lags(tmp_path):
    client = _client(
        tmp_path,
        watch_events=[_enroll_event("inst_flow", date(2026, 6, 1))],
        markers=[_marker("inst_flow", date(2026, 7, 2))],  # Thu, but Fri also closed
    )
    row = client.get("/monitor/watch").json()["data"][0]
    assert row["timer_health"] == "stale"
    assert row["last_trading_day"] == "2026-07-03"


def test_overview_surfaces_paused_berth(tmp_path):
    on = date(2026, 6, 1)
    client = _client(tmp_path, watch_events=[
        _enroll_event("inst_flow", on),
        {"strategy": "inst_flow", "event": "pause", "at": "2026-07-01T10:00:00+08:00"},
    ])
    row = client.get("/monitor/watch").json()["data"][0]
    assert row["status"] == "paused"


def test_overview_empty_when_no_berths(tmp_path):
    body = _client(tmp_path).get("/monitor/watch").json()
    assert body["success"] is True
    assert body["data"] == []
    assert body["meta"]["total"] == 0


# --------------------------------------------------------------------------- #
# POST pause / resume — app-level toggle round-trip                            #
# --------------------------------------------------------------------------- #
def test_pause_then_resume_round_trip(tmp_path):
    on = date(2026, 6, 1)
    client = _client(tmp_path, watch_events=[_enroll_event("inst_flow", on)])

    paused = client.post("/monitor/watch/inst_flow/pause").json()
    assert paused["success"] is True
    assert paused["data"]["status"] == "paused"
    assert client.get("/monitor/watch").json()["data"][0]["status"] == "paused"

    resumed = client.post("/monitor/watch/inst_flow/resume").json()
    assert resumed["data"]["status"] == "active"
    assert client.get("/monitor/watch").json()["data"][0]["status"] == "active"


def test_pause_unknown_strategy_is_a_client_error(tmp_path):
    client = _client(tmp_path)
    res = client.post("/monitor/watch/never_enrolled/pause")
    assert res.status_code == 400
    body = res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "BAD_REQUEST"


def test_pause_is_idempotent_over_http(tmp_path):
    client = _client(tmp_path, watch_events=[_enroll_event("inst_flow", date(2026, 6, 1))])
    client.post("/monitor/watch/inst_flow/pause")
    again = client.post("/monitor/watch/inst_flow/pause").json()
    assert again["success"] is True
    assert again["data"]["status"] == "paused"
