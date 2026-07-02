"""Batch fan-out (A1) — expand stock groups into RunConfigs, run them in a
bounded thread pool, and persist the running→done/failed lifecycle so the run
board can read live state straight from the runs table."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from backtest_platform.research.batch import expand_stock_groups, run_batch
from backtest_platform.research.run_config import RunConfig
from backtest_platform.research.runs_store import read_runs

_BASE = {
    "hypothesis": "90d window edge scan",
    "strategy": "inst_flow",
    "params": {"top_n": 2},
    "is_start": date(2026, 1, 5),
    "is_end": date(2026, 4, 10),
}


def _fake_record(cfg: RunConfig) -> dict:
    return {
        "run_id": cfg.run_id,
        "hypothesis": cfg.hypothesis,
        "strategy": cfg.strategy,
        "params": dict(cfg.params),
        "engine": cfg.engine,
        "stocks": list(cfg.stocks),
        "window": [cfg.is_start.isoformat(), cfg.is_end.isoformat()],
        "metrics": {"sharpe": 1.0},
        "gate_status": "PASS",
        "gate_summary": "ok",
    }


# ---------------------------------------------------------------------------
# expand_stock_groups
# ---------------------------------------------------------------------------
def test_expand_stock_groups_one_config_per_group() -> None:
    cfgs = expand_stock_groups(_BASE, [["2330", "2317"], ["2454"]])
    assert len(cfgs) == 2
    assert cfgs[0].stocks == ("2330", "2317")
    assert cfgs[1].stocks == ("2454",)
    assert all(c.strategy == "inst_flow" for c in cfgs)


def test_expand_stock_groups_dedups_identical_groups() -> None:
    cfgs = expand_stock_groups(_BASE, [["2330"], ["2330"], ["2317"]])
    assert len(cfgs) == 2  # same group → same deterministic run_id → one config


def test_expand_stock_groups_empty_group_rejected() -> None:
    with pytest.raises(ValueError, match="empty"):
        expand_stock_groups(_BASE, [["2330"], []])


# ---------------------------------------------------------------------------
# run_batch
# ---------------------------------------------------------------------------
def test_run_batch_runs_all_and_persists_ledger(tmp_path) -> None:
    runs_path = tmp_path / "runs.jsonl"
    cfgs = expand_stock_groups(_BASE, [["2330", "2317"], ["2454"], ["2308"]])

    results = run_batch(
        cfgs, executor=_fake_record, runs_path=runs_path,
        writer=MagicMock(), max_workers=2,
    )

    assert len(results) == 3
    assert {r["run_id"] for r in results} == {c.run_id for c in cfgs}
    assert all(r["batch_status"] == "done" for r in results)
    ledger_ids = {r["run_id"] for r in read_runs(runs_path)}
    assert ledger_ids == {c.run_id for c in cfgs}


def test_run_batch_results_keep_input_order(tmp_path) -> None:
    cfgs = expand_stock_groups(_BASE, [["2330"], ["2317"], ["2454"]])
    results = run_batch(
        cfgs, executor=_fake_record, runs_path=tmp_path / "runs.jsonl",
        writer=MagicMock(), max_workers=3,
    )
    assert [r["run_id"] for r in results] == [c.run_id for c in cfgs]


def test_run_batch_failure_is_isolated(tmp_path) -> None:
    """One config blowing up must not sink the batch: the failed run reports
    batch_status='failed' (+ error), every other run completes normally."""
    runs_path = tmp_path / "runs.jsonl"
    cfgs = expand_stock_groups(_BASE, [["2330"], ["2317"], ["2454"]])
    bad_id = cfgs[1].run_id

    def executor(cfg: RunConfig) -> dict:
        if cfg.run_id == bad_id:
            raise RuntimeError("sim exploded")
        return _fake_record(cfg)

    results = run_batch(
        cfgs, executor=executor, runs_path=runs_path,
        writer=MagicMock(), max_workers=2,
    )

    by_id = {r["run_id"]: r for r in results}
    assert by_id[bad_id]["batch_status"] == "failed"
    assert "sim exploded" in by_id[bad_id]["error"]
    done = [r for r in results if r["batch_status"] == "done"]
    assert len(done) == 2
    # failed run never reaches the ledger; the two good ones do
    assert {r["run_id"] for r in read_runs(runs_path)} == {r["run_id"] for r in done}


def test_run_batch_mirrors_lifecycle_to_runs_table(tmp_path) -> None:
    """The board reads live state from the runs table: each run upserts a
    'running' row before executing, then 'done' (via persist_run) after —
    and 'failed' on error."""
    runs_path = tmp_path / "runs.jsonl"
    cfgs = expand_stock_groups(_BASE, [["2330"], ["2317"]])
    bad_id = cfgs[1].run_id
    writer = MagicMock()

    def executor(cfg: RunConfig) -> dict:
        if cfg.run_id == bad_id:
            raise RuntimeError("boom")
        return _fake_record(cfg)

    run_batch(cfgs, executor=executor, runs_path=runs_path, writer=writer, max_workers=1)

    statuses: dict[str, list[str]] = {}
    for call in writer.upsert_runs.call_args_list:
        (rows,) = call.args
        for row in rows:
            statuses.setdefault(row["run_id"], []).append(row["status"])
    assert statuses[cfgs[0].run_id] == ["running", "done"]
    assert statuses[bad_id] == ["running", "failed"]


def test_run_batch_db_down_still_completes(tmp_path) -> None:
    """DB mirror is best-effort everywhere: a raising writer must not fail runs."""
    runs_path = tmp_path / "runs.jsonl"
    cfgs = expand_stock_groups(_BASE, [["2330"], ["2317"]])
    writer = MagicMock()
    writer.upsert_runs.side_effect = RuntimeError("connection refused")

    results = run_batch(
        cfgs, executor=_fake_record, runs_path=runs_path, writer=writer, max_workers=2,
    )
    assert all(r["batch_status"] == "done" for r in results)
    assert len(read_runs(runs_path)) == 2


def test_run_batch_rejects_bad_max_workers(tmp_path) -> None:
    cfgs = expand_stock_groups(_BASE, [["2330"]])
    with pytest.raises(ValueError, match="max_workers"):
        run_batch(cfgs, executor=_fake_record, runs_path=tmp_path / "r.jsonl",
                  writer=MagicMock(), max_workers=0)


def test_run_batch_empty_configs_returns_empty(tmp_path) -> None:
    assert run_batch([], executor=_fake_record, runs_path=tmp_path / "r.jsonl",
                     writer=MagicMock()) == []
