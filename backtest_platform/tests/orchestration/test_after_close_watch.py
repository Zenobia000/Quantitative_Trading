"""After-close × Paper-Watch enforcement (ADR-033) + no-data degrade tests.

The registry read (``watch_status``) and the expiry hook (``expire_watches``) are
injected seams, so these tests wire tiny stubs — no JSONL, no calendar, no network.
They pin: a strategy not holding an active berth is refused (the machine
enforcement of "who may run paper"), an expired berth is refused, a no-data day is
a benign skip (INFO, not a FAILED alert), and the Discord digest carries the
observation-day line + the maturity notice on the expiry crossing.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from backtest_platform.orchestration.after_close import (
    AfterCloseStatus,
    run_after_close,
)
from backtest_platform.research.watch_registry import OBSERVATION_DAYS, WatchStatus

_TWT = timezone(timedelta(hours=8))
_STRATEGY = "inst_flow"


def _after_close_now() -> datetime:
    return datetime(2026, 7, 2, 15, 0, tzinfo=_TWT)


def _active_status(strategy: str, as_of: date) -> WatchStatus:
    on = date(2026, 6, 1)
    return WatchStatus(
        strategy=strategy, state="active", enrolled_on=on, verdict_dsr=0.908,
        expiry_date=on + timedelta(days=OBSERVATION_DAYS),
        observed_trading_days=22, days_remaining=59,
    )


class _RecordingRunner:
    def __init__(self, ok: bool = True) -> None:
        self.calls: list[tuple[str, date]] = []
        self._ok = ok

    def __call__(self, strategy: str, as_of: date):
        self.calls.append((strategy, as_of))

        class _S:
            ok = self._ok

            def summary(self_inner) -> str:  # noqa: N805
                return "REPLAY: 1/1 sessions green" if self._ok else "REPLAY: 0/1"

        return _S()


class _Notifier:
    def __init__(self) -> None:
        self.messages: list[tuple[str, bool]] = []

    def __call__(self, message: str, ok: bool) -> None:
        self.messages.append((message, ok))


def _common(tmp_path, **over):
    base = dict(
        now=_after_close_now(),
        is_trading_day=lambda d: True,
        watch_status=_active_status,
        expire_watches=lambda d: [],
        notifier=_Notifier(),
        marker_path=tmp_path / "markers.jsonl",
    )
    base.update(over)
    return base


# --------------------------------------------------------------------------- #
# enforcement — a strategy with no active berth is refused (never runs)        #
# --------------------------------------------------------------------------- #
def test_not_enrolled_strategy_is_refused_without_running(tmp_path):
    runner = _RecordingRunner()
    res = run_after_close(
        _STRATEGY, date(2026, 7, 2),
        session_runner=runner,
        **_common(tmp_path, watch_status=lambda s, d: None),  # not in registry
    )
    assert res.status is AfterCloseStatus.NOT_ENROLLED
    assert res.exit_code == 1
    assert runner.calls == []  # the flow is never triggered
    assert "enroll" in res.message.lower()


def test_expired_watch_is_refused_with_reeval_hint(tmp_path):
    runner = _RecordingRunner()
    expired = WatchStatus(
        strategy=_STRATEGY, state="expired", enrolled_on=date(2026, 4, 1),
        verdict_dsr=0.908, expiry_date=date(2026, 6, 30),
        observed_trading_days=60, days_remaining=-2,
    )
    res = run_after_close(
        _STRATEGY, date(2026, 7, 2),
        session_runner=runner,
        **_common(tmp_path, watch_status=lambda s, d: expired),
    )
    assert res.status is AfterCloseStatus.WATCH_EXPIRED
    assert res.exit_code == 1
    assert runner.calls == []
    assert "重評" in res.message or "re-eval" in res.message.lower()


def test_active_watch_is_allowed_to_run(tmp_path):
    runner = _RecordingRunner(ok=True)
    res = run_after_close(
        _STRATEGY, date(2026, 7, 2),
        session_runner=runner,
        **_common(tmp_path),
    )
    assert res.status is AfterCloseStatus.SUCCESS
    assert runner.calls == [(_STRATEGY, date(2026, 7, 2))]


def test_paused_watch_is_skipped_benignly_without_running_or_discord(tmp_path):
    # An app-level pause (GUI / `watch pause`) means "stop collecting OOS for now"
    # without exiting the berth. After-close must SKIP it: benign exit 0 (like a
    # non-trading day), the daily flow never fires, and — crucially — NO Discord is
    # pushed (a paused berth every day would be pure noise; a log line suffices).
    runner = _RecordingRunner(ok=True)
    paused = WatchStatus(
        strategy=_STRATEGY, state="paused", enrolled_on=date(2026, 6, 1),
        verdict_dsr=0.908, expiry_date=date(2026, 8, 30),
        observed_trading_days=22, days_remaining=59,
    )
    notifier = _Notifier()
    res = run_after_close(
        _STRATEGY, date(2026, 7, 2),
        session_runner=runner,
        **_common(tmp_path, watch_status=lambda s, d: paused, notifier=notifier),
    )
    assert res.status is AfterCloseStatus.PAUSED
    assert res.exit_code == 0  # a paused berth is a benign skip, not a failure
    assert runner.calls == []  # the flow never fired
    assert notifier.messages == []  # no Discord noise for a paused berth
    assert not (tmp_path / "markers.jsonl").exists()  # nothing ran → no marker


# --------------------------------------------------------------------------- #
# no-data degrade — calendar says trading day but the source has no as-of row  #
# --------------------------------------------------------------------------- #
def test_no_data_day_is_benign_skip_not_failure(tmp_path):
    from backtest_platform.runtime.market_data_errors import NoMarketDataError

    def _no_data_runner(strategy: str, as_of: date):
        raise NoMarketDataError(strategy, as_of, "latest panel row 2026-07-01 < as_of")

    notifier = _Notifier()
    res = run_after_close(
        _STRATEGY, date(2026, 7, 2),
        session_runner=_no_data_runner,
        **_common(tmp_path, notifier=notifier),
    )
    assert res.status is AfterCloseStatus.NO_DATA
    assert res.exit_code == 0  # a holiday false-positive is NOT a failure
    # notified as INFO (ok=True), never as an ERROR alert
    assert notifier.messages and notifier.messages[-1][1] is True
    assert not any(ok is False for _msg, ok in notifier.messages)
    # a no-data skip writes no success marker (nothing actually ran)
    assert not (tmp_path / "markers.jsonl").exists()


def test_genuine_runner_failure_still_fails_and_alerts(tmp_path):
    def _boom(strategy: str, as_of: date):
        raise RuntimeError("finlab quota exhausted")

    notifier = _Notifier()
    res = run_after_close(
        _STRATEGY, date(2026, 7, 2),
        session_runner=_boom,
        **_common(tmp_path, notifier=notifier),
    )
    assert res.status is AfterCloseStatus.FAILED
    assert res.exit_code == 1
    assert notifier.messages[-1][1] is False  # ERROR alert


# --------------------------------------------------------------------------- #
# Discord digest — observation-day line + maturity notice on expiry crossing   #
# --------------------------------------------------------------------------- #
def test_success_digest_carries_observation_day_line(tmp_path):
    notifier = _Notifier()
    res = run_after_close(
        _STRATEGY, date(2026, 7, 2),
        session_runner=_RecordingRunner(ok=True),
        **_common(tmp_path, notifier=notifier),
    )
    assert res.status is AfterCloseStatus.SUCCESS
    ok_msg = next(m for m, ok in notifier.messages if ok)
    assert "觀察日" in ok_msg and "22" in ok_msg  # observed_trading_days surfaced


# --------------------------------------------------------------------------- #
# end-to-end — the real registry ↔ scheduler wiring (no watch_status stub)      #
# --------------------------------------------------------------------------- #
def test_enroll_then_after_close_admits_via_real_registry(tmp_path):
    from backtest_platform.research.watch_registry import enroll, status

    reg = tmp_path / "watch.jsonl"
    on = date(2026, 7, 2)
    enroll("inst_flow", 0.908, on, is_trading_day=lambda d: True, path=reg)

    def _read(strategy: str, as_of: date):
        return status(strategy, as_of=as_of, is_trading_day=lambda d: True, path=reg)

    # enrolled strategy → admitted → runs
    runner = _RecordingRunner(ok=True)
    admitted = run_after_close(
        "inst_flow", on, session_runner=runner,
        **_common(tmp_path, watch_status=_read),
    )
    assert admitted.status is AfterCloseStatus.SUCCESS
    assert runner.calls == [("inst_flow", on)]

    # a strategy never enrolled into the SAME registry → refused, never runs
    other = _RecordingRunner()
    refused = run_after_close(
        "never_enrolled", on, session_runner=other,
        **_common(tmp_path, watch_status=_read),
    )
    assert refused.status is AfterCloseStatus.NOT_ENROLLED
    assert other.calls == []


def test_expiry_crossing_pushes_maturity_notice(tmp_path):
    notifier = _Notifier()
    res = run_after_close(
        _STRATEGY, date(2026, 7, 2),
        session_runner=_RecordingRunner(ok=True),
        **_common(tmp_path, notifier=notifier, expire_watches=lambda d: [_STRATEGY]),
    )
    assert res.status is AfterCloseStatus.SUCCESS
    joined = "\n".join(m for m, _ok in notifier.messages)
    assert "觀察期滿" in joined  # maturity notice fired once on the crossing
    # the maturity notice is INFO (ok=True), never an error alert
    assert all(ok is True for _m, ok in notifier.messages)
