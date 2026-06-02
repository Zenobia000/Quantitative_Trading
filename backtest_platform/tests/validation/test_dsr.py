"""Tests for validation/dsr.py — Deflated / Probabilistic Sharpe Ratio.

Reference: Bailey & López de Prado (2012/2014). Cross-checks the formula
structure against dev_docs/18 §4.3 (PSR) + §4.4 (DSR, D 類). Numeric ground
truth recomputed from scipy.stats.norm closed forms, not magic constants.
"""
from __future__ import annotations

import math

import numpy as np
import pytest
from scipy.stats import norm

from backtest_platform.validation.dsr import (
    EULER_MASCHERONI,
    deflated_sharpe_ratio,
    expected_max_sharpe,
    psr,
)

# --------------------------------------------------------------------------- #
# PSR — Probabilistic Sharpe Ratio (Bailey & López de Prado 2012)
# --------------------------------------------------------------------------- #


def test_psr_returns_half_when_sr_equals_benchmark():
    """SR == SR* ⇒ numerator 0 ⇒ Φ(0) = 0.5 exactly."""
    assert psr(0.1, n_obs=1000, skew=0.0, kurtosis=3.0, sr_benchmark=0.1) == pytest.approx(0.5)


def test_psr_known_normal_case():
    """Hand-computed ground truth for Gaussian returns (skew=0, kurtosis=3).

    sr=0.1, n_obs=1000, benchmark=0:
      denom = sqrt(1 - 0 + (3-1)/4 * 0.1^2) = sqrt(1 + 0.005)
      z     = 0.1 * sqrt(999) / denom
      PSR   = Φ(z)
    """
    sr, n, bench = 0.1, 1000, 0.0
    denom = math.sqrt(1 + (3 - 1) / 4 * sr**2)
    expected = norm.cdf((sr - bench) * math.sqrt(n - 1) / denom)
    assert psr(sr, n_obs=n, skew=0.0, kurtosis=3.0) == pytest.approx(expected, abs=1e-12)
    assert expected == pytest.approx(0.99919150, abs=1e-6)


def test_psr_monotonic_increasing_in_sr():
    """Higher realized Sharpe ⇒ higher confidence it beats the benchmark."""
    vals = [psr(sr, n_obs=500, skew=0.0, kurtosis=3.0) for sr in (-0.2, 0.0, 0.05, 0.1, 0.3)]
    assert all(b > a for a, b in zip(vals, vals[1:]))


def test_psr_monotonic_increasing_in_n_obs():
    """More observations ⇒ tighter estimate ⇒ higher PSR for a positive SR."""
    vals = [psr(0.1, n_obs=n, skew=0.0, kurtosis=3.0) for n in (30, 100, 500, 2000)]
    assert all(b > a for a, b in zip(vals, vals[1:]))


def test_psr_negative_skew_lowers_confidence():
    """Negative skew inflates the variance denominator ⇒ lower PSR (riskier)."""
    base = psr(0.2, n_obs=500, skew=0.0, kurtosis=3.0)
    neg = psr(0.2, n_obs=500, skew=-1.0, kurtosis=3.0)
    assert neg < base


def test_psr_excess_kurtosis_lowers_confidence():
    """Fat tails (kurtosis > 3) inflate the denominator ⇒ lower PSR."""
    base = psr(0.2, n_obs=500, skew=0.0, kurtosis=3.0)
    fat = psr(0.2, n_obs=500, skew=0.0, kurtosis=9.0)
    assert fat < base


def test_psr_in_unit_interval():
    for sr in (-1.0, -0.1, 0.0, 0.1, 0.5, 2.0):
        p = psr(sr, n_obs=250, skew=-0.3, kurtosis=5.0)
        assert 0.0 <= p <= 1.0


# --------------------------------------------------------------------------- #
# expected_max_sharpe — Bailey deflation threshold SR*
# --------------------------------------------------------------------------- #


def test_expected_max_sharpe_known_value():
    """Bailey expected-maximum approximation, N=10, var=0.25.

    SR* = sqrt(var) * ((1-γ)·z1 + γ·z2),
          z1 = Φ⁻¹(1 - 1/N), z2 = Φ⁻¹(1 - 1/(N·e)), γ = Euler-Mascheroni.
    """
    N, var = 10, 0.25
    g = EULER_MASCHERONI
    z1 = norm.ppf(1 - 1 / N)
    z2 = norm.ppf(1 - 1 / (N * math.e))
    expected = math.sqrt(var) * ((1 - g) * z1 + g * z2)
    assert expected_max_sharpe(N, var) == pytest.approx(expected, abs=1e-12)
    assert expected == pytest.approx(0.787299, abs=1e-5)


