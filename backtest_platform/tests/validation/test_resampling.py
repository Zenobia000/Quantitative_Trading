"""Tests for validation/resampling.py — Bootstrap CI + Monte Carlo permutation.

Self-contained, pure-function module (no new-module imports). Covers the four
TDD contracts from the spec:
  1. seed fixed → reproducible
  2. strong-signal series → low permutation p-value
  3. pure noise → p-value not significant (≈ uniform, not tiny)
  4. bootstrap CI brackets the point estimate

Plus boundary / degenerate cases and a hand-computable sanity check.
"""
from __future__ import annotations

import numpy as np
import pytest

from backtest_platform.validation.resampling import (
    bootstrap_ci,
    monte_carlo_permutation_pvalue,
)

# --------------------------------------------------------------------------- #
# bootstrap_ci
# --------------------------------------------------------------------------- #


def test_bootstrap_ci_reproducible_with_seed() -> None:
    """Same seed → byte-identical (lo, hi, point)."""
    r = np.array([0.01, -0.02, 0.03, 0.005, -0.01, 0.04, 0.02, -0.03])
    a = bootstrap_ci(r, np.mean, n_iter=500, ci=0.95, seed=42)
    b = bootstrap_ci(r, np.mean, n_iter=500, ci=0.95, seed=42)
    assert a == b


def test_bootstrap_ci_different_seed_differs() -> None:
    """Different seed → different resample draws (CI bounds shift)."""
    r = np.array([0.01, -0.02, 0.03, 0.005, -0.01, 0.04, 0.02, -0.03])
    a = bootstrap_ci(r, np.mean, n_iter=500, seed=1)
    b = bootstrap_ci(r, np.mean, n_iter=500, seed=2)
    assert (a[0], a[1]) != (b[0], b[1])


def test_bootstrap_ci_point_is_stat_on_observed() -> None:
    """point estimate == stat_fn applied to the original (unresampled) sample."""
    r = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    lo, hi, point = bootstrap_ci(r, np.mean, n_iter=300, seed=7)
    assert point == pytest.approx(3.0)


def test_bootstrap_ci_brackets_point_estimate() -> None:
    """CI must contain the point estimate (lo <= point <= hi)."""
    rng = np.random.default_rng(0)
    r = rng.normal(0.001, 0.02, size=250)
    lo, hi, point = bootstrap_ci(r, np.mean, n_iter=1000, ci=0.95, seed=11)
    assert lo <= point <= hi
    assert lo < hi


def test_bootstrap_ci_wider_ci_is_not_narrower() -> None:
    """99% CI must be at least as wide as the 90% CI on the same data/seed."""
    rng = np.random.default_rng(3)
    r = rng.normal(0.0, 0.01, size=400)
    lo90, hi90, _ = bootstrap_ci(r, np.mean, n_iter=1000, ci=0.90, seed=5)
    lo99, hi99, _ = bootstrap_ci(r, np.mean, n_iter=1000, ci=0.99, seed=5)
    assert (hi99 - lo99) >= (hi90 - lo90)


def test_bootstrap_ci_recovers_known_mean() -> None:
    """For a tight normal sample, the 95% CI of the mean should contain the
    true population mean (known-truth check)."""
    rng = np.random.default_rng(123)
    true_mu = 0.05
    r = rng.normal(true_mu, 0.01, size=500)
    lo, hi, point = bootstrap_ci(r, np.mean, n_iter=2000, ci=0.95, seed=99)
    assert lo <= true_mu <= hi


def test_bootstrap_ci_supports_custom_stat_fn() -> None:
    """stat_fn is arbitrary — here the median; point must equal np.median."""
    r = np.array([10.0, 1.0, 2.0, 3.0, 100.0])
    lo, hi, point = bootstrap_ci(r, np.median, n_iter=500, seed=4)
    assert point == pytest.approx(3.0)
    assert lo <= point <= hi


def test_bootstrap_ci_single_element_is_degenerate() -> None:
    """One observation → every resample is that value → lo == hi == point."""
    r = np.array([0.07])
    lo, hi, point = bootstrap_ci(r, np.mean, n_iter=100, seed=1)
    assert lo == pytest.approx(0.07)
    assert hi == pytest.approx(0.07)
    assert point == pytest.approx(0.07)


def test_bootstrap_ci_rejects_empty_input() -> None:
    with pytest.raises(ValueError):
        bootstrap_ci(np.array([]), np.mean, n_iter=10, seed=1)


