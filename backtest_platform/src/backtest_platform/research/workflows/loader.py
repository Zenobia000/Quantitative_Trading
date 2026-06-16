"""Dynamic loader for per-strategy research_config modules."""
from __future__ import annotations

import importlib
import importlib.util

from backtest_platform.research.workflows.config import (
    DOEConfig, GOGatesConfig, TruthGateConfig, PaperReplayConfig,
)

_WORKFLOW_ATTRS: dict[str, tuple[str, type]] = {
    "doe":          ("DOE",          DOEConfig),
    "go_gates":     ("GO_GATES",     GOGatesConfig),
    "truth_gate":   ("TRUTH_GATE",   TruthGateConfig),
    "paper_replay": ("PAPER_REPLAY", PaperReplayConfig),
}


def _research_config_path(strategy_name: str) -> str:
    """Derive the research_config module path from the strategy's runner location.

    Strategy registry name (e.g. "four_layer") may differ from module folder name
    (e.g. "four_layer_resonance"). We ask the runner for its own module path and
    derive the sibling research_config from there.
    """
    from backtest_platform.research import runners as _r  # noqa: F401
    from backtest_platform.strategies.protocol import get_strategy
    try:
        runner  = get_strategy(strategy_name)
        # runner.__class__.__module__ == "...strategies.four_layer_resonance.runner"
        pkg = ".".join(runner.__class__.__module__.split(".")[:-1])
        return f"{pkg}.research_config"
    except ValueError:
        # Unknown strategy — build a path that will produce a nice error below
        return f"backtest_platform.strategies.{strategy_name}.research_config"


def load_research_config(strategy_name: str):
    """Dynamically import this strategy's ``research_config.py``."""
    module_path = _research_config_path(strategy_name)

    # Use find_spec to distinguish "file doesn't exist" from "dependency missing"
    try:
        spec = importlib.util.find_spec(module_path)
    except ModuleNotFoundError:
        spec = None
    if spec is None:
        raise ValueError(
            f"strategy {strategy_name!r} has no research_config.py — "
            f"copy from strategies/_template/research_config.py and fill in values"
        )
    return importlib.import_module(module_path)


def get_doe_config(strategy_name: str) -> DOEConfig:
    return _get_attr(strategy_name, "doe")

def get_go_gates_config(strategy_name: str) -> GOGatesConfig:
    return _get_attr(strategy_name, "go_gates")

def get_truth_gate_config(strategy_name: str) -> TruthGateConfig:
    return _get_attr(strategy_name, "truth_gate")

def get_paper_replay_config(strategy_name: str) -> PaperReplayConfig:
    return _get_attr(strategy_name, "paper_replay")

def list_workflow_configs(strategy_name: str) -> list[str]:
    """List which workflow configs are declared by this strategy."""
    mod = load_research_config(strategy_name)
    return [wf for wf, (attr, _) in _WORKFLOW_ATTRS.items() if hasattr(mod, attr)]


def _get_attr(strategy_name: str, workflow: str):
    attr_name, expected_type = _WORKFLOW_ATTRS[workflow]
    mod = load_research_config(strategy_name)
    if not hasattr(mod, attr_name):
        raise AttributeError(
            f"strategy {strategy_name!r} research_config.py has no {attr_name!r} — "
            f"see _template/research_config.py for the required structure"
        )
    obj = getattr(mod, attr_name)
    if not isinstance(obj, expected_type):
        raise TypeError(
            f"{strategy_name}/research_config.{attr_name} must be {expected_type.__name__}, "
            f"got {type(obj).__name__}"
        )
    return obj
