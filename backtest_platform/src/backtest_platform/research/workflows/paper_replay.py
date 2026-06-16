"""Paper replay workflow — run fixed_config through dispatch and persist."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from backtest_platform.research import runners as _runners  # noqa: F401
from backtest_platform.research.is_harness import load_merged_parquet
from backtest_platform.research.workflows.config import PaperReplayConfig
from backtest_platform.strategies.conformance import Loader
from backtest_platform.strategies.protocol import get_strategy
from backtest_platform.validation.gate_state import evaluate_gate


@dataclass(frozen=True)
class PaperReplayResult:
    strategy:    str
    run_id:      str
    gate_status: str
    metrics:     dict


def run_paper_replay_workflow(
    cfg: PaperReplayConfig,
    loader: Loader = load_merged_parquet,
) -> PaperReplayResult:
    """Run fixed_config on [as_of - buffer, as_of] and judge via the gate.

    Uses the ADR-028 dispatch layer (runner.run) — does not wire up the full
    orchestration chain (TimescaleDB, signals daemon). Use the runtime daemon
    for production forward-live paper trading.
    """
    runner       = get_strategy(cfg.strategy)
    sconf        = runner.config_model(**cfg.fixed_config.model_dump())
    window_start = cfg.as_of - timedelta(days=cfg.lookback_buffer_days)
    run_result   = runner.run(list(cfg.symbols), window_start, cfg.as_of, sconf, loader)
    gate_result  = evaluate_gate(run_result.metrics)
    run_id       = f"{cfg.run_id_prefix}_{cfg.strategy}_{cfg.as_of:%Y%m%d}"

    return PaperReplayResult(
        strategy=cfg.strategy,
        run_id=run_id,
        gate_status=gate_result.status.value,
        metrics=run_result.metrics,
    )
