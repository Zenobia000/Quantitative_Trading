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
"""
# Auto-register bundles on package import — zipline's `register()` writes to
# a process-global registry, so importing this once is enough for the CLI.
from backtest_platform.engines.zipline_adapter.bundles import (  # noqa: F401
    finmind_bundle,
)
