"""Research loop (v0.1): RunConfig + IS harness + runs ledger.

run_is(RunConfig) -> metrics -> evaluate_gate (validation.gate_state) -> ledger.
The productized form of scripts/v3_double_window_is.py: one disciplined,
hypothesis-pre-registered, lineage-bearing command instead of one-off scripts.
"""
from backtest_platform.research.is_harness import run_and_judge, run_is
from backtest_platform.research.run_config import RunConfig
from backtest_platform.research.runs_store import append_run, read_runs

__all__ = ["RunConfig", "run_is", "run_and_judge", "append_run", "read_runs"]
