"""Re-export shim (W5.1a) — moved to ``services.risk_gate.circuit_breaker``."""
from __future__ import annotations

from backtest_platform.services.risk_gate.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    RiskMetrics,
    Transition,
)
from backtest_platform.services.risk_gate.types import BreakerState

__all__ = [
    "BreakerState",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "RiskMetrics",
    "Transition",
]
