"""Explicit no-data signal shared by the live reader and the after-close scheduler.

Kept dependency-free (stdlib only) on purpose: the after-close scheduler core
imports this to catch *one specific* condition — "the calendar said trading day but
the data source has no row for this as-of" — without pulling pandas / FinLab into
its import path. That precision matters: a weekday Taiwan public holiday (the
approximate Mon–Fri calendar's blind spot) yields a live panel whose newest row is
the PRIOR session; running the chain on it would place orders on stale data. This
signal lets the scheduler degrade to a benign skip instead of a FAILED alert, while
genuine failures still surface loudly.
"""
from __future__ import annotations

from datetime import date


class NoMarketDataError(RuntimeError):
    """Raised when a session's as-of date has no market data yet.

    A benign, expected condition (approximate-calendar false positive or an ad-hoc
    TWSE halt) — NOT a pipeline failure. Carries ``strategy`` / ``as_of`` so the
    caller can degrade to an informational skip rather than an error alert.
    """

    def __init__(self, strategy: str, as_of: date, detail: str = "") -> None:
        self.strategy = strategy
        self.as_of = as_of
        self.detail = detail
        message = f"no market data for {strategy} @ {as_of}"
        if detail:
            message += f" — {detail}"
        super().__init__(message)
