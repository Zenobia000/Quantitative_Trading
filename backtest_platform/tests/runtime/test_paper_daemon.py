"""paper_daemon (8.H.8) replay core — per-date chain execution + cross-date resilience."""
from __future__ import annotations

from datetime import date

import pandas as pd

from backtest_platform.orchestration.daily_flow import FlowContext, StageResult
from backtest_platform.runtime.paper_daemon import (
    ReplaySummary,
    replay_schedule,
    run_paper_replay,
)

_DATES = [date(2023, 1, 3), date(2023, 4, 3), date(2023, 7, 3)]


def _ok_stage(name: str):
    def stage(ctx: FlowContext) -> StageResult:
        return StageResult(name, ok=True, detail="ok", output=ctx.config.get("as_of"))
    return stage


def _gated_stage(name: str):
    """Fails only when the day's config says so — models a bad session."""
    def stage(ctx: FlowContext) -> StageResult:
        return StageResult(name, ok=not ctx.config.get("fail", False), detail="gated")
    return stage


def _cfg_plain(d: date) -> dict:
    return {"as_of": d}


def test_runs_chain_once_per_date_all_green() -> None:
    summary = run_paper_replay(_DATES, _cfg_plain, stages=[("s1", _ok_stage("s1"))])
    assert isinstance(summary, ReplaySummary)
    assert summary.n_steps == 3
    assert summary.n_ok == 3
    assert summary.ok is True
    assert [s.as_of for s in summary.steps] == _DATES


def test_failing_stage_marks_only_that_session_and_continues() -> None:
    # middle session fails its stage; the daemon records it and runs the rest
    def cfg(d: date) -> dict:
        return {"as_of": d, "fail": d == _DATES[1]}

    summary = run_paper_replay(_DATES, cfg, stages=[("risk", _gated_stage("risk"))])
    assert summary.n_steps == 3
    assert summary.n_ok == 2
    assert summary.ok is False
    failures = summary.failures()
    assert [f.as_of for f in failures] == [_DATES[1]]
    assert failures[0].run.failed_stage == "risk"


def test_config_builder_raising_does_not_abort_replay() -> None:
    # cross-date resilience: one date's config blows up, later dates still run
    def cfg(d: date) -> dict:
        if d == _DATES[0]:
            raise ValueError("bad bundle for this session")
        return {"as_of": d}

    summary = run_paper_replay(_DATES, cfg, stages=[("s1", _ok_stage("s1"))])
    assert summary.n_steps == 3
    assert summary.n_ok == 2
    assert summary.failures()[0].as_of == _DATES[0]
    assert "raised ValueError" in summary.steps[0].run.stages[0].detail


def test_empty_dates_is_not_ok() -> None:
    summary = run_paper_replay([], _cfg_plain, stages=[("s1", _ok_stage("s1"))])
    assert summary.n_steps == 0
    assert summary.ok is False  # nothing ran → cannot claim green


def test_summary_string_lists_each_session() -> None:
    def cfg(d: date) -> dict:
        return {"as_of": d, "fail": d == _DATES[2]}

    summary = run_paper_replay(_DATES, cfg, stages=[("risk", _gated_stage("risk"))])
    text = summary.summary()
    assert "2/3 sessions green" in text
    assert "[FAIL] 2023-07-03 @ risk" in text


def test_replay_schedule_quarterly_from_index() -> None:
    idx = pd.bdate_range("2023-01-01", "2023-12-31")
    dates = replay_schedule(idx, "quarterly")
    # one as-of per quarter, all drawn from the index, in order
    assert len(dates) == 4
    assert all(isinstance(d, date) for d in dates)
    assert dates == sorted(dates)
