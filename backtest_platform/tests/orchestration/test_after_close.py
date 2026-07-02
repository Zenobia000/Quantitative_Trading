"""Tests for the after-close scheduler orchestration core.

Every seam (clock / trading-day calendar / session runner / Discord notifier /
done-marker path) is injected, so these tests touch no real time, no network, no
DB. They pin the five guard behaviours the scheduler must honour plus the
success / failure exit-code contract.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

import pytest

from backtest_platform.orchestration.after_close import (
    AfterCloseStatus,
    already_done,
    build_session_runner,
    record_done,
    run_after_close,
    safe_discord_notify,
)
from backtest_platform.orchestration.after_close import (
    _build_broker,
    _resolve_equity,
    _resolve_universe,
)

_TWT = timezone(timedelta(hours=8))
_STRATEGY = "inst_flow"


def _active_watch(_strategy: str, _as_of: date):
    """Stub觀察艙 read: an active berth so the ADR-033 enrollment gate admits the run.

    These tests pre-date the enrollment gate and exercise the OTHER guards
    (trading-day / after-close time / idempotency / failure); an active berth keeps
    them focused on the guard under test. Enrollment enforcement is pinned
    separately in ``test_after_close_watch.py``."""
    from datetime import date as _d

    from backtest_platform.research.watch_registry import OBSERVATION_DAYS, WatchStatus

    on = _d(2026, 6, 1)
    return WatchStatus(
        strategy=_strategy, state="active", enrolled_on=on, verdict_dsr=0.908,
        expiry_date=on + timedelta(days=OBSERVATION_DAYS),
        observed_trading_days=22, days_remaining=59,
    )


def _no_expiry(_as_of: date) -> list[str]:
    return []


class _FakeSummary:
    """Duck-types runtime.paper_daemon.ReplaySummary (only .ok + .summary())."""

    def __init__(self, ok: bool) -> None:
        self._ok = ok

    @property
    def ok(self) -> bool:
        return self._ok

    def summary(self) -> str:
        return f"REPLAY: {'1/1' if self._ok else '0/1'} sessions green"


class _RecordingRunner:
    """Session runner spy: records (strategy, date) calls, returns a fixed outcome."""

    def __init__(self, ok: bool = True) -> None:
        self.calls: list[tuple[str, date]] = []
        self._ok = ok

    def __call__(self, strategy: str, as_of: date) -> _FakeSummary:
        self.calls.append((strategy, as_of))
        return _FakeSummary(self._ok)


class _RecordingNotifier:
    def __init__(self) -> None:
        self.messages: list[tuple[str, bool]] = []

    def __call__(self, message: str, ok: bool) -> None:
        self.messages.append((message, ok))


def _after_close_now() -> datetime:
    return datetime(2026, 7, 2, 15, 0, tzinfo=_TWT)  # Thu 15:00, past close


# --------------------------------------------------------------------------- #
# (a) non-trading day → skip, no flow                                          #
# --------------------------------------------------------------------------- #
def test_non_trading_day_skips_without_running_flow(tmp_path):
    runner = _RecordingRunner()
    res = run_after_close(
        _STRATEGY, date(2026, 7, 4),  # Saturday
        now=_after_close_now(),
        is_trading_day=lambda d: False,
        session_runner=runner,
        notifier=_RecordingNotifier(),
        marker_path=tmp_path / "markers.jsonl",
    )
    assert res.status is AfterCloseStatus.NON_TRADING_DAY
    assert res.exit_code == 0
    assert runner.calls == []  # flow never triggered


# --------------------------------------------------------------------------- #
# (b) before close (no --force) → refuse, no flow                             #
# --------------------------------------------------------------------------- #
def test_before_close_refuses_without_force(tmp_path):
    runner = _RecordingRunner()
    res = run_after_close(
        _STRATEGY, date(2026, 7, 2),
        now=datetime(2026, 7, 2, 10, 0, tzinfo=_TWT),  # 10:00, before 14:30
        is_trading_day=lambda d: True,
        session_runner=runner,
        notifier=_RecordingNotifier(),
        marker_path=tmp_path / "markers.jsonl",
    )
    assert res.status is AfterCloseStatus.TOO_EARLY
    assert res.exit_code == 0
    assert runner.calls == []


def test_before_close_runs_with_force(tmp_path):
    runner = _RecordingRunner()
    res = run_after_close(
        _STRATEGY, date(2026, 7, 2),
        now=datetime(2026, 7, 2, 10, 0, tzinfo=_TWT),
        force=True,
        is_trading_day=lambda d: True,
        session_runner=runner,
        notifier=_RecordingNotifier(),
        marker_path=tmp_path / "markers.jsonl",
        watch_status=_active_watch,
        expire_watches=_no_expiry,
    )
    assert res.status is AfterCloseStatus.SUCCESS
    assert runner.calls == [(_STRATEGY, date(2026, 7, 2))]


def test_past_date_is_after_close_regardless_of_time(tmp_path):
    # Back-fill of an earlier session: the time gate is trivially satisfied.
    runner = _RecordingRunner()
    res = run_after_close(
        _STRATEGY, date(2026, 6, 30),
        now=datetime(2026, 7, 2, 9, 0, tzinfo=_TWT),  # early morning, later day
        is_trading_day=lambda d: True,
        session_runner=runner,
        notifier=_RecordingNotifier(),
        marker_path=tmp_path / "markers.jsonl",
        watch_status=_active_watch,
        expire_watches=_no_expiry,
    )
    assert res.status is AfterCloseStatus.SUCCESS
    assert runner.calls == [(_STRATEGY, date(2026, 6, 30))]


# --------------------------------------------------------------------------- #
# (c) idempotency — same (strategy, date) twice → second is skipped           #
# --------------------------------------------------------------------------- #
def test_idempotent_second_run_same_day_skips(tmp_path):
    marker = tmp_path / "markers.jsonl"
    runner = _RecordingRunner()
    common = dict(
        now=_after_close_now(),
        is_trading_day=lambda d: True,
        session_runner=runner,
        notifier=_RecordingNotifier(),
        marker_path=marker,
        watch_status=_active_watch,
        expire_watches=_no_expiry,
    )
    first = run_after_close(_STRATEGY, date(2026, 7, 2), **common)
    second = run_after_close(_STRATEGY, date(2026, 7, 2), **common)
    assert first.status is AfterCloseStatus.SUCCESS
    assert second.status is AfterCloseStatus.ALREADY_DONE
    assert second.exit_code == 0
    assert runner.calls == [(_STRATEGY, date(2026, 7, 2))]  # ran exactly once


# --------------------------------------------------------------------------- #
# (d) dry-run → guards pass but the daily flow is NOT triggered                #
# --------------------------------------------------------------------------- #
def test_dry_run_does_not_trigger_flow_or_marker(tmp_path):
    marker = tmp_path / "markers.jsonl"
    runner = _RecordingRunner()
    res = run_after_close(
        _STRATEGY, date(2026, 7, 2),
        dry_run=True,
        now=_after_close_now(),
        is_trading_day=lambda d: True,
        session_runner=runner,
        notifier=_RecordingNotifier(),
        marker_path=marker,
        watch_status=_active_watch,
        expire_watches=_no_expiry,
    )
    assert res.status is AfterCloseStatus.DRY_RUN
    assert res.exit_code == 0
    assert runner.calls == []          # flow not triggered
    assert not marker.exists()          # dry-run writes no done-marker


# --------------------------------------------------------------------------- #
# (e) Discord notify failure (e.g. missing token) must not crash the run      #
# --------------------------------------------------------------------------- #
def test_notify_failure_does_not_crash_run(tmp_path):
    def _raising_notifier(_message: str, _ok: bool) -> None:
        raise RuntimeError("DISCORD_BOT_TOKEN is empty")

    res = run_after_close(
        _STRATEGY, date(2026, 7, 2),
        now=_after_close_now(),
        is_trading_day=lambda d: True,
        session_runner=_RecordingRunner(ok=True),
        notifier=_raising_notifier,
        marker_path=tmp_path / "markers.jsonl",
        watch_status=_active_watch,
        expire_watches=_no_expiry,
    )
    assert res.status is AfterCloseStatus.SUCCESS  # run succeeded despite notify blow-up


def test_safe_discord_notify_swallows_missing_token(monkeypatch):
    # No DISCORD_BOT_TOKEN in env → the real notifier raises ValueError; the safe
    # wrapper must log and return without raising.
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
    safe_discord_notify("after-close test", ok=True)  # must not raise


# --------------------------------------------------------------------------- #
# failure contract — daily flow fails → non-zero exit + error notification    #
# --------------------------------------------------------------------------- #
def test_failed_session_exits_nonzero_and_alerts(tmp_path):
    notifier = _RecordingNotifier()
    res = run_after_close(
        _STRATEGY, date(2026, 7, 2),
        now=_after_close_now(),
        is_trading_day=lambda d: True,
        session_runner=_RecordingRunner(ok=False),  # chain failed
        notifier=notifier,
        marker_path=tmp_path / "markers.jsonl",
        watch_status=_active_watch,
        expire_watches=_no_expiry,
    )
    assert res.status is AfterCloseStatus.FAILED
    assert res.exit_code == 1
    assert notifier.messages and notifier.messages[-1][1] is False  # error alert sent


def test_raising_session_runner_is_reported_as_failure(tmp_path):
    def _boom(_strategy: str, _as_of: date):
        raise RuntimeError("finlab quota exhausted")

    notifier = _RecordingNotifier()
    res = run_after_close(
        _STRATEGY, date(2026, 7, 2),
        now=_after_close_now(),
        is_trading_day=lambda d: True,
        session_runner=_boom,
        notifier=notifier,
        marker_path=tmp_path / "markers.jsonl",
        watch_status=_active_watch,
        expire_watches=_no_expiry,
    )
    assert res.status is AfterCloseStatus.FAILED
    assert res.exit_code == 1
    assert "finlab quota exhausted" in res.message
    assert notifier.messages[-1][1] is False


def test_failed_run_is_retryable_not_blocked_by_idempotency(tmp_path):
    # A failed session must NOT write a success marker, so a retry actually reruns.
    marker = tmp_path / "markers.jsonl"
    first = run_after_close(
        _STRATEGY, date(2026, 7, 2),
        now=_after_close_now(), is_trading_day=lambda d: True,
        session_runner=_RecordingRunner(ok=False),
        notifier=_RecordingNotifier(), marker_path=marker,
        watch_status=_active_watch, expire_watches=_no_expiry,
    )
    assert first.status is AfterCloseStatus.FAILED
    assert already_done(_STRATEGY, date(2026, 7, 2), path=marker) is False


# --------------------------------------------------------------------------- #
# done-marker store unit behaviour                                            #
# --------------------------------------------------------------------------- #
def test_marker_store_roundtrip(tmp_path):
    marker = tmp_path / "markers.jsonl"
    assert already_done(_STRATEGY, date(2026, 7, 2), path=marker) is False
    record_done(_STRATEGY, date(2026, 7, 2), ok=True, detail="ok", path=marker)
    assert already_done(_STRATEGY, date(2026, 7, 2), path=marker) is True
    # a different date is independent
    assert already_done(_STRATEGY, date(2026, 7, 3), path=marker) is False
    # the record is valid JSON with the key fields
    rec = json.loads(marker.read_text(encoding="utf-8").splitlines()[0])
    assert rec["strategy"] == _STRATEGY and rec["date"] == "2026-07-02" and rec["ok"] is True


# --------------------------------------------------------------------------- #
# production wiring — resolvers + fail-loud guards (no finlab/DB touched)      #
# --------------------------------------------------------------------------- #
def test_resolve_universe_from_arg_and_env(monkeypatch):
    assert _resolve_universe("2330, 2317 ,2454") == ["2330", "2317", "2454"]
    monkeypatch.setenv("AFTER_CLOSE_UNIVERSE", "1101,1102")
    assert _resolve_universe(None) == ["1101", "1102"]


def test_resolve_universe_empty_fails_loud(monkeypatch):
    monkeypatch.delenv("AFTER_CLOSE_UNIVERSE", raising=False)
    with pytest.raises(ValueError, match="no universe configured"):
        _resolve_universe(None)


def test_resolve_equity_arg_env_default(monkeypatch):
    assert _resolve_equity(5_000_000.0) == 5_000_000.0
    monkeypatch.setenv("AFTER_CLOSE_EQUITY", "3000000")
    assert _resolve_equity(None) == 3_000_000.0
    monkeypatch.delenv("AFTER_CLOSE_EQUITY", raising=False)
    assert _resolve_equity(None) == 10_000_000.0  # documented default


def test_build_session_runner_rejects_unknown_strategy():
    with pytest.raises(ValueError, match="only wires 'inst_flow'"):
        build_session_runner("bogus", "2330", None)


def test_build_session_runner_inst_flow_returns_callable_without_touching_finlab():
    # Assembling the runner binds the live-panel path but does NOT read a panel or
    # the DB (both are only hit when the returned callable is invoked per session).
    runner = build_session_runner("inst_flow", "2330,2317", 1_000_000.0)
    assert callable(runner)


# --------------------------------------------------------------------------- #
# _build_broker — cross-day position restore wiring (the PR #151 limitation)   #
# --------------------------------------------------------------------------- #
def test_build_broker_seeds_from_restored_state():
    """(a) telemetry present → broker rehydrated with the persisted cash + book."""
    from backtest_platform.data.db_reader import BrokerState, PositionState

    def loader(_strategy):
        return BrokerState(cash=850_000.0, positions={"2330": PositionState(1_000, 500.0)})

    br = _build_broker("inst_flow", 10_000_000.0, state_loader=loader)
    assert br.cash == 850_000.0
    assert br.positions["2330"].qty == 1_000
    assert br.positions["2330"].cost_basis == 500.0


def test_build_broker_first_day_none_is_fresh():
    """(b) first session (loader → None) → a fresh broker at the configured cash."""
    br = _build_broker("inst_flow", 10_000_000.0, state_loader=lambda _s: None)
    assert br.cash == 10_000_000.0
    assert br.positions == {}


def test_build_broker_db_error_propagates_never_silent_empty():
    """(c) a DB failure fails loud (propagates) — never a silent empty book."""
    def loader(_strategy):
        raise RuntimeError("db down")

    with pytest.raises(RuntimeError, match="db down"):
        _build_broker("inst_flow", 10_000_000.0, state_loader=loader)


def test_build_broker_fresh_flag_skips_restore():
    """(d) --fresh → skip restore entirely; the loader is never consulted."""
    def loader(_strategy):
        raise AssertionError("state_loader must not be called when fresh=True")

    br = _build_broker("inst_flow", 10_000_000.0, fresh=True, state_loader=loader)
    assert br.cash == 10_000_000.0
    assert br.positions == {}


def test_restored_broker_positions_are_seen_by_risk_gate():
    """(e) integration: a restored position makes EX-002 reject an over-concentrating
    buy that a fresh (empty) broker would have approved — the whole point of the fix."""
    from backtest_platform.data.db_reader import BrokerState, PositionState
    from backtest_platform.orchestration.collaborators import make_risk_check

    # Restored: 2330 already ~6.5% of equity, so a +100k buy tips it over the 8% cap.
    def loader(_strategy):
        return BrokerState(cash=2_900_000.0, positions={"2330": PositionState(2_000, 100.0)})

    restored = _build_broker("inst_flow", 10_000_000.0, state_loader=loader)
    fresh = _build_broker("inst_flow", 3_000_000.0, state_loader=lambda _s: None)

    signal = {
        "stock_id": "2330", "side": "buy", "qty": 1_000, "price": 100.0,
        "stop_loss": 95.0, "prev_close": 100.0, "avg_volume_20d": 10_000_000.0,
        "industry": "semi",
    }
    ok_fresh, _ = make_risk_check(fresh)([signal])
    ok_restored, why = make_risk_check(restored)([signal])

    assert ok_fresh is True  # empty book: the buy is only 3.3% of equity → allowed
    assert ok_restored is False  # restored 2330 (200k) + 100k = ~9.7% → EX-002 rejects
    assert "2330" in why
