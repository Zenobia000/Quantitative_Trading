"""Research workflow platform services — DOE / GO gates / truth gate / paper replay
plus the ``build_universe`` data-prep workflow (ADR-032).

Generic, strategy-agnostic workflows (ADR-029). The strategy-research workflows drive
the ADR-028 dispatch layer (``get_strategy(name).run(...)``); ``build_universe`` is a
data-prep step (survivorship-clean FinLab ingest) rather than a backtest run, but
follows the same declare-then-execute contract (a ``UniverseConfig`` in the strategy's
``research_config.py``). Adding a strategy to all workflows needs zero new workflow code.
"""
