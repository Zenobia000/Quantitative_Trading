"""wfa — Walk-Forward Analysis splitter with purge + embargo (pure date logic).

Self-contained module: depends only on the stdlib ``datetime``. No IO, no other
project modules, fully deterministic. It produces the IS/OOS calendar windows
that drive Pipeline stage 8 (``dev_docs/18_reference_architecture_and_metrics.md``
§5, row 8 — *Walk-Forward Analysis*).

Background
----------
Walk-forward analysis evaluates a strategy on a sequence of out-of-sample (OOS)
segments, each preceded by an in-sample (IS) fit segment that slides forward in
time. To prevent information leakage from IS into OOS when labels span multiple
bars, López de Prado introduces two devices:

* **Purging** — drop training observations whose label horizon overlaps the test
  set. Here it is realised as a fixed ``purge_days`` calendar gap *between* the
  IS window's end and the OOS window's start.
* **Embargo** — additionally drop training observations that *immediately follow*
  the test set (serial correlation leaks backward across the IS/OOS seam). Here
  it is an ``embargo_days`` band reserved *after* each OOS window that the next
  fold's IS window may not enter.

Reference
---------
López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley.
    Ch. 7 §7.4.1 (purging), §7.4.2 (embargo); Ch. 11 (walk-forward / CPCV).
Bailey, Borwein, López de Prado & Zhu (2017). *The probability of backtest
    overfitting*. J. Computational Finance — motivation for leakage-free splits.

Window model (formulae)
-----------------------
All windows are half-open ``[start, end)`` measured in **calendar days**.
For fold ``i`` (0-indexed) let ``o = i * step_days`` be the fold offset.

ROLLING (``anchored=False``)::

    is_start_i  = start + o
    is_end_i    = is_start_i + is_days
    oos_start_i = is_end_i + purge_days          # purge gap
    oos_end_i   = oos_start_i + oos_days

ANCHORED (``anchored=True``) — IS start pinned, IS window expands::

    is_start_i  = start                          # pinned
    oos_start_i = start + is_days + o + purge_days
    oos_end_i   = oos_start_i + oos_days
    is_end_i    = oos_start_i - purge_days        # IS grows to meet the purge gap

Acceptance / embargo rules
--------------------------
A fold ``i`` is emitted iff::

    is_start_i >= start  and  oos_end_i <= end                     (in-bounds)
    oos_start_i >= prev_oos_end + embargo_days  (i > 0)            (embargo)

The embargo guards the seam between one fold's OOS region and the *next* fold's
OOS region, so it is applied to ``oos_start`` — this is correct for both rolling
(where IS slides) and anchored (where IS start is pinned and cannot itself carry
the constraint). Iteration stops at the first ``oos_end_i > end``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

__all__ = ["WFAFold", "walk_forward_splits"]


@dataclass(frozen=True)
class WFAFold:
    """One walk-forward fold. All bounds half-open ``[start, end)``.

    Invariant (purge_days >= 0, embargo >= 0):
        ``is_start < is_end <= oos_start < oos_end``.
    """

    is_start: date
    is_end: date
    oos_start: date
    oos_end: date


def walk_forward_splits(
    start: date,
    end: date,
    is_days: int,
    oos_days: int,
    step_days: int | None = None,
    purge_days: int = 0,
    embargo_days: int = 0,
    *,
    anchored: bool = False,
) -> list[WFAFold]:
    """Generate walk-forward IS/OOS folds with purge + embargo (pure dates).

    Parameters
    ----------
    start, end : date
        Global span ``[start, end)`` available for all folds. ``end`` exclusive.
    is_days : int
        In-sample window length in calendar days. For ``anchored=True`` this is
        the *initial / minimum* IS length (the window then expands).
    oos_days : int
        Out-of-sample window length in calendar days.
    step_days : int | None
        Forward advance per fold. ``None`` → defaults to ``oos_days`` (adjacent,
        non-overlapping OOS segments — the canonical rolling cadence).
    purge_days : int
        Calendar-day gap inserted between IS end and OOS start (AFML §7.4.1).
    embargo_days : int
        Calendar-day band reserved after each OOS window; the next fold's IS may
        not start before ``oos_end + embargo_days`` (AFML §7.4.2).
    anchored : bool
        ``False`` (default) → rolling IS window. ``True`` → IS start pinned to
        ``start`` and the IS window expands each fold.

    Returns
    -------
    list[WFAFold]
        Chronological folds fully inside ``[start, end)``. Empty if the span
        cannot fit even one fold.

    Raises
    ------
    ValueError
        On ``end <= start``, non-positive ``is_days``/``oos_days``/``step_days``,
        or negative ``purge_days``/``embargo_days``.
    """
    # --- input validation (system boundary; fail fast) --------------------- #
    if end <= start:
        raise ValueError(f"end ({end}) must be after start ({start})")
    if is_days <= 0:
        raise ValueError(f"is_days must be positive, got {is_days}")
    if oos_days <= 0:
        raise ValueError(f"oos_days must be positive, got {oos_days}")
    if purge_days < 0:
        raise ValueError(f"purge_days must be >= 0, got {purge_days}")
    if embargo_days < 0:
        raise ValueError(f"embargo_days must be >= 0, got {embargo_days}")

    step = oos_days if step_days is None else step_days
    if step <= 0:
        raise ValueError(f"step_days must be positive, got {step_days}")

    folds: list[WFAFold] = []
    prev_oos_end: date | None = None
    i = 0
    while True:
        offset = i * step
        fold = _build_fold(
            start=start,
            offset=offset,
            is_days=is_days,
            oos_days=oos_days,
            purge_days=purge_days,
            anchored=anchored,
        )
        # Stop once the OOS tail runs past the global end — later folds only
        # push further out, so no point continuing.
        if fold.oos_end > end:
            break

        # Embargo: this fold's OOS must clear the previous OOS + embargo band.
        # Applied to oos_start so it holds for anchored mode too (is_start is
        # pinned there and cannot carry the constraint).
        if prev_oos_end is not None and fold.oos_start < prev_oos_end + timedelta(
            days=embargo_days
        ):
            i += 1
            continue

        folds.append(fold)
        prev_oos_end = fold.oos_end
        i += 1

    return folds


def _build_fold(
    *,
    start: date,
    offset: int,
    is_days: int,
    oos_days: int,
    purge_days: int,
    anchored: bool,
) -> WFAFold:
    """Construct a single fold's four boundaries from its forward ``offset``.

    Implements the ROLLING / ANCHORED formulae documented in the module
    docstring. Pure: no side effects, no bounds checking (caller filters).
    """
    if anchored:
        is_start = start
        oos_start = start + timedelta(days=is_days + offset + purge_days)
        is_end = oos_start - timedelta(days=purge_days)
    else:
        is_start = start + timedelta(days=offset)
        is_end = is_start + timedelta(days=is_days)
        oos_start = is_end + timedelta(days=purge_days)

    oos_end = oos_start + timedelta(days=oos_days)
    return WFAFold(
        is_start=is_start,
        is_end=is_end,
        oos_start=oos_start,
        oos_end=oos_end,
    )
