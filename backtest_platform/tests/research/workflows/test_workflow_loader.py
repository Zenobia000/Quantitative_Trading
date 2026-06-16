import pytest
from backtest_platform.research.workflows.loader import (
    load_research_config, get_doe_config, get_go_gates_config,
    get_truth_gate_config, get_paper_replay_config, list_workflow_configs,
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

def test_unknown_strategy_raises():
    with pytest.raises(ValueError, match="no research_config"):
        load_research_config("nonexistent_xyz")

def test_get_doe_config_returns_doe_config():
    from backtest_platform.research.workflows.config import DOEConfig
    cfg = get_doe_config("inst_flow")
    assert isinstance(cfg, DOEConfig)
    assert cfg.strategy == "inst_flow"

def test_list_workflow_configs_inst_flow():
    workflows = list_workflow_configs("inst_flow")
    assert "doe" in workflows
    assert "go_gates" in workflows
    assert "truth_gate" in workflows
    assert "paper_replay" in workflows

def test_list_workflow_configs_template():
    workflows = list_workflow_configs("template")
    assert "doe" in workflows

def test_missing_attr_raises_attribute_error():
    # four_layer only has DOE, not GO_GATES
    with pytest.raises(AttributeError, match="GO_GATES"):
        get_go_gates_config("four_layer")
