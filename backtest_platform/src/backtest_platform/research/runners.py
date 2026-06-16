"""Strategy runner aggregator (ADR-027).

Each strategy's runner now lives WITH its strategy in
``strategies/<name>/runner.py`` — a self-contained authoring unit (config + pure
logic + runner). Importing this module imports every built-in runner, which
triggers their ``@register_strategy`` registration, so the platform
(research / engine / CLI) can resolve any strategy via ``get_strategy(name)``.

To register a new strategy, add one import line below (see
``strategies/_template/README.md``). This file also re-exports the panel helpers
that used to live here, so existing importers keep working.
"""
from backtest_platform.strategies._template.runner import TemplateRunner
from backtest_platform.strategies.common.panel import (
    column_panel as _column_panel,
)
from backtest_platform.strategies.common.panel import (
    flow_panels as _flow_panels,
)
from backtest_platform.strategies.common.panel import (
    panel_metrics as _panel_metrics,
)
from backtest_platform.strategies.four_layer_resonance.runner import FourLayerRunner
from backtest_platform.strategies.inst_flow.runner import InstFlowRunner
from backtest_platform.strategies.momentum.runner import MomentumRunner

__all__ = [
    "FourLayerRunner",
    "InstFlowRunner",
    "MomentumRunner",
    "TemplateRunner",
    "_column_panel",
    "_flow_panels",
    "_panel_metrics",
]
