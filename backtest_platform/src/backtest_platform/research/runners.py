"""Strategy runner re-export — the live strategy-registration seam.

NOT a deprecated shim: importing this module is the canonical way ~12 production
call sites (``research.is_harness``, ``research.cli``, ``research.batch``, the
workflows, tests) trigger every built-in runner's ``@register_strategy``
side-effect. Removing it would silently empty the strategy registry. Keep it.

Strategy registration now lives in ``strategies/__init__.py`` (the seam belongs
with the strategies, not up here in research). This module used to BE the
aggregator; it is now a thin re-export so existing import paths keep working:

- ``from backtest_platform.research.runners import MomentumRunner, _column_panel``
- ``import backtest_platform.research.runners  # noqa: F401  # registers built-ins``

Importing this module imports the ``strategies`` package, which triggers every
built-in runner's ``@register_strategy`` side-effect — so the historical
"import runners to register" contract is preserved.
"""
# Re-export the runner classes (in ``__all__`` below) — importing this also imports
# the ``strategies`` package, which registers every built-in via side-effect.
from backtest_platform.strategies import (
    FourLayerRunner,
    InstFlowRunner,
    MomentumRunner,
    ReversalRunner,
    TemplateRunner,
)
from backtest_platform.strategies.common.panel import (
    column_panel as _column_panel,
)
from backtest_platform.strategies.common.panel import (
    flow_panels as _flow_panels,
)
from backtest_platform.strategies.common.panel import (
    panel_metrics as _panel_metrics,
)

__all__ = [
    "FourLayerRunner",
    "InstFlowRunner",
    "MomentumRunner",
    "ReversalRunner",
    "TemplateRunner",
    "_column_panel",
    "_flow_panels",
    "_panel_metrics",
]
