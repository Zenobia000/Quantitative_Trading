"""Batch fan-out for research runs (A1 — parallel run launcher).

Expands one base spec × N stock groups into deterministic RunConfigs and runs
them through a bounded ThreadPoolExecutor. Each run mirrors its lifecycle to
the runs table (running → done|failed, best-effort) so the run board reads
live state straight from SQL; completed records land in the JSONL ledger via
``persist_run`` exactly like a single run.

Threads, not processes: the sim is pandas/numpy-heavy (C ops release the GIL)
and a 90-day / ≤2-symbol window runs in seconds — process-pool pickling and
per-process DB connections aren't worth it at this scale. The existing job
runner (``jobs/job_runner.py``) stays the API-side async path; this module is
the research-side fan-out with a concurrency bound.
"""
from __future__ import annotations

import threading
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from backtest_platform.research.run_config import RunConfig
from backtest_platform.research.run_persist import mark_run_status, persist_run
from backtest_platform.research.runs_store import DEFAULT_RUNS_PATH


def expand_stock_groups(
    base: Mapping[str, Any], stock_groups: Sequence[Sequence[str]]
) -> list[RunConfig]:
    """One RunConfig per stock group, sharing ``base`` (strategy/params/window/
    hypothesis). Identical groups collapse via the deterministic run_id —
    re-listing a group can never double-run it. Empty groups fail fast."""
    configs: list[RunConfig] = []
    seen: set[str] = set()
    for group in stock_groups:
        stocks = tuple(group)
        if not stocks:
            raise ValueError("empty stock group in batch spec")
        cfg = RunConfig(**dict(base), stocks=stocks)
        if cfg.run_id not in seen:
            seen.add(cfg.run_id)
            configs.append(cfg)
    return configs


def run_batch(
    configs: Sequence[RunConfig],
    *,
    executor: Callable[[RunConfig], dict] | None = None,
    runs_path: Path | str = DEFAULT_RUNS_PATH,
    writer: Any = None,
    max_workers: int = 4,
) -> list[dict]:
    """Run every config through ``executor`` in a bounded thread pool.

    Returns one result dict per config, in input order: the ledger record plus
    ``batch_status='done'``, or ``{run_id, batch_status='failed', error}`` when
    that run raised (failures are isolated — the batch always completes).
    A failed run is marked ``status='failed'`` in the runs table and never
    reaches the ledger. ``executor``/``writer`` are injectable for tests;
    the default executor is the real IS pipeline (``run_and_judge_persist``).
    """
    if max_workers < 1:
        raise ValueError(f"max_workers must be >= 1, got {max_workers}")
    if not configs:
        return []
    if executor is None:
        from backtest_platform.research.is_harness import (
            run_and_judge_persist as executor,
        )

    # Ledger appends from worker threads are serialized: a JSONL line must hit
    # the file as one uninterleaved write, and Python's buffered append gives
    # no cross-thread guarantee for records larger than the I/O buffer.
    ledger_lock = threading.Lock()

    def _one(cfg: RunConfig) -> dict:
        mark_run_status(cfg, "running", writer=writer)
        try:
            record = executor(cfg)
        except Exception as exc:  # noqa: BLE001 — isolated into the result row
            mark_run_status(cfg, "failed", writer=writer)
            return {"run_id": cfg.run_id, "batch_status": "failed", "error": str(exc)}
        with ledger_lock:
            persist_run(record, runs_path, writer=writer)
        return {**record, "batch_status": "done"}

    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(_one, configs))
