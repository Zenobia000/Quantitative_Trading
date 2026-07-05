"""Research loop (v0.1): RunConfig + IS harness + runs ledger.

run_is(RunConfig) -> metrics -> evaluate_gate (validation.gate_state) -> ledger.
The productized form of scripts/v3_double_window_is.py: one disciplined,
hypothesis-pre-registered, lineage-bearing command instead of one-off scripts.
"""
from backtest_platform.research.batch import expand_stock_groups, run_batch
from backtest_platform.research.compare import CompareReport, RunComparison, compare_runs, rank_by
from backtest_platform.research.is_harness import run_and_judge, run_is
from backtest_platform.research.run_config import RunConfig
from backtest_platform.research.run_persist import persist_run
from backtest_platform.research.runs_store import append_run, read_runs
from backtest_platform.research.sweep import expand_grid, run_sweep, to_heatmap

__all__ = [
    "RunConfig", "run_is", "run_and_judge", "append_run", "persist_run", "read_runs",
    "expand_grid", "run_sweep", "to_heatmap",
    "expand_stock_groups", "run_batch",
    "compare_runs", "rank_by", "CompareReport", "RunComparison",
]
