"""research.evaluation.profiles — registry + contract fidelity (rebuild Goal 3)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from quant_platform.services.research_validation.evaluation.profiles import (
    EvaluationProfile,
    get_profile,
    list_profile_names,
    list_profiles,
)
from quant_platform.services.research_validation.evaluation.profiles import _BUILTIN_DICTS  # type: ignore

_CONTRACT = (
    Path(__file__).resolve().parents[3]
    / "packages" / "contracts" / "schemas" / "evaluation_profile.schema.json"
)


def test_four_builtins_registered():
    names = list_profile_names()
    assert names == ["quick_triage", "fixed_hypothesis_oos", "grid_search_selection", "deployment_strict"]


def test_list_profiles_returns_models():
    profiles = list_profiles()
    assert len(profiles) == 4
    assert all(isinstance(p, EvaluationProfile) for p in profiles)


def test_get_profile_resolves():
    p = get_profile("quick_triage")
    assert p.name == "quick_triage"
    assert p.stage == "triage"
    assert p.run_mode == "single_config"
    assert p.wraps_primitives == ("single_run",)


def test_get_profile_unknown_raises():
    with pytest.raises(ValueError, match="unknown evaluation profile"):
        get_profile("does_not_exist")


def test_deployment_strict_wraps_truth_gate_only():
    p = get_profile("deployment_strict")
    assert p.wraps_primitives == ("truth_gate",)
    assert p.stage == "deployment"
    assert p.live_oos_policy.default_recommendation == "blocked"


def test_builtins_match_contract_examples_exactly():
    """The Python built-ins must be byte-identical to the schema examples[] (single truth)."""
    schema = json.loads(_CONTRACT.read_text(encoding="utf-8"))
    examples = {ex["name"]: ex for ex in schema["examples"]}
    assert set(examples) == {d["name"] for d in _BUILTIN_DICTS}
    for d in _BUILTIN_DICTS:
        assert d == examples[d["name"]], f"profile {d['name']} drifted from the contract example"


def test_every_gate_has_severity():
    for p in list_profiles():
        for g in p.gates:
            assert g.severity in ("info", "warn", "block_live_oos", "block_deploy")


def test_all_profiles_emit_five_scorecards():
    for p in list_profiles():
        assert set(p.scorecards) == {"profitability", "risk", "risk_adjusted", "win_rate", "liquidity"}
