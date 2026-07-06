"""Run-Report v1 aggregations — pure functions, no IO.

Two chart-backing transforms the ``GET /runs/{id}/report`` endpoint needs, plus a
DSR-band classifier. Kept here (``validation/``) so they are unit-testable against
hand-computed oracles and reusable by a CLI / tear-sheet path, exactly like the
sibling ``validation.metrics`` primitives.

Why new functions (and not ``metrics`` / ``tearsheet``)
-------------------------------------------------------
``validation.metrics`` has ``max_drawdown`` (a single scalar) and a private
per-period drawdown series — neither yields the *table of discrete drawdown
events* (peak/trough/recovery) the report needs. ``validation.tearsheet`` produces
a monthly heat-map only via optional quantstats (returns ``{}`` when the extra is
absent), so it cannot back a contract endpoint that must always answer. These two
functions fill that gap dependency-free (stdlib + pandas already in core).

Date handling
-------------
``monthly_returns_matrix`` keys off a real ``DatetimeIndex`` on the returns Series.
The v1 series sidecar (``run_series_store``) persists equity/drawdown as bare float
lists WITHOUT a date index, so the endpoint reconstructs an approximate business-day
index across the run window before calling here (disclosed via a ``basis`` field on
the payload). The returns/depths themselves are genuine; only the date *labels* are
reconstructed — never fabricated values.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

import pandas as pd

from quant_platform.services.research_validation.validation.two_stage_gate import DSR_MIN, PAPER_WATCH_DSR_MIN

__all__ = ["drawdown_events", "dsr_band", "monthly_returns_matrix"]


def monthly_returns_matrix(returns: pd.Series) -> dict[str, Any]:
    """Year×month compounded-return grid from a date-indexed daily-returns Series.

    Each cell is the month's compounded return ``prod(1 + r) - 1``; a month with no
    observation is ``None`` (never ``0.0`` — a real flat month and a no-data month
    must read differently). ``annual`` is the same compounding over each whole year.

    Returns ``{"years": [...], "matrix": [[12 cells], ...], "annual": [...]}``; an
    empty Series yields empty lists. The Series index must be datetime-like (the
    caller reconstructs it from the run window when the sidecar lacks dates).
    """
    r = pd.Series(returns, dtype=float).dropna()
    if r.empty:
        return {"years": [], "matrix": [], "annual": []}

    idx = pd.to_datetime(r.index)
    frame = pd.DataFrame({"ret": r.to_numpy()}, index=idx)
    frame["year"] = frame.index.year
    frame["month"] = frame.index.month

    years = sorted(int(y) for y in frame["year"].unique())
    matrix: list[list[float | None]] = []
    annual: list[float] = []
    for y in years:
        year_rows = frame[frame["year"] == y]
        row: list[float | None] = [None] * 12
        for m in range(1, 13):
            cells = year_rows.loc[year_rows["month"] == m, "ret"]
            if not cells.empty:
                row[m - 1] = float((1.0 + cells).prod() - 1.0)
        matrix.append(row)
        annual.append(float((1.0 + year_rows["ret"]).prod() - 1.0))
    return {"years": years, "matrix": matrix, "annual": annual}


def drawdown_events(
    equity: Sequence[float],
    dates: Sequence[str] | None = None,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    """Top-``N`` discrete drawdown events from an equity curve (deepest first).

    An event opens the bar equity first dips below a running peak and closes when
    equity reclaims that peak (``recovered=True``); an event still under water at
    the last bar is reported with ``recovery_idx=None`` / ``recovered=False``. Each
    event carries integer bar positions (always exact) plus optional ISO date
    labels when ``dates`` is supplied (same length as ``equity``).

    ``depth`` is the positive fraction ``(peak - trough) / peak``; ``duration_bars``
    counts peak→recovery (recovered) or peak→last-bar (still under water).
    """
    eq = [float(x) for x in equity]
    n = len(eq)
    if n == 0:
        return []

    def _label(i: int | None) -> str | None:
        if i is None or dates is None or i >= len(dates):
            return None
        return str(dates[i])

    events: list[dict[str, Any]] = []
    peak = eq[0]
    peak_idx = 0
    in_dd = False
    trough = eq[0]
    trough_idx = 0

    def _close(recovery_idx: int | None) -> None:
        peak_val = eq[peak_idx]
        depth = (peak_val - trough) / peak_val if peak_val else 0.0
        end = recovery_idx if recovery_idx is not None else n - 1
        events.append(
            {
                "peak_idx": peak_idx,
                "trough_idx": trough_idx,
                "recovery_idx": recovery_idx,
                "peak_date": _label(peak_idx),
                "trough_date": _label(trough_idx),
                "recovery_date": _label(recovery_idx),
                "depth": depth,
                "duration_bars": end - peak_idx,
                "recovered": recovery_idx is not None,
            }
        )

    for i in range(1, n):
        if eq[i] >= peak:  # new high → reclaims any open drawdown
            if in_dd:
                _close(recovery_idx=i)
                in_dd = False
            peak = eq[i]
            peak_idx = i
        else:
            if not in_dd:
                in_dd = True
                trough = eq[i]
                trough_idx = i
            elif eq[i] < trough:
                trough = eq[i]
                trough_idx = i
    if in_dd:  # ended under water — never recovered
        _close(recovery_idx=None)

    events.sort(key=lambda e: e["depth"], reverse=True)
    return events[:top_n]


def dsr_band(dsr: float | None) -> str | None:
    """Classify a Deflated Sharpe Ratio into its ADR-025/033 deploy band.

    ``>= DSR_MIN`` (0.95) → ``"REAL"`` (deployable); ``[0.90, 0.95)`` →
    ``"PAPER_WATCH"`` (zero-capital observation艙); ``< 0.90`` → ``"REJECTED"``.
    ``None`` in → ``None`` out (an unknown DSR is never fabricated into a band).
    Thresholds are the single source of truth in ``two_stage_gate`` (data, not
    re-derived here).
    """
    if dsr is None or (isinstance(dsr, float) and not math.isfinite(dsr)):
        return None
    if dsr >= DSR_MIN:
        return "REAL"
    if dsr >= PAPER_WATCH_DSR_MIN:
        return "PAPER_WATCH"
    return "REJECTED"
