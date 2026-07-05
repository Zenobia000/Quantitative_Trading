"""Dynamic loader for per-strategy ``research_config.py`` modules (ADR-029).

A strategy participates in the research workflows by declaring
``strategies/<pkg>/research_config.py`` with module-level ``DOE`` / ``GO_GATES`` /
``TRUTH_GATE`` / ``PAPER_REPLAY`` constants. This loader resolves a registered
strategy *name* to its package via the dispatch registry — NOT by assuming the
name equals the directory (it doesn't: ``four_layer`` lives in
``four_layer_resonance/``, ``template`` in ``_template/``).
"""
from __future__ import annotations

import importlib
from types import ModuleType

# Import side-effect: register the built-in strategies so get_strategy resolves.
from backtest_platform.research import runners as _runners  # noqa: F401
from backtest_platform.research.workflows.config import (
    DOEConfig,
    GOGatesConfig,
    PaperReplayConfig,
    TruthGateConfig,
    UniverseConfig,
)
from backtest_platform.strategies.protocol import get_strategy

_WORKFLOW_ATTRS: dict[str, tuple[str, type]] = {
    "doe": ("DOE", DOEConfig),
    "go_gates": ("GO_GATES", GOGatesConfig),
    "truth_gate": ("TRUTH_GATE", TruthGateConfig),
    "paper_replay": ("PAPER_REPLAY", PaperReplayConfig),
}


def load_research_config(strategy_name: str) -> ModuleType:
    """Import ``research_config.py`` from the strategy's package.

    Resolves name→package via the registry (the runner's ``__module__``), so the
    name need not match the directory. Unknown strategy or missing module both
    surface as a single "no research_config" ``ValueError`` with the fix hint.
    """
    try:
        runner = get_strategy(strategy_name)               # ValueError if unknown name
        package = type(runner).__module__.rsplit(".", 1)[0]  # ...<pkg>.runner → ...<pkg>
        return importlib.import_module(f"{package}.research_config")
    except (ValueError, ModuleNotFoundError):
        raise ValueError(
            f"strategy {strategy_name!r} has no research_config.py — "
            f"copy from strategies/_template/research_config.py and fill in values"
        ) from None


def get_doe_config(strategy_name: str) -> DOEConfig:
    return _get_attr(strategy_name, "doe")


def get_go_gates_config(strategy_name: str) -> GOGatesConfig:
    return _get_attr(strategy_name, "go_gates")


def get_truth_gate_config(strategy_name: str) -> TruthGateConfig:
    return _get_attr(strategy_name, "truth_gate")


def get_paper_replay_config(strategy_name: str) -> PaperReplayConfig:
    return _get_attr(strategy_name, "paper_replay")


def get_universe_config(strategy_name: str) -> UniverseConfig:
    """The strategy's ``UNIVERSE`` build declaration (ADR-032).

    Kept out of ``_WORKFLOW_ATTRS`` (and thus ``list_workflow_configs``) on purpose:
    ``build_universe`` is a data-prep workflow, not one of the strategy-research
    workflows that drive ``get_strategy(name).run()``.
    """
    mod = load_research_config(strategy_name)
    if not hasattr(mod, "UNIVERSE"):
        raise AttributeError(
            f"strategy {strategy_name!r} research_config.py has no 'UNIVERSE' — "
            f"declare a UniverseConfig to use the build-universe workflow"
        )
    obj = mod.UNIVERSE
    if not isinstance(obj, UniverseConfig):
        raise TypeError(
            f"{strategy_name}/research_config.UNIVERSE must be UniverseConfig, "
            f"got {type(obj).__name__}"
        )
    return obj


def list_workflow_configs(strategy_name: str) -> list[str]:
    """Workflow names this strategy declares (``research_config.py`` constants present)."""
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
