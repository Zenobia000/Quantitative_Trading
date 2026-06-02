"""Resampling-based statistical validation — Bootstrap CI + Monte Carlo permutation.

Self-contained, pure functions (no IO, no new-module imports; numpy only). Two
non-parametric tools for judging whether a backtest's edge is real or luck:

1. ``bootstrap_ci`` — a percentile bootstrap confidence interval for any
   statistic of a return series (mean, median, Sharpe, ...). Answers
   "how uncertain is this metric given the sample we have?".

2. ``monte_carlo_permutation_pvalue`` — a Monte Carlo permutation (randomisation)
   test on the *sign* of trade returns. Answers "is the observed cumulative
   return better than what a random win/lose sequence of the same magnitudes
   would produce?" — i.e. does the strategy beat chance?

Both use ``np.random.default_rng(seed)`` (PCG64) so every result is exactly
reproducible from its seed.

--------------------------------------------------------------------------------
Formulas & references (cross-ref dev_docs/18 §4)
--------------------------------------------------------------------------------

§4 — Statistical-robustness family (D). These are the resampling primitives that
PBO/DSR/CPCV build on; they sit upstream of `validation/pbo.py` and
`validation/dsr.py` in the same §7 "Statistical Validation" pipeline stage.

Percentile bootstrap CI
  Given a sample x = (x_1, ..., x_n) and statistic θ̂ = s(x):
    - For b = 1..B: draw x*_b by sampling n elements from x *with replacement*,
      compute θ̂*_b = s(x*_b).
    - The (1 - α) percentile CI is
          [ Q_{α/2}({θ̂*_b}),  Q_{1 - α/2}({θ̂*_b}) ]
      where Q_p is the p-quantile of the bootstrap distribution.
    - point estimate = s(x) on the *observed* sample.
  Ref: Efron & Tibshirani (1993), *An Introduction to the Bootstrap*, Ch. 13
       (percentile method). Davison & Hinkley (1997), *Bootstrap Methods and
       Their Application*, §5.

Monte Carlo permutation (sign-flip) p-value
  Statistic: T(x) = sum(x)  (total / cumulative simple return; the sign of the
  cumulative log-return is identical, and for a fixed magnitude set the ranking
  is monotone in mean — so mean-edge ⇔ large T).
  Null: each trade's outcome is an independent fair coin on its sign, i.e. the
  observed magnitudes |x_i| are fixed but their signs are exchangeable random
  ±1. Under H0 the expected cumulative return is 0; H1 (one-sided) is "the
  strategy has a positive edge".
    - For b = 1..B: draw s_b ∈ {-1,+1}^n uniformly, T*_b = sum(s_b ⊙ |x|).
    - p = (1 + #{ b : T*_b >= T(x) }) / (1 + B)
  The "+1" (Davison & Hinkley convention; North, Curtis & Sham 2002) counts the
  observed arrangement itself and keeps p strictly > 0, never overstating
  significance.
  Ref: Davison & Hinkley (1997) §4; North, Curtis & Sham (2002),
       *A note on the calculation of empirical P values from Monte Carlo
       procedures*, Am. J. Hum. Genet. 71(2). Aronson (2006),
       *Evidence-Based Technical Analysis*, Ch. 6 (permutation test of trading
       system significance) — the trading-specific framing used here.
--------------------------------------------------------------------------------
"""
from __future__ import annotations

from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray


