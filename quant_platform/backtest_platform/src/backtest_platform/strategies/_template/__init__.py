"""TEMPLATE strategy package — copy this folder to author a new strategy.

See ``strategy.py`` for the step-by-step + the I/O contract, ``runner.py`` for the
4-line platform adapter, and ``README.md`` for the checklist. Registered as
``"template"`` (a working equal-weight buy-and-hold baseline).
"""
from backtest_platform.strategies._template.strategy import (
    TemplateConfig,
    TemplateResult,
    backtest_template,
)

__all__ = ["TemplateConfig", "TemplateResult", "backtest_template"]
