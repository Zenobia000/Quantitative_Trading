"""research.branch_store — branch lineage: create / evaluate / compare (Goal 9).

Pure-function guards (delta classify / apply / immutability), a create→evaluate→compare
round-trip over the synthetic loader, and the two acceptance invariants: the parent
records are never mutated, and a branch never folds over its parent's evaluation.
"""
from __future__ import annotations

from datetime import date

import pytest

from backtest_platform.research.adapters import branch_store as bs
from backtest_platform.research.evaluation import evaluate
from backtest_platform.research.evaluation.store import get_evaluation, read_evaluations
from backtest_platform.strategies.conformance import synthetic_loader

_SYMS = [f"SYN{i:04d}" for i in range(6)]
_SCHEMA = {"properties": {"lookback_days": {}, "top_fraction": {}}}


# --------------------------------------------------------------------------- #
# pure functions                                                              #
# --------------------------------------------------------------------------- #
def test_classify_delta_splits_config_overlay_illegal():
    cfg, overlay, illegal = bs.classify_delta(
        [{"key": "lookback_days", "to": 90}, {"key": "slippage_bps", "to": 10}, {"key": "bogus", "to": 1}],
        _SCHEMA,
    )
    assert cfg == ["lookback_days"]
    assert overlay == ["slippage_bps"]
    assert illegal == ["bogus"]


def test_apply_config_delta_returns_new_object_parent_untouched():
    parent = {"lookback_days": 60, "top_fraction": 0.33}
    branch = bs.apply_config_delta(parent, [{"key": "lookback_days", "to": 90}], _SCHEMA)
    assert branch == {"lookback_days": 90, "top_fraction": 0.33}
    assert parent == {"lookback_days": 60, "top_fraction": 0.33}  # never mutated
    assert branch is not parent


def test_apply_config_delta_ignores_overlay_knobs():
    parent = {"lookback_days": 60}
    branch = bs.apply_config_delta(parent, [{"key": "slippage_bps", "to": 10}], _SCHEMA)
    assert branch == {"lookback_days": 60}  # overlay knob not injected into run params


# --------------------------------------------------------------------------- #
# fixtures — seed a real parent evaluation via the synthetic loader           #
# --------------------------------------------------------------------------- #
@pytest.fixture
def store(tmp_path):
    return {
        "evaluations_path": tmp_path / "ev.jsonl",
        "branches_path": tmp_path / "br.jsonl",
        "pack_root": tmp_path / "packs",
    }


def _seed_parent(store):
    return evaluate(
        "momentum", "quick_triage", loader=synthetic_loader(n_bars=500),
        symbols=_SYMS, is_start=date(2019, 1, 1), is_end=date(2020, 12, 31),
        evaluations_path=store["evaluations_path"], pack_root=store["pack_root"],
    )


def _create(store, parent, delta, **kw):
    return bs.create_branch(
        parent["evaluation_id"], delta,
        branches_path=store["branches_path"], evaluations_path=store["evaluations_path"], **kw,
    )


# --------------------------------------------------------------------------- #
# create                                                                       #
# --------------------------------------------------------------------------- #
def test_create_branch_links_parent_and_applies_delta(store):
    parent = _seed_parent(store)
    branch = _create(store, parent, [{"key": "lookback_days", "to": 90}])
    assert branch["parent_evaluation_id"] == parent["evaluation_id"]
    assert branch["parent_run_id"] == parent["run_id"]
    assert branch["strategy"] == "momentum"
    assert branch["status"] == "draft"
    assert branch["evaluation_id"] is None
    assert branch["applies_to_rerun"] is True
    assert branch["branch_config"]["lookback_days"] == 90
    # `from` resolved from the parent config, not trusted from the client.
    assert branch["config_delta"][0]["from"] == parent["lineage"]["params"]["lookback_days"]


def test_create_branch_unknown_parent_raises(store):
    with pytest.raises(bs.ParentNotFoundError):
        _create(store, {"evaluation_id": "eval_ghost"}, [{"key": "lookback_days", "to": 90}])


def test_create_branch_illegal_key_raises(store):
    parent = _seed_parent(store)
    with pytest.raises(bs.IllegalDeltaError):
        _create(store, parent, [{"key": "not_a_field", "to": 1}])


def test_create_branch_out_of_bounds_value_raises(store):
    parent = _seed_parent(store)
    # lookback_days has ge/le bounds on the config_model → a wild value is rejected.
    with pytest.raises(bs.IllegalDeltaError):
        _create(store, parent, [{"key": "lookback_days", "to": 100000}])


def test_create_branch_empty_delta_raises(store):
    parent = _seed_parent(store)
    with pytest.raises(bs.IllegalDeltaError):
        _create(store, parent, [])


def test_create_branch_overlay_only_not_evaluable(store):
    parent = _seed_parent(store)
    branch = _create(store, parent, [{"key": "slippage_bps", "to": 10}], origin="simulation")
    assert branch["applies_to_rerun"] is False  # runner does not consume the knob


# --------------------------------------------------------------------------- #
# evaluate + immutability                                                       #
# --------------------------------------------------------------------------- #
def test_evaluate_branch_backfills_distinct_evaluation(store):
    parent = _seed_parent(store)
    branch = _create(store, parent, [{"key": "lookback_days", "to": 90}])
    out = bs.evaluate_branch(
        branch["branch_id"], loader=synthetic_loader(n_bars=500),
        branches_path=store["branches_path"], evaluations_path=store["evaluations_path"],
        pack_root=store["pack_root"], ingest=False,
    )
    ev = out["evaluation"]
    assert out["branch"]["status"] == "evaluated"
    assert out["branch"]["evaluation_id"] == ev["evaluation_id"]
    # A branch NEVER folds over its parent — distinct run_id (config hash) + eval id.
    assert ev["evaluation_id"] != parent["evaluation_id"]
    assert ev["run_id"] != parent["run_id"]
    assert ev["branch"]["branch_id"] == branch["branch_id"]