def bootstrap_ci(
    returns: NDArray[np.float64] | np.ndarray,
    stat_fn: Callable[[np.ndarray], float],
    n_iter: int = 1000,
    ci: float = 0.95,
    seed: int | None = None,
) -> tuple[float, float, float]:
    """Percentile-bootstrap confidence interval for ``stat_fn(returns)``.

    Resamples ``returns`` *with replacement* ``n_iter`` times, recomputes the
    statistic on each resample, and takes the empirical ``[α/2, 1-α/2]``
    percentiles of that bootstrap distribution as the CI. ``α = 1 - ci``.

    Implements the percentile bootstrap — Efron & Tibshirani (1993) Ch. 13;
    Davison & Hinkley (1997) §5. (dev_docs/18 §4 family D resampling primitive.)

    Parameters
    ----------
    returns
        1-D array of observations (e.g. per-period or per-trade returns).
    stat_fn
        Statistic to estimate; must accept a 1-D ``np.ndarray`` and return a
        scalar (``np.mean``, ``np.median``, a Sharpe function, ...).
    n_iter
        Number of bootstrap resamples ``B`` (must be > 0).
    ci
        Confidence level in (0, 1), e.g. 0.95 for a 95% interval.
    seed
        Seed for ``np.random.default_rng``; fixing it makes the result exactly
        reproducible.

    Returns
    -------
    (lo, hi, point)
        ``lo``/``hi`` are the lower/upper CI bounds; ``point`` is
        ``stat_fn(returns)`` on the *observed* (unresampled) sample. The CI
        always brackets ``point`` only up to sampling noise, but ``point`` is
        reported separately so callers see the observed estimate exactly.

    Raises
    ------
    ValueError
        If ``returns`` is empty, ``ci`` is not in (0, 1), or ``n_iter <= 0``.
    """
    x = np.asarray(returns, dtype=np.float64).ravel()
    if x.size == 0:
        raise ValueError("returns must be non-empty")
    if not np.all(np.isfinite(x)):
        raise ValueError("returns must be finite (no NaN/inf)")
    if not (0.0 < ci < 1.0):
        raise ValueError(f"ci must be in (0, 1), got {ci}")
    if n_iter <= 0:
        raise ValueError(f"n_iter must be positive, got {n_iter}")

    rng = np.random.default_rng(seed)
    n = x.size
    # Vectorised: (n_iter, n) matrix of indices sampled with replacement.
    idx = rng.integers(0, n, size=(n_iter, n))
    samples = x[idx]
    stats = np.array([float(stat_fn(row)) for row in samples], dtype=np.float64)

    alpha = 1.0 - ci
    lo = float(np.percentile(stats, 100.0 * (alpha / 2.0)))
    hi = float(np.percentile(stats, 100.0 * (1.0 - alpha / 2.0)))
    point = float(stat_fn(x))
    return lo, hi, point


def monte_carlo_permutation_pvalue(
    trade_returns: NDArray[np.float64] | np.ndarray,
    n_iter: int = 1000,
    seed: int | None = None,
) -> float:
    """One-sided Monte Carlo permutation (sign-flip) p-value for an edge.

    Tests H0 "trade signs are random fair coins (no edge)" against H1 "the
    strategy has a positive cumulative-return edge". The observed statistic is
    the total return ``T = sum(trade_returns)``; under H0 the magnitudes
    ``|trade_returns|`` are held fixed and each sign is an independent ±1, so a
    permutation draws a random sign vector and recomputes the total.

    p-value estimator (Davison & Hinkley 1997 §4; North, Curtis & Sham 2002)::

        p = (1 + #{ b : T*_b >= T_obs }) / (1 + n_iter)

    The "+1"s count the observed arrangement and keep ``p > 0``, so significance
    is never overstated. A small ``p`` means the observed cumulative return is
    rarely beaten by a random sign sequence → the edge is unlikely to be luck.
    (dev_docs/18 §4 family D; trading framing per Aronson 2006 Ch. 6.)

    Parameters
    ----------
    trade_returns
        1-D array of per-trade returns (signed). Magnitudes are kept; only signs
        are permuted under the null.
    n_iter
        Number of random sign permutations ``B`` (must be > 0).
    seed
        Seed for ``np.random.default_rng`` for reproducibility.

    Returns
    -------
    float
        p-value in ``(0, 1]`` — the estimated probability that a random
        sign sequence achieves a cumulative return ``>=`` the observed one.

    Raises
    ------
    ValueError
        If ``trade_returns`` is empty or ``n_iter <= 0``.
    """
    x = np.asarray(trade_returns, dtype=np.float64).ravel()
    if x.size == 0:
        raise ValueError("trade_returns must be non-empty")
    if not np.all(np.isfinite(x)):
        raise ValueError("trade_returns must be finite (no NaN/inf)")
    if n_iter <= 0:
        raise ValueError(f"n_iter must be positive, got {n_iter}")

    rng = np.random.default_rng(seed)
    observed = float(np.sum(x))
    mag = np.abs(x)

    # (n_iter, n) random signs in {-1, +1}; permuted totals = signs · |x|.
    signs = rng.integers(0, 2, size=(n_iter, x.size)) * 2 - 1
    permuted_totals = signs @ mag  # shape (n_iter,)

    n_ge = int(np.count_nonzero(permuted_totals >= observed))
    return (1 + n_ge) / (1 + n_iter)
