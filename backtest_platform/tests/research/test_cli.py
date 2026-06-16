"""research.cli — `validate` subcommand (hermetic, ledger + ValidationGate) and
the `run-is --tearsheet` flag (sim stubbed so no parquet/quantstats is touched)."""
from __future__ import annotations

import json

import pandas as pd
from click.testing import CliRunner

from backtest_platform.research import cli as cli_mod
from backtest_platform.research.cli import cli

# Metrics that clear every DEFAULT_GATE criterion (edge + health).
_PASS_METRICS = {
    "cagr": 0.25, "sharpe": 1.5, "slippage_sharpe": 1.2,
    "struct1_pct": 0.10, "churn_pct": 0.10, "avg_hold": 8.0,
}
# Fails the edge criteria + the health checks.
_FAIL_METRICS = {
    "cagr": 0.01, "sharpe": 0.2, "slippage_sharpe": 0.2,
    "struct1_pct": 0.90, "churn_pct": 0.90, "avg_hold": 1.0,
}


def _write_ledger(path, records):
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# --- validate ------------------------------------------------------------

def test_validate_is_pass(tmp_path):
    ledger = tmp_path / "runs.jsonl"
    _write_ledger(ledger, [{"run_id": "good1", "strategy": "four_layer", "hypothesis": "h", "metrics": _PASS_METRICS}])
    res = CliRunner().invoke(cli, ["validate", "--run-id", "good1", "--runs-path", str(ledger)])
    assert res.exit_code == 0, res.output
    assert "GATE STATE: IS_PASS" in res.output
    assert "WFA 已解鎖" in res.output
    # OOS stays sealed until WFA is submitted
    assert "SEALED" in res.output


def test_validate_is_fail(tmp_path):
    ledger = tmp_path / "runs.jsonl"
    _write_ledger(ledger, [{"run_id": "bad1", "strategy": "four_layer", "hypothesis": "h", "metrics": _FAIL_METRICS}])
    res = CliRunner().invoke(cli, ["validate", "--run-id", "bad1", "--runs-path", str(ledger)])
    assert res.exit_code == 0, res.output
    assert "GATE STATE: FAILED" in res.output
    assert "FAIL" in res.output


def test_validate_incomplete_metrics_is_not_pass(tmp_path):
    ledger = tmp_path / "runs.jsonl"
    _write_ledger(ledger, [{"run_id": "inc1", "strategy": "four_layer", "hypothesis": "h", "metrics": {"cagr": 0.25}}])
    res = CliRunner().invoke(cli, ["validate", "--run-id", "inc1", "--runs-path", str(ledger)])
    assert res.exit_code == 0, res.output
    # INCOMPLETE gate → submit_is → FAILED (cannot APPROVE what you cannot fully judge)
    assert "GATE STATE: FAILED" in res.output
    assert "INCOMPLETE" in res.output


def test_validate_unknown_run_id_errors(tmp_path):
    ledger = tmp_path / "runs.jsonl"
    _write_ledger(ledger, [])
    res = CliRunner().invoke(cli, ["validate", "--run-id", "nope", "--runs-path", str(ledger)])
    assert res.exit_code != 0
    assert "not found" in res.output


# --- run-is --tearsheet --------------------------------------------------

_CANNED_REC = {
    "run_id": "rid9", "strategy": "four_layer", "hypothesis": "h",
    "metrics": {"trades": 3, "cagr": 0.10, "sharpe": 0.50,
                "struct1_pct": 0.10, "churn_pct": 0.10, "avg_hold": 7.0},
    "gate_status": "INCOMPLETE", "gate_summary": "GATE: INCOMPLETE",
}
_RUN_IS_ARGS = [
    "run-is", "--strategy", "four_layer", "--params", "{}",
    "--hypothesis", "h", "--stocks", "2330",
    "--start", "2020-01-01", "--end", "2024-12-31",
]


def test_run_is_tearsheet_flag_writes_report(tmp_path, monkeypatch):
    ledger = tmp_path / "runs.jsonl"
    returns = pd.Series([0.01, -0.02, 0.03, 0.0, 0.01])
    monkeypatch.setattr(cli_mod, "run_and_judge_with_returns", lambda cfg: (_CANNED_REC, returns))

    captured = {}

    def _stub_write(series, out_path, title=""):
        from pathlib import Path
        captured["series"] = series
        captured["out_path"] = Path(out_path)
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text("<html>stub</html>", encoding="utf-8")
        return Path(out_path)

    monkeypatch.setattr(cli_mod, "write_tearsheet", _stub_write)

    res = CliRunner().invoke(cli, [
        *_RUN_IS_ARGS, "--runs-path", str(ledger),
        "--tearsheet", "--tearsheet-dir", str(tmp_path / "ts"),
    ])
    assert res.exit_code == 0, res.output
    assert "tear sheet:" in res.output
    assert captured["series"] is returns
    assert captured["out_path"].name == "rid9.html"
    assert ledger.exists()  # run still appended


def test_run_is_tearsheet_skipped_when_unavailable(tmp_path, monkeypatch):
    ledger = tmp_path / "runs.jsonl"
    returns = pd.Series([0.01, -0.02])
    monkeypatch.setattr(cli_mod, "run_and_judge_with_returns", lambda cfg: (_CANNED_REC, returns))
    monkeypatch.setattr(cli_mod, "write_tearsheet", lambda *a, **k: None)

    res = CliRunner().invoke(cli, [
        *_RUN_IS_ARGS, "--runs-path", str(ledger), "--tearsheet",
    ])
    assert res.exit_code == 0, res.output
    assert "skipped" in res.output


