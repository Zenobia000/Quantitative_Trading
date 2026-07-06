"""PBO — Probability of Backtest Overfitting via CSCV.

Reference: Bailey, Borwein, López de Prado, Zhu (2017), *The probability of
backtest overfitting*, Journal of Computational Finance 20(4), 39-69.

Self-contained tests for ``validation/pbo.py``. Three behavioural anchors from
the paper's interpretation of PBO (Eq. 5 / §3):

(a) fully random config returns      → PBO ≈ 0.5 (no edge, pure noise)
(b) one config truly best IS *and* OOS → PBO low  (a real, persistent edge)
(c) one config overfit on IS only, OOS random → PBO high (overfitting detected)

Plus boundary / contract tests (shape validation, determinism, range).
"""
from __future__ import annotations

import numpy as np
import pytest

from quant_platform.services.research_validation.validation.pbo import (
    probability_of_backtest_overfitting,
    sharpe_metric,
)


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


# --------------------------------------------------------------------------- #
# (a) Pure noise → PBO ≈ 0.5                                                   #
# --------------------------------------------------------------------------- #
def test_random_matrix_pbo_near_half() -> None:
    """No config has any edge: the IS-best is a coin-flip OOS → PBO ≈ 0.5.

    Paper §4 (Monte-Carlo): under H0 of no skill the logits λ are symmetric
    about 0, so the fraction with λ<0 converges to 1/2.
    """
    rng = _rng(7)
    T, N = 1600, 20
    returns = rng.standard_normal((T, N))
    pbo = probability_of_backtest_overfitting(returns, n_splits=8)
    assert 0.0 <= pbo <= 1.0
    assert pbo == pytest.approx(0.5, abs=0.18)


# --------------------------------------------------------------------------- #
# (b) Real, persistent edge → PBO low                                         #
# --------------------------------------------------------------------------- #
def test_true_edge_pbo_low() -> None:
    """One config has a genuine drift present in *every* row (IS and OOS).

    Its Sharpe dominates in any split → IS-best is also OOS-best → λ>0 almost
    always → PBO ≈ 0.
    """
    rng = _rng(11)
    T, N = 1600, 20
    returns = rng.standard_normal((T, N)) * 0.01
    # config 0 carries a persistent positive drift on top of the same noise
    returns[:, 0] += 0.01
    pbo = probability_of_backtest_overfitting(returns, n_splits=8)
    assert pbo < 0.20


# --------------------------------------------------------------------------- #
# (c) Overfit on IS only, OOS noise → PBO high                                #
# --------------------------------------------------------------------------- #
def test_overfit_only_in_sample_pbo_high() -> None:
    """Construct configs that win IS but are random OOS.

    Build T rows; for each *contiguous* IS-block of rows, a different config is
    artificially inflated, but OOS performance is pure noise. The IS-best
    almost never repeats OOS → λ<0 dominates → PBO ≈ 1.

    Concretely: many configs, each is noise everywhere except it gets a big
    positive spike in exactly one sub-block. CSCV picks whichever config owns
    the IS blocks; that config is plain noise on the held-out OOS blocks.
    """
    rng = _rng(23)
    S = 8
    block = 200
    T = S * block
    N = 40
    returns = rng.standard_normal((T, N)) * 0.01
    # Each config gets a strong, isolated spike in a single distinct block so
    # that whichever blocks land in-sample, *some* config looks best there,
    # yet that same config is just noise on the out-of-sample blocks.
    for cfg in range(N):
        b = cfg % S
        sl = slice(b * block, (b + 1) * block)
        returns[sl, cfg] += rng.standard_normal(block) * 0.05 + 0.05
    pbo = probability_of_backtest_overfitting(returns, n_splits=S)
    assert pbo > 0.55


# --------------------------------------------------------------------------- #
# Deterministic / hand-checkable anchor                                       #
# --------------------------------------------------------------------------- #
def test_dominant_config_pbo_zero() -> None:
    """A config strictly best in every single row → best on every IS *and*
    OOS slice → never below OOS median → PBO is exactly 0."""
    T, N, S = 800, 10, 8
    base = _rng(3).standard_normal((T, N)) * 0.001
    base[:, 4] += 1.0  # config 4 dwarfs everyone, everywhere
    pbo = probability_of_backtest_overfitting(base, n_splits=S)
    assert pbo == 0.0


def test_sharpe_metric_matches_manual() -> None:
    """sharpe_metric reduces to mean/std (annualisation cancels in ranking,
    but we still verify the per-column value matches the textbook formula)."""
    x = np.array([[0.01, -0.02], [0.02, 0.04], [0.03, 0.00], [0.00, 0.06]])
    got = sharpe_metric(x)
    # column 0
    c0 = x[:, 0]
    exp0 = c0.mean() / c0.std(ddof=1) * np.sqrt(252)
    assert got.shape == (2,)
    assert got[0] == pytest.approx(exp0)


# --------------------------------------------------------------------------- #
# Boundary / contract                                                         #
# --------------------------------------------------------------------------- #
def test_deterministic_same_input_same_output() -> None:
    rng = _rng(99)
    returns = rng.standard_normal((400, 12))
    a = probability_of_backtest_overfitting(returns, n_splits=8)
    b = probability_of_backtest_overfitting(returns, n_splits=8)
    assert a == b


def test_returns_in_unit_interval() -> None:
    rng = _rng(5)
    returns = rng.standard_normal((480, 15))
    pbo = probability_of_backtest_overfitting(returns, n_splits=6)
    assert 0.0 <= pbo <= 1.0


def test_odd_n_splits_rejected() -> None:
    returns = _rng(1).standard_normal((100, 5))
    with pytest.raises(ValueError, match="even"):
        probability_of_backtest_overfitting(returns, n_splits=7)


def test_too_few_configs_rejected() -> None:
    returns = _rng(1).standard_normal((100, 1))
    with pytest.raises(ValueError, match="config"):
        probability_of_backtest_overfitting(returns, n_splits=8)


def test_non_2d_rejected() -> None:
    returns = _rng(1).standard_normal(100)
    with pytest.raises(ValueError, match="2-D"):
        probability_of_backtest_overfitting(returns, n_splits=8)


def test_n_splits_exceeds_rows_rejected() -> None:
    returns = _rng(1).standard_normal((6, 5))
    with pytest.raises(ValueError, match="rows"):
        probability_of_backtest_overfitting(returns, n_splits=8)


def test_custom_metric_callable() -> None:
    """metric may be any callable [T x N] -> [N]; mean-return ranking here."""
    rng = _rng(42)
    returns = rng.standard_normal((800, 16)) * 0.01
    returns[:, 0] += 0.02  # persistent winner under mean metric too
    pbo = probability_of_backtest_overfitting(
        returns, n_splits=8, metric=lambda m: m.mean(axis=0)
    )
    assert pbo < 0.25
