"""quantstats HTML tear sheet integration (dev_docs 6.1.2).

Turns a strategy's *daily returns* series into a self-contained quantstats
HTML tear sheet (equity curve, drawdown, monthly heatmap, the full metrics
table) plus a flat ``dict`` of headline statistics for programmatic use.

quantstats is an **optional** dependency, shipped in the ``validation`` extra
(``pyproject.toml`` ``[project.optional-dependencies].validation``). This module
therefore degrades gracefully: if quantstats is not importable, or the input is
too small to produce a meaningful report (``< 2`` bars), the public functions
log a warning and return ``None`` / ``{}`` instead of raising. A missing report
must never crash the validation pipeline that calls it.

Public API
----------
- ``write_tearsheet(daily_returns, output_path, title="") -> Path | None``
- ``summary_stats(daily_returns) -> dict[str, float]``

Both accept a ``pd.Series`` of *period returns* (not an equity curve). The index
is coerced to a ``DatetimeIndex`` when possible, because quantstats keys most of
its time-based aggregations (monthly/yearly tables) off real dates.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

__all__ = ["summary_stats", "write_tearsheet"]

# Minimum bars for quantstats to compute anything non-degenerate. A single
# observation has no variance / no drawdown, and quantstats' resampling helpers
# raise on length-1 input — so we gate before ever calling into the library.
_MIN_BARS: int = 2

# Headline stats surfaced by ``summary_stats``. Name → quantstats.stats attr.
# Kept small and stable so callers (dashboard, run records) can rely on the keys.
_SUMMARY_FIELDS: tuple[tuple[str, str], ...] = (
    ("sharpe", "sharpe"),
    ("sortino", "sortino"),
    ("cagr", "cagr"),
    ("volatility", "volatility"),
    ("max_drawdown", "max_drawdown"),
    ("calmar", "calmar"),
    ("win_rate", "win_rate"),
    ("profit_factor", "profit_factor"),
    ("total_return", "comp"),
)


def _coerce_returns(daily_returns: pd.Series) -> pd.Series | None:
    """Clean the series and ensure a ``DatetimeIndex``; ``None`` if unusable.

    - Drops NaNs (quantstats propagates them into the metrics table).
    - If the index is not already datetime-like, attempts ``pd.to_datetime``;
      on failure, synthesizes a business-day index so the report still renders.
    - Returns ``None`` when fewer than ``_MIN_BARS`` clean observations remain.
    """
    if daily_returns is None:
        return None

    series = pd.Series(daily_returns, dtype=float).dropna()
    if len(series) < _MIN_BARS:
        return None

    if not isinstance(series.index, pd.DatetimeIndex):
        try:
            series.index = pd.to_datetime(series.index)
        except (ValueError, TypeError):
            # A plain RangeIndex (or other non-date labels) — fabricate dates so
            # quantstats' date-keyed aggregations have something to bucket on.
            series.index = pd.date_range(
                "2000-01-03", periods=len(series), freq="B"
            )

    if series.name is None:
        series = series.rename("strategy")
    return series


def write_tearsheet(
    daily_returns: pd.Series,
    output_path: str | Path,
    title: str = "",
) -> Path | None:
    """Render a quantstats HTML tear sheet to ``output_path``.

    Parameters
    ----------
    daily_returns:
        Series of *period* returns (e.g. daily). The index is coerced to a
        ``DatetimeIndex`` when it is not already one.
    output_path:
        Destination ``.html`` path (``str`` or ``Path``). Parent directories are
        created if missing.
    title:
        Optional tear-sheet title; defaults to ``"Strategy Tearsheet"`` inside
        quantstats when left empty.

    Returns
    -------
    Path | None
        The written path on success, or ``None`` if quantstats is unavailable,
        the input has ``< 2`` clean bars, or rendering fails — each case logs a
        warning rather than raising.
    """
    series = _coerce_returns(daily_returns)
    if series is None:
        logger.warning(
            "write_tearsheet: insufficient data (< %d clean bars); skipping report.",
            _MIN_BARS,
        )
        return None

    try:
        import quantstats as qs
    except ImportError:
        logger.warning(
            "write_tearsheet: quantstats not installed (validation extra); "
            "skipping tear sheet. Install with `uv sync --extra validation`."
        )
        return None

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        qs.reports.html(
            series,
            output=str(out),
            title=title or "Strategy Tearsheet",
        )
    except Exception as exc:  # never let a report crash the validation pipeline
        logger.warning("write_tearsheet: quantstats failed to render: %s", exc)
        return None

    if not out.exists():
        logger.warning("write_tearsheet: quantstats reported success but no file at %s", out)
        return None

    return out


def _as_float(value: object) -> float | None:
    """Coerce a quantstats stat (scalar, 1-element Series, or array) to float.

    quantstats sometimes returns a length-1 ``Series`` when the input series is
    unnamed; this normalizes everything to a plain ``float`` and drops anything
    that is non-finite or non-scalar.
    """
    try:
        if isinstance(value, pd.Series):
            if len(value) != 1:
                return None
            value = value.iloc[0]
        scalar = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not np.isfinite(scalar):
        return None
    return scalar


def summary_stats(daily_returns: pd.Series) -> dict[str, float]:
    """Headline performance statistics as a flat ``{name: float}`` dict.

    A thin wrapper over ``quantstats.stats`` for the fields in
    ``_SUMMARY_FIELDS``. Degrades gracefully:

    - ``< 2`` clean bars ⇒ ``{}``.
    - quantstats missing ⇒ ``{}`` (with a logged warning).
    - any individual field that quantstats cannot compute (non-finite /
      non-scalar) is simply omitted rather than poisoning the whole dict.
    """
    series = _coerce_returns(daily_returns)
    if series is None:
        return {}

    try:
        import quantstats as qs
    except ImportError:
        logger.warning(
            "summary_stats: quantstats not installed (validation extra); "
            "returning empty stats."
        )
        return {}

    stats: dict[str, float] = {}
    for name, attr in _SUMMARY_FIELDS:
        func = getattr(qs.stats, attr, None)
        if func is None:
            continue
        try:
            raw = func(series)
        except Exception:  # a single bad stat must not sink the rest of the dict
            continue
        coerced = _as_float(raw)
        if coerced is not None:
            stats[name] = coerced
    return stats
