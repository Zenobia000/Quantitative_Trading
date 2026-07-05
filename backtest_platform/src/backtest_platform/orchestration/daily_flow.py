"""Re-export shim (W5.1c) — moved to ``services.strategy_runtime.daily_flow``."""
from backtest_platform.services.strategy_runtime.daily_flow import (
    FlowContext,
    FlowRun,
    Stage,
    StageResult,
    build_daily_stages,
    demo_stages,
    run_flow,
    stage_etl,
    stage_log,
    stage_orders,
    stage_risk_gate,
    stage_signals,
)

__all__ = [
    "FlowContext",
    "FlowRun",
    "Stage",
    "StageResult",
    "build_daily_stages",
    "demo_stages",
    "run_flow",
    "stage_etl",
    "stage_log",
    "stage_orders",
    "stage_risk_gate",
    "stage_signals",
]
