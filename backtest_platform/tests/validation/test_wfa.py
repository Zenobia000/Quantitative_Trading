"""TDD spec for validation/wfa.py — Walk-Forward splitter (purge + embargo).

Pure date arithmetic. We assert against hand-computed fold boundaries plus
leakage / boundary invariants (López de Prado, *Advances in Financial Machine
Learning* (2018), Ch. 7 — purging & embargo; Ch. 11 — walk-forward / CPCV).

All windows are half-open ``[start, end)`` in *calendar days*. Conventions
mirrored by the implementation:

* IS length = ``is_days``, OOS length = ``oos_days``.
* ``purge_days`` calendar days are dropped *between* IS end and OOS start.
* ``embargo_days`` calendar days are reserved *after* OOS end; the next fold's
  IS may not start inside that embargo band.
* rolling: each fold advances by ``step_days`` (default ``oos_days``).
* anchored: ``is_start`` is pinned to ``start`` and the IS window expands.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from backtest_platform.validation.wfa import WFAFold, walk_forward_splits


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _days(fold_attr_a: date, fold_attr_b: date) -> int:
    return (fold_attr_b - fold_attr_a).days


# --------------------------------------------------------------------------- #
# Hand-computed known case — rolling, no purge/embargo
# --------------------------------------------------------------------------- #
def test_rolling_hand_computed_two_folds() -> None:
    """1 Jan → 2 Mar, IS=30, OOS=15, step default(=OOS=15).

    Fold 0: IS [01-01, 01-31), OOS [01-31, 02-15)
    Fold 1: IS [01-16, 02-15), OOS [02-15, 03-02)
    A 3rd fold would need OOS end 03-17 > end (03-02) → excluded.
    """
    folds = walk_forward_splits(
        start=date(2021, 1, 1),
        end=date(2021, 3, 2),
        is_days=30,
        oos_days=15,
        step_days=None,  # default → oos_days
    )
    assert len(folds) == 2

    f0 = folds[0]
    assert f0.is_start == date(2021, 1, 1)
    assert f0.is_end == date(2021, 1, 31)
    assert f0.oos_start == date(2021, 1, 31)
    assert f0.oos_end == date(2021, 2, 15)

    f1 = folds[1]
    assert f1.is_start == date(2021, 1, 16)  # advanced by step=15
    assert f1.is_end == date(2021, 2, 15)
    assert f1.oos_start == date(2021, 2, 15)
    assert f1.oos_end == date(2021, 3, 2)


def test_rolling_window_lengths_constant() -> None:
    folds = walk_forward_splits(
        start=date(2020, 1, 1),
        end=date(2022, 1, 1),
        is_days=180,
        oos_days=60,
    )
    assert folds, "expected at least one fold"
    for f in folds:
        assert _days(f.is_start, f.is_end) == 180
        assert _days(f.oos_start, f.oos_end) == 60


# --------------------------------------------------------------------------- #
# Anchored
# --------------------------------------------------------------------------- #
def test_anchored_is_start_is_pinned_and_expands() -> None:
    folds = walk_forward_splits(
        start=date(2021, 1, 1),
        end=date(2021, 4, 1),
        is_days=30,      # minimum/initial IS length
        oos_days=15,
        anchored=True,
    )
    assert len(folds) >= 2
    # IS start pinned to global start for every fold.
    assert all(f.is_start == date(2021, 1, 1) for f in folds)
    # IS window strictly expands fold over fold.
    is_lengths = [_days(f.is_start, f.is_end) for f in folds]
    assert is_lengths == sorted(is_lengths)
    assert is_lengths[0] == 30
    assert is_lengths[-1] > is_lengths[0]


def test_anchored_first_fold_matches_rolling_first_fold() -> None:
    common = dict(
        start=date(2021, 1, 1),
        end=date(2021, 6, 1),
        is_days=40,
        oos_days=20,
    )
    rolling = walk_forward_splits(anchored=False, **common)
    anchored = walk_forward_splits(anchored=True, **common)
    assert rolling[0] == anchored[0]


# --------------------------------------------------------------------------- #
# Purge & embargo gaps
# --------------------------------------------------------------------------- #
def test_purge_gap_is_exact() -> None:
    folds = walk_forward_splits(
        start=date(2021, 1, 1),
        end=date(2021, 12, 31),
        is_days=60,
        oos_days=30,
        purge_days=5,
    )
    assert folds
    for f in folds:
        # purge band sits strictly between IS end and OOS start.
        assert _days(f.is_end, f.oos_start) == 5
        assert _days(f.is_start, f.is_end) == 60
        assert _days(f.oos_start, f.oos_end) == 30


def test_embargo_separates_consecutive_oos_windows() -> None:
    """Embargo reserves a band after each OOS; the next fold's OOS may not begin
    before ``prev.oos_end + embargo`` (AFML §7.4.2). With step == oos_days the
    OOS windows would otherwise be adjacent, so a positive embargo forces a gap
    by skipping folds whose OOS would fall inside the band."""
    embargo = 7
    base = dict(
        start=date(2021, 1, 1),
        end=date(2022, 6, 1),
        is_days=90,
        oos_days=30,
        step_days=30,
    )
    folds = walk_forward_splits(embargo_days=embargo, **base)
    assert len(folds) >= 2
    for prev, nxt in zip(folds, folds[1:]):
        assert nxt.oos_start >= prev.oos_end + timedelta(days=embargo)

    # Embargo must be *observable*: it drops folds vs the no-embargo run.
    no_embargo = walk_forward_splits(embargo_days=0, **base)
    assert len(folds) < len(no_embargo)


def test_purge_and_embargo_combined_no_negative_windows() -> None:
    folds = walk_forward_splits(
        start=date(2021, 1, 1),
        end=date(2023, 1, 1),
        is_days=120,
        oos_days=40,
        purge_days=10,
        embargo_days=10,
    )
    assert folds
    for f in folds:
        assert f.is_start < f.is_end <= f.oos_start < f.oos_end


# --------------------------------------------------------------------------- #
# No-leakage invariants
# --------------------------------------------------------------------------- #
def test_is_and_oos_never_overlap_within_a_fold() -> None:
    folds = walk_forward_splits(
        start=date(2019, 1, 1),
        end=date(2024, 1, 1),
        is_days=252,
        oos_days=63,
        purge_days=5,
        embargo_days=5,
    )
    assert folds
    for f in folds:
        assert f.is_end <= f.oos_start  # IS fully precedes OOS (purge >= 0)


def test_oos_windows_are_chronological_and_non_overlapping_when_step_ge_oos() -> None:
    folds = walk_forward_splits(
        start=date(2020, 1, 1),
        end=date(2023, 1, 1),
        is_days=180,
        oos_days=60,
        step_days=60,  # == oos_days → adjacent, non-overlapping OOS
    )
    assert len(folds) >= 2
    for prev, nxt in zip(folds, folds[1:]):
        assert nxt.oos_start >= prev.oos_end


def test_all_windows_within_global_bounds() -> None:
    start, end = date(2021, 1, 1), date(2022, 1, 1)
    folds = walk_forward_splits(
        start=start,
        end=end,
        is_days=90,
        oos_days=30,
        purge_days=3,
        embargo_days=3,
    )
    assert folds
    for f in folds:
        assert f.is_start >= start
        assert f.oos_end <= end


# --------------------------------------------------------------------------- #
# Boundary / insufficient-data cases
# --------------------------------------------------------------------------- #
def test_insufficient_data_returns_empty() -> None:
    # Need >= is_days + purge + oos days of span; give far less.
    folds = walk_forward_splits(
        start=date(2021, 1, 1),
        end=date(2021, 1, 20),  # 19 days span
        is_days=30,
        oos_days=15,
    )
    assert folds == []


def test_exactly_one_fold_when_span_fits_once() -> None:
    # span exactly is_days + oos_days, step large → only one fold.
    folds = walk_forward_splits(
        start=date(2021, 1, 1),
        end=date(2021, 1, 1) + timedelta(days=45),
        is_days=30,
        oos_days=15,
        step_days=999,
    )
    assert len(folds) == 1
    f = folds[0]
    assert f.is_start == date(2021, 1, 1)
    assert f.oos_end == date(2021, 1, 1) + timedelta(days=45)


def test_returns_list_of_frozen_dataclass() -> None:
    folds = walk_forward_splits(
        start=date(2021, 1, 1),
        end=date(2021, 12, 31),
        is_days=60,
        oos_days=30,
    )
    assert isinstance(folds, list)
    f = folds[0]
    assert isinstance(f, WFAFold)
    with pytest.raises((AttributeError, TypeError)):  # frozen → immutable
        f.is_start = date(2000, 1, 1)  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# Input validation
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "kwargs",
    [
        dict(is_days=0, oos_days=15),
        dict(is_days=30, oos_days=0),
        dict(is_days=-1, oos_days=15),
        dict(is_days=30, oos_days=15, step_days=0),
        dict(is_days=30, oos_days=15, purge_days=-1),
        dict(is_days=30, oos_days=15, embargo_days=-1),
    ],
)
def test_invalid_params_raise(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        walk_forward_splits(
            start=date(2021, 1, 1),
            end=date(2021, 12, 31),
            **kwargs,
        )


def test_end_before_start_raises() -> None:
    with pytest.raises(ValueError):
        walk_forward_splits(
            start=date(2021, 12, 31),
            end=date(2021, 1, 1),
            is_days=30,
            oos_days=15,
        )
