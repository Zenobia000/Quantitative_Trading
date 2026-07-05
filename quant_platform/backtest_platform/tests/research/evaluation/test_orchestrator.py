"""research.evaluation.orchestrator — profile e2e over a synthetic loader (Goal 3)."""
from __future__ import annotations

import json
from datetime import date

import pytest

from backtest_platform.research.evaluation import evaluate
from backtest_platform.research.evaluation.store import get_evaluation, read_evaluations
from backtest_platform.strategies.conformance import synthetic_loader

_SYMS = [f"SYN{i:04d}" for i in range(6)]


@pytest.fixture
def paths(tmp_path):
    return {"evaluations_path": tmp_path / "ev.jsonl", "pack_root": tmp_path / "packs"}


def _triage(paths, **kw):
    return evaluate(
        "momentum", "quick_triage", loader=synthetic_loader(n_bars=500),
        symbols=_SYMS, is_start=date(2019, 1, 1), is_end=date(2020, 12, 31),
        **paths, **kw,
    )


def test_quick_triage_e2e_returns_contract_shape(paths):
    r = _triage(paths)
    assert r["schema_version"] == "1.0"
    assert r["strategy"] == "momentum"
    assert r["profile"] == "quick_triage"
    assert r["verdict"]["truth_verdict"] is None
    assert [sc["category"] for sc in r["scorecards"]] == \
        ["profitability", "risk", "risk_adjusted", "win_rate", "liquidity"]
    assert "report_pack_ref" in r


def test_quick_triage_persists_to_ledger(paths):
    r = _triage(paths)
    ledger = read_evaluations(paths["evaluations_path"])
    assert len(ledger) == 1
    assert get_evaluation(r["evaluation_id"], paths["evaluations_path"])["run_id"] == r["run_id"]


def test_report_pack_has_required_files(paths):
    r = _triage(paths)
    pack_dir = paths["pack_root"] / r["run_id"]
    for f in ("summary.json", "metrics.json", "scorecards.json", "report.md", "manifest.json"):
        assert (pack_dir / f).exists(), f"missing {f}"
    manifest = json.loads((pack_dir / "manifest.json").read_text())
    names = {f["name"]: f["status"] for f in manifest["files"]}
    assert names["summary.json"] == "available"
    assert names["scorecards.json"] == "available"


def test_weak_strategy_still_persisted(paths):
    """A failing/weak strategy is a research asset — never discarded (global acceptance #5)."""
    r = _triage(paths)  # synthetic momentum is a weak edge
    assert r["verdict"]["label"] in ("Weak", "Negative", "Promising")
    assert len(read_evaluations(paths["evaluations_path"])) == 1


def test_unknown_profile_raises(paths):
    with pytest.raises(ValueError, match="unknown evaluation profile"):
        evaluate("momentum", "nope", loader=synthetic_loader(), symbols=_SYMS,
                 is_start=date(2019, 1, 1), is_end=date(2020, 12, 31), **paths)


def test_unknown_strategy_raises(paths):
    with pytest.raises(ValueError, match="unknown strategy"):
        evaluate("nope", "quick_triage", loader=synthetic_loader(), symbols=_SYMS,
                 is_start=date(2019, 1, 1), is_end=date(2020, 12, 31), **paths)


def test_evaluation_id_is_deterministic_per_config(paths):
    r1 = _triage(paths)
    r2 = _triage({"evaluations_path": paths["evaluations_path"], "pack_root": paths["pack_root"]})
    assert r1["evaluation_id"] == r2["evaluation_id"]  # same config → same id (re-run folds)


@pytest.mark.slow
def test_fixed_hypothesis_oos_runs(paths):
    r = evaluate("momentum", "fixed_hypothesis_oos", loader=synthetic_loader(n_bars=1500), **paths)
    assert r["profile"] == "fixed_hypothesis_oos"
    assert "wfa_oos_positive_frac" in r["headline_metrics"]


@pytest.mark.slow
def test_grid_search_selection_runs(paths):
    r = evaluate("momentum", "grid_search_selection", loader=synthetic_loader(n_bars=1500), **paths)
    assert r["profile"] == "grid_search_selection"
    assert r["lineage"]["n_trials"] >= 1


@pytest.mark.slow
def test_deployment_strict_wraps_truth_gate(paths):
    r = evaluate("momentum", "deployment_strict", loader=synthetic_loader(n_bars=1800), **paths)
    assert r["profile"] == "deployment_strict"
    assert r["verdict"]["truth_verdict"] in ("REAL", "PAPER_WATCH", "REJECTED", "INCOMPLETE")
    # deployment_strict emits the severity-graded checks
    assert any(c["metric"] == "survivorship_clean" for c in r["checks"])
