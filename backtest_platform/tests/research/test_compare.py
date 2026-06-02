"""compare_runs / rank_by — multi-run side-by-side comparison (8.G.5b).

Pure data processing over runs-ledger dicts (run_id/metrics/gate_status/hypothesis).
Synthetic records only — no parquet, no IO.
"""
from __future__ import annotations

import pytest

from backtest_platform.research.compare import (
    CompareReport,
    RunComparison,
    compare_runs,
    rank_by,
)


def _rec(run_id: str, *, cagr=0.0, sharpe=0.0, struct1_pct=0.0, churn_pct=0.0,
         gate_status="FAIL", hypothesis="h", **extra) -> dict:
    """A minimal ledger-shaped record."""
    m = {"cagr": cagr, "sharpe": sharpe, "struct1_pct": struct1_pct, "churn_pct": churn_pct}
    m.update(extra)
    return {
        "run_id": run_id,
        "metrics": m,
        "gate_status": gate_status,
        "hypothesis": hypothesis,
        "preset": "v3",
    }


# --------------------------------------------------------------------------- #
# rank_by
# --------------------------------------------------------------------------- #
def test_rank_by_descending_default() -> None:
    recs = [_rec("a", cagr=0.10), _rec("b", cagr=0.30), _rec("c", cagr=0.20)]
    ranked = rank_by(recs, "cagr")
    assert [r["run_id"] for r in ranked] == ["b", "c", "a"]


def test_rank_by_ascending() -> None:
    recs = [_rec("a", churn_pct=0.50), _rec("b", churn_pct=0.10), _rec("c", churn_pct=0.30)]
    ranked = rank_by(recs, "churn_pct", descending=False)
    assert [r["run_id"] for r in ranked] == ["b", "c", "a"]


def test_rank_by_does_not_mutate_input() -> None:
    recs = [_rec("a", sharpe=0.1), _rec("b", sharpe=0.9)]
    original_order = [r["run_id"] for r in recs]
    rank_by(recs, "sharpe")
    assert [r["run_id"] for r in recs] == original_order


def test_rank_by_missing_metric_sorts_last() -> None:
    # records lacking the metric must not crash; they sink to the end.
    good = _rec("a", cagr=0.20)
    bad = {"run_id": "b", "metrics": {}, "gate_status": "INCOMPLETE", "hypothesis": "h"}
    ranked = rank_by([bad, good], "cagr")
    assert [r["run_id"] for r in ranked] == ["a", "b"]


def test_rank_by_empty() -> None:
    assert rank_by([], "cagr") == []


# --------------------------------------------------------------------------- #
# compare_runs — baseline + deltas
# --------------------------------------------------------------------------- #
def test_compare_explicit_baseline_deltas() -> None:
    recs = [
        _rec("base", cagr=0.10, sharpe=1.0, struct1_pct=0.20, churn_pct=0.10),
        _rec("cand", cagr=0.25, sharpe=1.5, struct1_pct=0.35, churn_pct=0.05),
    ]
    rep = compare_runs(recs, baseline_id="base")
    assert rep.baseline_id == "base"
    cand = rep.by_id("cand")
    # delta = candidate - baseline, per metric
    assert cand.delta["cagr"] == pytest.approx(0.15)
    assert cand.delta["sharpe"] == pytest.approx(0.5)
    assert cand.delta["struct1_pct"] == pytest.approx(0.15)
    assert cand.delta["churn_pct"] == pytest.approx(-0.05)


def test_baseline_self_delta_is_zero() -> None:
    recs = [_rec("base", cagr=0.10, sharpe=1.0), _rec("cand", cagr=0.25)]
    rep = compare_runs(recs, baseline_id="base")
    base = rep.by_id("base")
    assert base.is_baseline is True
    assert base.delta["cagr"] == pytest.approx(0.0)
    assert base.delta["sharpe"] == pytest.approx(0.0)


def test_default_baseline_is_first_record() -> None:
    recs = [_rec("first", cagr=0.10), _rec("second", cagr=0.40)]
    rep = compare_runs(recs)  # baseline_id=None
    assert rep.baseline_id == "first"
    assert rep.by_id("second").delta["cagr"] == pytest.approx(0.30)


def test_missing_baseline_raises() -> None:
    recs = [_rec("a", cagr=0.1), _rec("b", cagr=0.2)]
    with pytest.raises(KeyError):
        compare_runs(recs, baseline_id="does-not-exist")


