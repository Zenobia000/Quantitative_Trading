"""Research workflow platform services — DOE / GO gates / truth gate / paper replay.

Generic, strategy-agnostic workflows (ADR-029). Every workflow drives the
ADR-028 dispatch layer (``get_strategy(name).run(...)``) and reads its parameters
from the strategy's own ``research_config.py`` — so adding a strategy to all
workflows needs zero new workflow code.
"""
