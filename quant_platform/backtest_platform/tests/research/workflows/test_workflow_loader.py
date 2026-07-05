"""workflow.loader — resolve a strategy name to its research_config declarations."""
from __future__ import annotations

import pytest

from backtest_platform.research.workflows.config import DOEConfig
from backtest_platform.research.workflows.loader import (
    get_doe_config,
    list_workflow_configs,
    load_research_config,
)


def test_load_inst_flow_research_config():
    mod = load_research_config("inst_flow")
    assert hasattr(mod, "DOE")
    assert hasattr(mod, "GO_GATES")
    assert hasattr(mod, "TRUTH_GATE")
    assert hasattr(mod, "PAPER_REPLAY")


def test_load_momentum_research_config():
    mod = load_research_config("momentum")
    assert hasattr(mod, "DOE")


def test_load_reversal_research_config():
    mod = load_research_config("reversal")
    assert hasattr(mod, "DOE")
    assert hasattr(mod, "GO_GATES")
    assert hasattr(mod, "TRUTH_GATE")
    assert hasattr(mod, "PAPER_REPLAY")


def test_list_workflow_configs_reversal():
    workflows = list_workflow_configs("reversal")
    assert {"doe", "go_gates", "truth_gate", "paper_replay"} == set(workflows)


def test_unknown_strategy_raises():
    with pytest.raises(ValueError, match="no research_config"):
        load_research_config("nonexistent_xyz")


def test_get_doe_config_returns_doe_config():
    cfg = get_doe_config("inst_flow")
    assert isinstance(cfg, DOEConfig)
    assert cfg.strategy == "inst_flow"


def test_get_undeclared_workflow_raises_attributeerror():
    # four_layer declares only DOE (ADR-023) — GO_GATES is intentionally absent
    from backtest_platform.research.workflows.loader import get_go_gates_config
    with pytest.raises(AttributeError, match="GO_GATES"):
        get_go_gates_config("four_layer")


def test_list_workflow_configs_inst_flow():
    workflows = list_workflow_configs("inst_flow")
    assert {"doe", "go_gates", "truth_gate", "paper_replay"} == set(workflows)


def test_list_workflow_configs_template():
    workflows = list_workflow_configs("template")
    assert "doe" in workflows


def test_list_workflow_configs_four_layer_only_doe():
    workflows = list_workflow_configs("four_layer")
    assert workflows == ["doe"]
