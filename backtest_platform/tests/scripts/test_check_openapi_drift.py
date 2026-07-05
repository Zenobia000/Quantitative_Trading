"""Unit tests for the repo-root ``scripts/check_openapi_drift.py`` Check C.

The script lives at the repo root (not in the package), so it is loaded by path.
These cover the *pure* helper with no live OpenAPI dump / no ``uv`` subprocess: the
``data_source`` literal scanner (Check C), including its drift-detecting negative
paths.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

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


# ---- Check C: data_source literal scanner ----------------------------------
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
