"""Shared risk types.

Single canonical ``BreakerState`` for the whole ``risk`` package. Hoisted here to
close a CRITICAL integration hole: ``circuit_breaker`` latches the tripped breaker
into the terminal ``HALTED`` state, so ``risk_gate.check_ex012`` MUST reject orders
on ``HALTED`` (and ``L3``) — a divergent per-module enum let halted-state orders
slip through.
"""
from __future__ import annotations

from enum import Enum


class BreakerState(str, Enum):
    """Discrete breaker levels, ordered by severity (spec 24 §4).

    ``L3`` is the transient "fully tripped" classification produced by
    ``CircuitBreaker.evaluate``; the machine immediately latches it into the
    terminal ``HALTED`` state, which only ``CircuitBreaker.reset`` clears.
    ``severity`` gives a monotonic ordering. Both ``L3`` and ``HALTED`` are a
    full stop — ``risk_gate`` EX-012 rejects all orders in either.
    """

    NORMAL = "normal"
    L1 = "l1_pause"
    L2 = "l2_cut"
    L3 = "l3_halt"
    HALTED = "halted"

    @property
    def severity(self) -> int:
        return _SEVERITY[self]


_SEVERITY: dict[BreakerState, int] = {
    BreakerState.NORMAL: 0,
    BreakerState.L1: 1,
    BreakerState.L2: 2,
    BreakerState.L3: 3,
    BreakerState.HALTED: 3,
}
