"""zipline-reloaded adapter (M2, ADR-013).

Wraps zipline-reloaded as M2 backtest engine. Importing this package
auto-registers our custom bundles with zipline's bundle registry so
`zipline ingest -b finmind` works without manual extension.py setup.

Module map:
    bundles/        FinMind/parquet ingesters (zipline bundle registry)
    algorithms/     Wrap M1 pure functions as zipline TradingAlgorithm
    controls/       Taiwan stock rules (price limits, fees, tax)
    multi_strategy/ Multi-algorithm result aggregation
    adapters/       Broker adapters (paper / Shioaji live)
    validation/     Cross-check against M1 pipeline / vectorbt
    cli.py          Click entry: backtest-run / paper-run / live-run

Bundle registration is now an EXPLICIT call — ``finmind_bundle.ensure_registered()``
invoked at the zipline entry points (``cli.py`` before ``run_algorithm`` /
``list-bundles``) — NOT an import-time side-effect of this package
(dependency-untangle refactor). Importing this package therefore no longer mutates
zipline's process-global bundle registry (nor requires zipline to be importable);
call ``ensure_registered()`` before any ``run_algorithm`` / ``zipline ingest -b
finmind``.
"""