def test_run_is_without_tearsheet_does_not_write(tmp_path, monkeypatch):
    ledger = tmp_path / "runs.jsonl"
    returns = pd.Series([0.01, -0.02])
    monkeypatch.setattr(cli_mod, "run_and_judge_with_returns", lambda cfg: (_CANNED_REC, returns))

    def _boom(*a, **k):  # must NOT be called without the flag
        raise AssertionError("write_tearsheet called without --tearsheet")

    monkeypatch.setattr(cli_mod, "write_tearsheet", _boom)

    res = CliRunner().invoke(cli, [*_RUN_IS_ARGS, "--runs-path", str(ledger)])
    assert res.exit_code == 0, res.output
    assert "tear sheet" not in res.output
    assert ledger.exists()


# --- promote-check -------------------------------------------------------

def test_promote_check_approved_is_eligible(tmp_path):
    # Forward-compat: a run that carries an explicit APPROVED validation_status
    # (written once v0.2 wires OOS into the ledger) is the only promotable state.
    ledger = tmp_path / "runs.jsonl"
    _write_ledger(ledger, [{
        "run_id": "appr1", "strategy": "four_layer", "hypothesis": "h",
        "metrics": _PASS_METRICS, "gate_status": "PASS",
        "validation_status": "APPROVED",
    }])
    res = CliRunner().invoke(cli, ["promote-check", "--run-id", "appr1", "--runs-path", str(ledger)])
    assert res.exit_code == 0, res.output
    assert "VALIDATION STATUS: APPROVED" in res.output
    assert "ELIGIBLE" in res.output
    assert "NOT ELIGIBLE" not in res.output


def test_promote_check_is_pass_not_eligible_lists_outstanding(tmp_path):
    # IS passes but nothing beyond is recorded → NOT promotable; WFA/OOS/approve
    # are listed as outstanding. Promotion is never rubber-stamped on IS alone.
    ledger = tmp_path / "runs.jsonl"
    _write_ledger(ledger, [{"run_id": "good1", "strategy": "four_layer", "hypothesis": "h", "metrics": _PASS_METRICS}])
    res = CliRunner().invoke(cli, ["promote-check", "--run-id", "good1", "--runs-path", str(ledger)])
    assert res.exit_code == 0, res.output
    assert "VALIDATION STATUS: IS_PASS" in res.output
    assert "NOT ELIGIBLE" in res.output
    assert "WFA" in res.output and "OOS" in res.output


def test_promote_check_is_fail_not_eligible(tmp_path):
    ledger = tmp_path / "runs.jsonl"
    _write_ledger(ledger, [{"run_id": "bad1", "strategy": "four_layer", "hypothesis": "h", "metrics": _FAIL_METRICS}])
    res = CliRunner().invoke(cli, ["promote-check", "--run-id", "bad1", "--runs-path", str(ledger)])
    assert res.exit_code == 0, res.output
    assert "VALIDATION STATUS: FAILED" in res.output
    assert "NOT ELIGIBLE" in res.output


def test_promote_check_explicit_status_overrides_derivation(tmp_path):
    # An explicit (non-terminal) validation_status is honored over IS derivation:
    # OOS_PASS shows as such, still NOT eligible, only `approve` outstanding.
    ledger = tmp_path / "runs.jsonl"
    _write_ledger(ledger, [{
        "run_id": "oos1", "strategy": "four_layer", "hypothesis": "h",
        "metrics": _FAIL_METRICS, "validation_status": "OOS_PASS",
    }])
    res = CliRunner().invoke(cli, ["promote-check", "--run-id", "oos1", "--runs-path", str(ledger)])
    assert res.exit_code == 0, res.output
    assert "VALIDATION STATUS: OOS_PASS" in res.output
    assert "NOT ELIGIBLE" in res.output
    assert "approve" in res.output


def test_promote_check_honors_persisted_lowercase_verdict(tmp_path):
    # Regression (code-audit 2026-06-10): promotion_service writes validation_status
    # in the lowercase verdict vocabulary ("is_pass"). The CLI used to parse it as a
    # GateState enum, fail, and silently re-derive from metrics — here the metrics
    # FAIL, so the bug would have shown FAILED. With coerce_gate_state the persisted
    # is_pass is honored → IS_PASS (and the recorded verdict is NOT overridden by the
    # contradicting metrics).
    ledger = tmp_path / "runs.jsonl"
    _write_ledger(ledger, [{
        "run_id": "lp1", "strategy": "four_layer", "hypothesis": "h",
        "metrics": _FAIL_METRICS, "validation_status": "is_pass",
    }])
    res = CliRunner().invoke(cli, ["promote-check", "--run-id", "lp1", "--runs-path", str(ledger)])
    assert res.exit_code == 0, res.output
    assert "VALIDATION STATUS: IS_PASS" in res.output
    assert "VALIDATION STATUS: FAILED" not in res.output
    assert "NOT ELIGIBLE" in res.output


def test_promote_check_unknown_run_id_errors(tmp_path):
    ledger = tmp_path / "runs.jsonl"
    _write_ledger(ledger, [])
    res = CliRunner().invoke(cli, ["promote-check", "--run-id", "nope", "--runs-path", str(ledger)])
    assert res.exit_code != 0
    assert "not found" in res.output