def test_bootstrap_ci_rejects_bad_ci_level() -> None:
    r = np.array([1.0, 2.0, 3.0])
    with pytest.raises(ValueError):
        bootstrap_ci(r, np.mean, n_iter=10, ci=1.5, seed=1)
    with pytest.raises(ValueError):
        bootstrap_ci(r, np.mean, n_iter=10, ci=0.0, seed=1)


def test_bootstrap_ci_rejects_nonpositive_iter() -> None:
    r = np.array([1.0, 2.0, 3.0])
    with pytest.raises(ValueError):
        bootstrap_ci(r, np.mean, n_iter=0, seed=1)


# --------------------------------------------------------------------------- #
# monte_carlo_permutation_pvalue
# --------------------------------------------------------------------------- #


def test_permutation_pvalue_reproducible_with_seed() -> None:
    rng = np.random.default_rng(0)
    r = rng.normal(0.001, 0.01, size=120)
    p1 = monte_carlo_permutation_pvalue(r, n_iter=1000, seed=2024)
    p2 = monte_carlo_permutation_pvalue(r, n_iter=1000, seed=2024)
    assert p1 == p2


def test_permutation_pvalue_in_unit_interval() -> None:
    rng = np.random.default_rng(1)
    r = rng.normal(0.0, 0.01, size=80)
    p = monte_carlo_permutation_pvalue(r, n_iter=500, seed=1)
    assert 0.0 <= p <= 1.0


def test_permutation_pvalue_strong_signal_is_significant() -> None:
    """A clearly positive-edge sequence (almost all wins, big mean) must yield
    a small p-value: the observed cumulative return beats random sign-flips."""
    rng = np.random.default_rng(7)
    # strong positive drift relative to noise
    r = rng.normal(0.02, 0.005, size=200)
    p = monte_carlo_permutation_pvalue(r, n_iter=2000, seed=7)
    assert p < 0.05


def test_permutation_pvalue_pure_noise_not_significant() -> None:
    """Zero-mean noise should NOT look like a real edge — p comfortably above
    the 5% rejection threshold (averaged over several seeds to avoid a fluke)."""
    ps = []
    for s in range(10):
        rng = np.random.default_rng(1000 + s)
        r = rng.normal(0.0, 0.01, size=150)
        ps.append(monte_carlo_permutation_pvalue(r, n_iter=1000, seed=s))
    # most noise draws are non-significant; mean p should sit well above 0.05
    assert np.mean(ps) > 0.20


def test_permutation_pvalue_strong_negative_signal_is_not_significant() -> None:
    """A strongly *negative* edge is not 'better than random' on the
    one-sided (>=) test → large p-value."""
    rng = np.random.default_rng(5)
    r = rng.normal(-0.02, 0.005, size=200)
    p = monte_carlo_permutation_pvalue(r, n_iter=2000, seed=5)
    assert p > 0.5


def test_permutation_pvalue_has_plus_one_floor() -> None:
    """The (b+1)/(n+1) estimator can never return exactly 0 (Davison &
    Hinkley convention) — guards against overstated significance."""
    r = np.full(50, 0.01)  # every trade identical positive return
    p = monte_carlo_permutation_pvalue(r, n_iter=100, seed=3)
    assert p > 0.0
    assert p == pytest.approx(1.0 / 101.0)


def test_permutation_pvalue_rejects_empty_input() -> None:
    with pytest.raises(ValueError):
        monte_carlo_permutation_pvalue(np.array([]), n_iter=10, seed=1)


def test_permutation_pvalue_rejects_nonpositive_iter() -> None:
    with pytest.raises(ValueError):
        monte_carlo_permutation_pvalue(np.array([0.01, -0.02]), n_iter=0, seed=1)


def test_nan_input_rejected_not_silently_significant():
    """HIGH fix: NaN in returns must raise, not silently produce a p-value/CI."""
    import numpy as np
    import pytest

    from backtest_platform.validation.resampling import (
        bootstrap_ci,
        monte_carlo_permutation_pvalue,
    )

    with pytest.raises(ValueError, match="finite"):
        monte_carlo_permutation_pvalue(np.array([0.1, np.nan, -0.05]), n_iter=100, seed=1)
    with pytest.raises(ValueError, match="finite"):
        bootstrap_ci(np.array([0.1, np.inf, -0.05]), np.mean, n_iter=100, seed=1)
