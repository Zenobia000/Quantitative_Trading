"""runs_store — append-only run ledger (collects the散裝 reports/ orphans)."""
from __future__ import annotations

from backtest_platform.research.runs_store import append_run, read_runs


def test_append_and_read_roundtrip(tmp_path) -> None:
    p = tmp_path / "runs.jsonl"
    append_run({"run_id": "abc", "gate_status": "FAIL", "metrics": {"cagr": -0.02}}, p)
    append_run({"run_id": "def", "gate_status": "PASS", "metrics": {"cagr": 0.20}}, p)
    runs = read_runs(p)
    assert [r["run_id"] for r in runs] == ["abc", "def"]
    assert runs[1]["gate_status"] == "PASS"
    assert runs[0]["metrics"]["cagr"] == -0.02


def test_read_missing_file_is_empty(tmp_path) -> None:
    assert read_runs(tmp_path / "nope.jsonl") == []


def test_append_creates_parent_dir(tmp_path) -> None:
    p = tmp_path / "nested" / "runs.jsonl"
    append_run({"run_id": "x"}, p)
    assert p.exists()
    assert read_runs(p)[0]["run_id"] == "x"