def test_evaluate_branch_does_not_mutate_parent_evaluation(store):
    """Goal 9 acceptance #3: the parent evaluation record is provably unchanged."""
    parent = _seed_parent(store)
    before = get_evaluation(parent["evaluation_id"], store["evaluations_path"])
    branch = _create(store, parent, [{"key": "lookback_days", "to": 90}])
    bs.evaluate_branch(
        branch["branch_id"], loader=synthetic_loader(n_bars=500),
        branches_path=store["branches_path"], evaluations_path=store["evaluations_path"],
        pack_root=store["pack_root"], ingest=False,
    )
    after = get_evaluation(parent["evaluation_id"], store["evaluations_path"])
    assert after == before  # parent evaluation byte-identical after the branch ran
    # ...and the parent's original ledger line still exists (append-only, not overwritten).
    ids = [r["evaluation_id"] for r in read_evaluations(store["evaluations_path"])]
    assert ids.count(parent["evaluation_id"]) == 1


def test_evaluate_branch_overlay_only_raises(store):
    parent = _seed_parent(store)
    branch = _create(store, parent, [{"key": "slippage_bps", "to": 10}], origin="simulation")
    with pytest.raises(bs.BranchNotEvaluableError):
        bs.evaluate_branch(
            branch["branch_id"], branches_path=store["branches_path"],
            evaluations_path=store["evaluations_path"], pack_root=store["pack_root"],
        )


def test_evaluate_branch_unknown_raises(store):
    with pytest.raises(bs.BranchNotFoundError):
        bs.evaluate_branch("branch_ghost", branches_path=store["branches_path"])


# --------------------------------------------------------------------------- #
# compare                                                                       #
# --------------------------------------------------------------------------- #
def test_compare_branch_before_evaluation_is_prompt_not_error(store):
    parent = _seed_parent(store)
    branch = _create(store, parent, [{"key": "lookback_days", "to": 90}])
    cmp = bs.compare_branch(
        branch["branch_id"], branches_path=store["branches_path"],
        evaluations_path=store["evaluations_path"],
    )
    assert cmp["branch_evaluated"] is False
    assert cmp["decision"] is None
    # parent column filled, branch/delta null (UI prompts "evaluate first").
    row = next(r for r in cmp["metrics"] if r["metric"] == "sharpe")
    assert row["branch"] is None and row["delta"] is None


def test_compare_branch_delta_and_decision(store):
    parent = _seed_parent(store)
    branch = _create(store, parent, [{"key": "lookback_days", "to": 90}])
    bs.evaluate_branch(
        branch["branch_id"], loader=synthetic_loader(n_bars=500),
        branches_path=store["branches_path"], evaluations_path=store["evaluations_path"],
        pack_root=store["pack_root"], ingest=False,
    )
    cmp = bs.compare_branch(
        branch["branch_id"], branches_path=store["branches_path"],
        evaluations_path=store["evaluations_path"],
    )
    assert cmp["branch_evaluated"] is True
    assert cmp["decision"]["verdict"] in {"branch_better", "parent_better", "inconclusive"}
    # Every metric row that has both sides carries a computed delta = branch - parent.
    for r in cmp["metrics"]:
        if r["parent"] is not None and r["branch"] is not None:
            assert r["delta"] == pytest.approx(r["branch"] - r["parent"])


def test_compare_decision_hand_checked():
    """_decision is a pure Sharpe tie-break — verify the three branches by hand."""
    def rows(parent_sharpe, branch_sharpe):
        return [{"metric": "sharpe", "parent": parent_sharpe, "branch": branch_sharpe,
                 "delta": branch_sharpe - parent_sharpe, "change": "x"}]

    assert bs._decision(rows(1.0, 1.5), "Weak", "Promising")["verdict"] == "branch_better"
    assert bs._decision(rows(1.5, 1.0), "Promising", "Weak")["verdict"] == "parent_better"
    assert bs._decision(rows(1.0, 1.0), "Weak", "Weak")["verdict"] == "inconclusive"


def test_compare_branch_unknown_raises(store):
    with pytest.raises(bs.BranchNotFoundError):
        bs.compare_branch("branch_ghost", branches_path=store["branches_path"])


# --------------------------------------------------------------------------- #
# list                                                                          #
# --------------------------------------------------------------------------- #
def test_list_branches_filters_by_strategy_and_parent(store):
    parent = _seed_parent(store)
    b1 = _create(store, parent, [{"key": "lookback_days", "to": 90}])
    b2 = _create(store, parent, [{"key": "top_fraction", "to": 0.25}])
    ids = {b["branch_id"] for b in bs.list_branches(
        strategy="momentum", branches_path=store["branches_path"])}
    assert {b1["branch_id"], b2["branch_id"]} <= ids
    assert bs.list_branches(strategy="inst_flow", branches_path=store["branches_path"]) == []
    by_parent = bs.list_branches(
        parent_evaluation_id=parent["evaluation_id"], branches_path=store["branches_path"])
    assert len(by_parent) == 2
