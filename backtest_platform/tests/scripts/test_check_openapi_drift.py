"""Unit tests for the repo-root ``scripts/check_openapi_drift.py`` Check C / Check D.

The script lives at the repo root (not in the package), so it is loaded by path.
These cover the *pure* helpers (no live OpenAPI dump / no ``uv`` subprocess): the
doc-25 §6 inventory parser (Check C) and the ``data_source`` literal scanner (Check
D), including their drift-detecting negative paths.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO_ROOT / "scripts" / "check_openapi_drift.py"


def _load_drift_module():
    spec = importlib.util.spec_from_file_location("check_openapi_drift", _SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


drift = _load_drift_module()

_MEMBERS = {"PENDING": "pending", "TIMESCALEDB": "timescaledb", "LEDGER": "ledger"}


# ---- Check C: doc §6 inventory table parser --------------------------------
_TABLE = """intro text
<!-- drift:endpoint-inventory:begin -->
| Method | Path | Zone | 📄 | no-FE |
| :--- | :--- | :--- | :---: | :---: |
| GET | `/runs` | Research | 📄 |  |
| POST | `/runs` | Research |  |  |
| GET | `/monitor/board` | Monitor | 📄 |  |
<!-- drift:endpoint-inventory:end -->
trailing text
"""


def test_parse_inventory_table_extracts_method_path_rows():
    ops = drift.parse_inventory_table(_TABLE)
    assert ops == {("GET", "/runs"), ("POST", "/runs"), ("GET", "/monitor/board")}


def test_parse_inventory_table_skips_header_and_separator():
    # "Method" (header) and ":---" (separator) first cells are not verbs → skipped.
    ops = drift.parse_inventory_table(_TABLE)
    assert ("METHOD", "Path") not in ops
    assert not any(p.startswith(":") for _, p in ops)


def test_parse_inventory_table_missing_sentinels_is_infra_error():
    with pytest.raises(drift.CheckInfraError):
        drift.parse_inventory_table("| GET | `/runs` |")


def test_live_operations_from_spec():
    spec = {"paths": {"/x": {"get": {}, "post": {}}, "/y": {"get": {}, "parameters": []}}}
    assert drift.live_operations(spec) == {("GET", "/x"), ("POST", "/x"), ("GET", "/y")}


def test_inventory_diff_summary_flags_both_directions():
    doc = {("GET", "/runs")}
    live = {("GET", "/runs"), ("POST", "/runs")}
    lines = drift._summarize_inventory_diff(doc, live)
    assert any("MISSING from doc" in ln and "POST /runs" in ln for ln in lines)
    # phantom (in doc not live)
    lines2 = drift._summarize_inventory_diff({("GET", "/ghost")}, set())
    assert any("phantom" in ln and "GET /ghost" in ln for ln in lines2)


# ---- Check D: data_source literal scanner ----------------------------------
def test_scan_accepts_enum_reference_and_valid_string():
    src = 'a = {"data_source": DataSource.PENDING}\nb = {"data_source": "timescaledb"}'
    assert drift.scan_data_source_literals(src, _MEMBERS) == []


def test_scan_rejects_unknown_string_literal():
    problems = drift.scan_data_source_literals('a = {"data_source": "pending_m4"}', _MEMBERS)
    assert problems and "pending_m4" in problems[0]


def test_scan_rejects_unknown_enum_member():
    problems = drift.scan_data_source_literals('a = {"data_source": DataSource.NOPE}', _MEMBERS)
    assert problems and "NOPE" in problems[0]


def test_scan_rejects_noncanonical_variable_reference():
    # a re-introduced private constant (the exact pattern A1 killed) must be flagged.
    problems = drift.scan_data_source_literals('a = {"data_source": _SOURCE}', _MEMBERS)
    assert problems and "non-canonical" in problems[0]


def test_datasource_members_parses_live_enum():
    envelope = (_REPO_ROOT / "backtest_platform" / "src" / "backtest_platform" / "api" / "envelope.py")
    members = drift.datasource_members(envelope.read_text(encoding="utf-8"))
    assert members["PENDING"] == "pending"
    assert "TIMESCALEDB" in members and members["TIMESCALEDB"] == "timescaledb"
