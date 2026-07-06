"""run_persist — JSONL ledger (authoritative) + best-effort TimescaleDB mirror.

The ledger append must NEVER be blocked by DB unavailability: a research run's
record is authoritative in reports/runs.jsonl; the runs hypertable is a mirror
for the board/analytics (A0, 8.G.1 closing the "upsert_runs has no caller" gap).
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

from quant_platform.packages.adapters.run_writer import persist_run
from quant_platform.packages.adapters.run_db_mapper import run_record_to_db_row
from quant_platform.packages.adapters.runs_store import read_runs

_RECORD = {
    "run_id": "a1b2c3d4e5f6",
    "created_at": "2026-07-02T10:00:00",
    "hypothesis": "inst_flow edge survives costs",
    "strategy": "inst_flow",
    "params": {"top_n": 5},
    "engine": "sim",
    "stocks": ["2330", "2317"],
    "window": ["2026-01-05", "2026-04-10"],
    "metrics": {"cagr": 0.12, "sharpe": 1.1},
    "gate_status": "PASS",
    "gate_summary": "IS gate: 4/4 checks passed",
}


# ---------------------------------------------------------------------------
# run_record_to_db_row — pure ledger-record → runs-row mapping
# ---------------------------------------------------------------------------
def test_run_record_to_db_row_maps_window_to_date_columns() -> None:
    row = run_record_to_db_row(_RECORD)
    assert row["is_start"] == "2026-01-05"
    assert row["is_end"] == "2026-04-10"
    assert "window" not in row  # DDL has no window column


def test_run_record_to_db_row_supplies_not_null_defaults() -> None:
    """status / trials_count are NOT NULL in DDL — the mapper must supply them."""
    row = run_record_to_db_row(_RECORD)
    assert row["status"] == "done"
    assert row["trials_count"] == 1


def test_run_record_to_db_row_carries_gate_verdict() -> None:
    row = run_record_to_db_row(_RECORD)
    assert row["gate_status"] == "PASS"
    assert row["gate_summary"] == "IS gate: 4/4 checks passed"


def test_run_record_to_db_row_passes_identity_and_payloads() -> None:
    row = run_record_to_db_row(_RECORD)
    assert row["run_id"] == "a1b2c3d4e5f6"
    assert row["hypothesis"] == _RECORD["hypothesis"]
    assert row["strategy"] == "inst_flow"
    assert row["engine"] == "sim"
    assert row["stocks"] == ["2330", "2317"]
    assert row["params"] == {"top_n": 5}
    assert row["metrics"] == {"cagr": 0.12, "sharpe": 1.1}


def test_run_record_to_db_row_tolerates_missing_window() -> None:
    rec = {k: v for k, v in _RECORD.items() if k != "window"}
    row = run_record_to_db_row(rec)
    assert row["is_start"] is None and row["is_end"] is None


# ---------------------------------------------------------------------------
# persist_run — ledger append + best-effort DB mirror
# ---------------------------------------------------------------------------
def test_persist_run_appends_ledger_and_mirrors_db(tmp_path) -> None:
    runs_path = tmp_path / "runs.jsonl"
    writer = MagicMock()
    mirrored = persist_run(_RECORD, runs_path, writer=writer)

    assert mirrored is True
    ledger = read_runs(runs_path)
    assert len(ledger) == 1 and ledger[0]["run_id"] == "a1b2c3d4e5f6"
    writer.upsert_runs.assert_called_once()
    (rows,) = writer.upsert_runs.call_args.args
    assert rows == [run_record_to_db_row(_RECORD)]


def test_persist_run_db_failure_is_nonfatal_ledger_wins(tmp_path) -> None:
    """DB down / bad creds must not lose the run: ledger written, False returned."""
    runs_path = tmp_path / "runs.jsonl"
    writer = MagicMock()
    writer.upsert_runs.side_effect = RuntimeError("connection refused")

    mirrored = persist_run(_RECORD, runs_path, writer=writer)

    assert mirrored is False
    assert len(read_runs(runs_path)) == 1  # ledger append survived


def test_persist_run_default_writer_degrades_without_db(tmp_path) -> None:
    """No injected writer + placeholder POSTGRES_PASSWORD → require_postgres
    refuses before any socket opens; persist_run degrades to ledger-only."""
    runs_path = tmp_path / "runs.jsonl"
    mirrored = persist_run(_RECORD, runs_path)
    assert mirrored is False
    assert len(read_runs(runs_path)) == 1


def test_persist_run_appends_not_overwrites(tmp_path) -> None:
    runs_path = tmp_path / "runs.jsonl"
    persist_run(_RECORD, runs_path, writer=MagicMock())
    persist_run({**_RECORD, "run_id": "ffffffffffff"}, runs_path, writer=MagicMock())
    ids = [r["run_id"] for r in read_runs(runs_path)]
    assert ids == ["a1b2c3d4e5f6", "ffffffffffff"]


def test_persist_run_record_stays_json_serializable(tmp_path) -> None:
    """The mirrored row must not mutate the ledger record (immutability rule)."""
    runs_path = tmp_path / "runs.jsonl"
    record = dict(_RECORD)
    persist_run(record, runs_path, writer=MagicMock())
    assert record == _RECORD  # untouched
    json.dumps(record)  # still serializable
