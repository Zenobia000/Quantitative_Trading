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


# ── Research workflow commands (ADR-029) ────────────────────────────────────

def test_doe_dry_run_template():
    """doe --strategy template --dry-run prints config without running the sim."""
    result = CliRunner().invoke(cli, ["doe", "--strategy", "template", "--dry-run"])
    assert result.exit_code == 0
    assert "template" in result.output


def test_doe_unknown_strategy_exits_nonzero():
    result = CliRunner().invoke(cli, ["doe", "--strategy", "nonexistent_xyz"])
    assert result.exit_code != 0


def test_go_gates_dry_run_momentum():
    result = CliRunner().invoke(cli, ["go-gates", "--strategy", "momentum", "--dry-run"])
    assert result.exit_code == 0


def test_truth_gate_dry_run_momentum():
    result = CliRunner().invoke(cli, ["truth-gate", "--strategy", "momentum", "--dry-run"])
    assert result.exit_code == 0


def test_truth_gate_paper_watch_prints_observation_banner(monkeypatch):
    # ADR-033: a PAPER_WATCH verdict must surface the zero-capital / 3-month clause
    # so an operator never mistakes the observation艙 for a deploy-ready REAL.
    from backtest_platform.research.workflows import truth_gate as tg_mod

    fake = tg_mod.TruthGateResult(
        strategy="momentum", verdict="PAPER_WATCH", dsr=0.908,
        slippage_sharpe=0.846, wfa_oos_positive_frac=1.0, oos_holdout_sharpe=0.892,
        position_size=0.0,
        reasons=("DSR 0.908 ∈ [0.9, 0.95) (paper-watch band ...)",),
        details={},
    )
    monkeypatch.setattr(tg_mod, "run_truth_gate", lambda cfg: fake)
    result = CliRunner().invoke(cli, ["truth-gate", "--strategy", "momentum"])
    assert result.exit_code == 0
    assert "🟡" in result.output
    assert "觀察艙" in result.output


def test_paper_replay_dry_run_momentum():
    result = CliRunner().invoke(cli, ["paper-replay", "--strategy", "momentum", "--dry-run"])
    assert result.exit_code == 0


def test_go_gates_undeclared_workflow_exits_nonzero():
    """four_layer declares only DOE — go-gates must fail clearly (not crash)."""
    result = CliRunner().invoke(cli, ["go-gates", "--strategy", "four_layer"])
    assert result.exit_code != 0


def test_build_universe_dry_run_inst_flow():
    """build-universe --dry-run prints the UniverseConfig without touching FinLab."""
    result = CliRunner().invoke(cli, ["build-universe", "--strategy", "inst_flow", "--dry-run"])
    assert result.exit_code == 0
    assert "inst_flow" in result.output
    assert "data/parquet_finlab_universe" in result.output


def test_build_universe_unknown_strategy_exits_nonzero():
    result = CliRunner().invoke(cli, ["build-universe", "--strategy", "nonexistent_xyz"])
    assert result.exit_code != 0


# --- doe --is-start/--is-end override re-validation (審查缺陷 #11) ------------
# The CLI window override used model_copy(update=), so a bad date exploded with a
# bare ValueError traceback and an inverted window slipped through silently. Both
# must now fail at the boundary with a clean ClickException.


def test_doe_valid_window_override_dry_run():
    result = CliRunner().invoke(
        cli,
        ["doe", "--strategy", "momentum",
         "--is-start", "2018-01-01", "--is-end", "2019-01-01", "--dry-run"],
    )
    assert result.exit_code == 0, result.output
    assert "2018-01-01" in result.output and "2019-01-01" in result.output


def test_doe_bad_date_override_clean_error():
    result = CliRunner().invoke(
        cli,
        ["doe", "--strategy", "momentum", "--is-start", "not-a-date", "--dry-run"],
    )
    assert result.exit_code != 0
    # Clean ClickException message reaches the user (not an empty bare traceback).
    assert "invalid" in result.output.lower()


def test_doe_inverted_window_override_rejected():
    result = CliRunner().invoke(
        cli,
        ["doe", "--strategy", "momentum",
         "--is-start", "2025-01-01", "--is-end", "2020-01-01", "--dry-run"],
    )
    # model_copy used to let this pass with exit 0; re-validation must reject it.
    assert result.exit_code != 0
    assert "invalid" in result.output.lower()


# --- run-batch (A1) --------------------------------------------------------

_BATCH_ARGS = [
    "run-batch", "--strategy", "inst_flow", "--hypothesis", "h",
    "--start", "2026-01-05", "--end", "2026-04-10",
]


def test_run_batch_fans_out_and_reports(tmp_path, monkeypatch):
    """One group per semicolon segment; results echo run_id + gate + sharpe."""
    from backtest_platform.research import batch as batch_mod

    captured = {}

    def fake_run_batch(configs, *, runs_path, max_workers, **kw):
        captured["stocks"] = [c.stocks for c in configs]
        captured["max_workers"] = max_workers
        return [
            {"run_id": c.run_id, "batch_status": "done", "gate_status": "PASS",
             "stocks": list(c.stocks), "metrics": {"sharpe": 1.2}}
            for c in configs
        ]

    monkeypatch.setattr(batch_mod, "run_batch", fake_run_batch)
    res = CliRunner().invoke(cli, [
        *_BATCH_ARGS, "--stock-groups", "2330,2317;2454",
        "--max-workers", "2", "--runs-path", str(tmp_path / "runs.jsonl"),
    ])
    assert res.exit_code == 0, res.output
    assert captured["stocks"] == [("2330", "2317"), ("2454",)]
    assert captured["max_workers"] == 2
    assert "[PASS" in res.output and "2 done / 0 failed" in res.output


def test_run_batch_failure_exits_nonzero(tmp_path, monkeypatch):
    from backtest_platform.research import batch as batch_mod

    def fake_run_batch(configs, **kw):
        return [{"run_id": configs[0].run_id, "batch_status": "failed",
                 "error": "sim exploded"}]

    monkeypatch.setattr(batch_mod, "run_batch", fake_run_batch)
    res = CliRunner().invoke(cli, [
        *_BATCH_ARGS, "--stock-groups", "2330",
        "--runs-path", str(tmp_path / "runs.jsonl"),
    ])
    assert res.exit_code == 1
    assert "sim exploded" in res.output


def test_run_batch_empty_groups_is_usage_error(tmp_path):
    res = CliRunner().invoke(cli, [
        *_BATCH_ARGS, "--stock-groups", ";;",
        "--runs-path", str(tmp_path / "runs.jsonl"),
    ])
    assert res.exit_code == 2  # click UsageError