def test_empty_records_returns_empty_report() -> None:
    rep = compare_runs([])
    assert rep.baseline_id is None
    assert rep.comparisons == ()
    assert rep.rankings == {}
    assert rep.sign_consistent == {}


# --------------------------------------------------------------------------- #
# compare_runs — cross-run rankings
# --------------------------------------------------------------------------- #
def test_rankings_per_metric() -> None:
    recs = [
        _rec("a", cagr=0.10, sharpe=2.0),
        _rec("b", cagr=0.30, sharpe=0.5),
        _rec("c", cagr=0.20, sharpe=1.0),
    ]
    rep = compare_runs(recs, baseline_id="a")
    # cagr descending → b, c, a
    assert rep.rankings["cagr"] == ("b", "c", "a")
    # sharpe descending → a, c, b
    assert rep.rankings["sharpe"] == ("a", "c", "b")


def test_churn_ranked_ascending_lower_is_better() -> None:
    # churn_pct & struct1_pct are health metrics where lower is better.
    recs = [
        _rec("a", churn_pct=0.30, struct1_pct=0.40),
        _rec("b", churn_pct=0.10, struct1_pct=0.20),
    ]
    rep = compare_runs(recs, baseline_id="a")
    assert rep.rankings["churn_pct"] == ("b", "a")
    assert rep.rankings["struct1_pct"] == ("b", "a")


def test_comparison_carries_rank_position() -> None:
    recs = [_rec("a", cagr=0.10), _rec("b", cagr=0.30)]
    rep = compare_runs(recs, baseline_id="a")
    # best cagr → rank 1
    assert rep.by_id("b").rank["cagr"] == 1
    assert rep.by_id("a").rank["cagr"] == 2


# --------------------------------------------------------------------------- #
# compare_runs — sign consistency
# --------------------------------------------------------------------------- #
def test_sign_consistent_all_positive() -> None:
    recs = [_rec("a", cagr=0.10, sharpe=1.2), _rec("b", cagr=0.30, sharpe=0.8)]
    rep = compare_runs(recs, baseline_id="a")
    assert rep.sign_consistent["cagr"] is True
    assert rep.sign_consistent["sharpe"] is True


def test_sign_inconsistent_when_signs_differ() -> None:
    recs = [_rec("a", cagr=0.10), _rec("b", cagr=-0.05)]
    rep = compare_runs(recs, baseline_id="a")
    assert rep.sign_consistent["cagr"] is False


def test_sign_consistency_single_run_is_trivially_true() -> None:
    rep = compare_runs([_rec("solo", cagr=0.10, sharpe=1.0)])
    assert rep.sign_consistent["cagr"] is True
    assert rep.sign_consistent["sharpe"] is True


def test_sign_consistency_missing_metric_is_false() -> None:
    a = _rec("a", cagr=0.10)
    b = {"run_id": "b", "metrics": {"sharpe": 1.0}, "gate_status": "FAIL", "hypothesis": "h"}
    rep = compare_runs([a, b])
    assert rep.sign_consistent["cagr"] is False


# --------------------------------------------------------------------------- #
# custom metric_keys + report shape
# --------------------------------------------------------------------------- #
def test_custom_metric_keys_restrict_scope() -> None:
    recs = [_rec("a", cagr=0.1, sharpe=1.0), _rec("b", cagr=0.2, sharpe=2.0)]
    rep = compare_runs(recs, baseline_id="a", metric_keys=("sharpe",))
    assert set(rep.rankings.keys()) == {"sharpe"}
    assert set(rep.by_id("b").delta.keys()) == {"sharpe"}


def test_report_and_comparison_are_frozen() -> None:
    rep = compare_runs([_rec("a", cagr=0.1)])
    assert isinstance(rep, CompareReport)
    assert isinstance(rep.by_id("a"), RunComparison)
    with pytest.raises(Exception):
        rep.baseline_id = "x"  # type: ignore[misc]


def test_by_id_unknown_raises() -> None:
    rep = compare_runs([_rec("a", cagr=0.1)])
    with pytest.raises(KeyError):
        rep.by_id("nope")


def test_comparisons_preserve_input_order() -> None:
    recs = [_rec("z", cagr=0.1), _rec("m", cagr=0.5), _rec("a", cagr=0.3)]
    rep = compare_runs(recs, baseline_id="m")
    assert tuple(c.run_id for c in rep.comparisons) == ("z", "m", "a")