def test_expected_max_sharpe_monotonic_in_trials():
    """More trials ⇒ a higher max-Sharpe is expected by chance ⇒ SR* rises."""
    vals = [expected_max_sharpe(n, 0.25) for n in (2, 5, 10, 50, 500)]
    assert all(b > a for a, b in zip(vals, vals[1:]))


def test_expected_max_sharpe_scales_with_sqrt_variance():
    """SR* is linear in sqrt(variance_of_sharpes)."""
    a = expected_max_sharpe(20, 0.25)
    b = expected_max_sharpe(20, 1.0)
    assert b == pytest.approx(2 * a, rel=1e-12)  # sqrt(1.0)/sqrt(0.25) = 2


def test_expected_max_sharpe_single_trial_no_deflation():
    """N=1 ⇒ no multiple-testing correction ⇒ SR* = 0 (avoids ppf(0)=-inf)."""
    assert expected_max_sharpe(1, 0.25) == 0.0


def test_expected_max_sharpe_zero_variance():
    """No dispersion across trials ⇒ nothing to deflate."""
    assert expected_max_sharpe(100, 0.0) == 0.0


# --------------------------------------------------------------------------- #
# deflated_sharpe_ratio — DSR = PSR(SR*)
# --------------------------------------------------------------------------- #


def test_dsr_equals_psr_at_deflated_benchmark():
    """DSR is exactly PSR evaluated with sr_benchmark = SR*."""
    sr, n_trials, n_obs, skew, kurt, var = 1.2, 25, 1250, -0.4, 6.0, 0.3
    srstar = expected_max_sharpe(n_trials, var)
    expected = psr(sr, n_obs=n_obs, skew=skew, kurtosis=kurt, sr_benchmark=srstar)
    got = deflated_sharpe_ratio(
        sr, n_trials=n_trials, n_obs=n_obs, skew=skew, kurtosis=kurt, sharpe_variance=var
    )
    assert got == pytest.approx(expected, abs=1e-12)


def test_dsr_in_unit_interval():
    for n_trials in (1, 2, 10, 100, 1000):
        d = deflated_sharpe_ratio(
            0.9, n_trials=n_trials, n_obs=252, skew=-0.3, kurtosis=5.0, sharpe_variance=0.25
        )
        assert 0.0 <= d <= 1.0


def test_dsr_decreasing_in_n_trials():
    """More backtested configurations ⇒ stronger deflation ⇒ lower DSR."""
    vals = [
        deflated_sharpe_ratio(
            0.8, n_trials=n, n_obs=100, skew=0.0, kurtosis=3.0, sharpe_variance=0.25
        )
        for n in (2, 5, 10, 50, 200)
    ]
    assert all(b < a for a, b in zip(vals, vals[1:]))
    assert all(0.0 <= v <= 1.0 for v in vals)


def test_dsr_single_trial_reduces_to_psr_against_zero():
    """With one trial there is no deflation: DSR == PSR(benchmark=0)."""
    d = deflated_sharpe_ratio(
        0.5, n_trials=1, n_obs=500, skew=0.0, kurtosis=3.0, sharpe_variance=0.25
    )
    p = psr(0.5, n_obs=500, skew=0.0, kurtosis=3.0, sr_benchmark=0.0)
    assert d == pytest.approx(p, abs=1e-12)


def test_dsr_high_sharpe_low_trials_passes_adr016_gate():
    """A strong, lightly-searched strategy clears the ADR-016 M3 DSR>0.95 bar."""
    d = deflated_sharpe_ratio(
        2.0, n_trials=5, n_obs=1250, skew=0.0, kurtosis=3.0, sharpe_variance=0.25
    )
    assert d > 0.95


def test_dsr_overfit_fails_adr016_gate():
    """A marginal Sharpe found after thousands of trials fails DSR>0.95."""
    d = deflated_sharpe_ratio(
        0.9, n_trials=5000, n_obs=252, skew=-0.5, kurtosis=8.0, sharpe_variance=0.5
    )
    assert d < 0.95


def test_euler_mascheroni_constant():
    assert EULER_MASCHERONI == pytest.approx(0.5772156649, abs=1e-10)


def test_psr_rejects_nonpositive_n_obs():
    with pytest.raises(ValueError):
        psr(0.1, n_obs=1, skew=0.0, kurtosis=3.0)
    with pytest.raises(ValueError):
        psr(0.1, n_obs=0, skew=0.0, kurtosis=3.0)


def test_expected_max_sharpe_rejects_negative_variance():
    with pytest.raises(ValueError):
        expected_max_sharpe(10, -0.1)


def test_expected_max_sharpe_rejects_nonpositive_trials():
    with pytest.raises(ValueError):
        expected_max_sharpe(0, 0.25)
