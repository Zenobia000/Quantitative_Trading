"""Strategy package — the platform's strategy catalog + registration aggregator.

Importing this package imports every built-in strategy's ``runner`` module, whose
``@register_strategy`` decorator populates the name→runner registry in
``strategies.protocol``. So after ``import backtest_platform.strategies`` the
platform (research / engine / CLI) can resolve any built-in via
``get_strategy(name)`` — no importer needs to know which module to touch.

Why registration lives HERE (dependency-untangle refactor):
    Registration used to be aggregated in ``research.runners`` — an UPPER layer —
    which forced every entry point to import ``research`` just to populate the
    strategy registry (an inverted dependency: the platform reached up into
    research to learn about strategies). The seam belongs where the strategies
    live, so the aggregation moved here. ``research.runners`` is now a thin
    back-compat re-export of the classes below.

To register a new strategy, add one import line below (see
``strategies/_template/README.md``).
"""
from backtest_platform.strategies._template.runner import TemplateRunner
from backtest_platform.strategies.four_layer_resonance.runner import FourLayerRunner
from backtest_platform.strategies.inst_flow.runner import InstFlowRunner
from backtest_platform.strategies.momentum.runner import MomentumRunner
from backtest_platform.strategies.reversal.runner import ReversalRunner

__all__ = [
    "FourLayerRunner",
    "InstFlowRunner",
    "MomentumRunner",
    "ReversalRunner",
    "TemplateRunner",
]
