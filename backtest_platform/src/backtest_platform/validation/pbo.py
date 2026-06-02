"""Probability of Backtest Overfitting (PBO) via CSCV.

Pure-function implementation of the Combinatorially-Symmetric Cross-Validation
(CSCV) estimator of the Probability of Backtest Overfitting. Self-contained:
depends only on ``numpy`` / ``scipy`` (no other project modules), so it can be
built in parallel with sibling validation modules.

Reference
---------
Bailey, D. H., Borwein, J. M., López de Prado, M., & Zhu, Q. J. (2017).
*The probability of backtest overfitting.* Journal of Computational Finance,
20(4), 39-69.  https://doi.org/10.21314/JCF.2016.322

Why CSCV (paper §3, §4)
-----------------------
Given a matrix ``M`` of ``T`` observations × ``N`` strategy configurations, a
researcher who optimises a performance statistic (here Sharpe) over the *N*
configs in-sample (IS) overstates expected out-of-sample (OOS) performance. PBO
estimates the probability that the IS-optimal configuration under-performs the
*median* configuration OOS — i.e. that the selection was driven by overfitting
rather than skill.

Algorithm (paper §3, the CSCV procedure)
----------------------------------------
1. Partition the ``T`` rows into ``S`` disjoint sub-matrices of equal size
   (``S`` even).                                                      (paper §3.1)
2. Form **all** ``C(S, S/2)`` combinations ``c`` that assign exactly ``S/2``
   sub-matrices to the IS set ``J_c``; the complement ``J̄_c`` is the OOS set.
   This symmetric enumeration is what makes CSCV unbiased.            (paper §3.2)
3. For each combination ``c``:
   a. Build IS matrix ``J`` (the chosen sub-matrices, row-stacked) and OOS
      matrix ``J̄`` (the rest).
   b. Compute the performance vector ``R^c  = metric(J)``   over the N configs,
      and          ``R̄^c = metric(J̄)``.                              (paper Eq. 2)
   c. ``n*_c = argmax_n R^c_n``  — the IS-optimal configuration.       (paper Eq. 3)
   d. Rank ``n*_c`` among the N configs by OOS performance ``R̄^c``,
      giving rank ``r_c ∈ {1..N}`` (1 = worst, N = best). Define the
      **relative rank**            ``ω̄_c = r_c / (N + 1) ∈ (0, 1)``.   (paper Eq. 4)
   e. **Logit**                    ``λ_c = ln( ω̄_c / (1 - ω̄_c) )``.    (paper Eq. 5)
      ``λ_c ≤ 0``  ⇔ the IS-best config sits at or below the OOS median.
4. The distribution of ``{λ_c}`` is the OOS-performance-degradation distribution
   ``f(λ)``. PBO is the relative frequency of overfit combinations:
            ``PBO = (1 / N_c) · Σ_c  1[ λ_c ≤ 0 ]``.                   (paper Eq. 6)

Interpretation
--------------
* ``PBO ≈ 0.5`` — IS selection is no better than a coin flip OOS (pure noise).
* ``PBO → 0``   — IS-best persistently wins OOS (a genuine, robust edge).
* ``PBO → 1``   — IS-best is systematically a *loser* OOS (severe overfitting).

ADR-016 M3 gate: ``PBO < 0.30``.
"""
from __future__ import annotations

from collections.abc import Callable
from itertools import combinations

import numpy as np

__all__ = ["probability_of_backtest_overfitting", "sharpe_metric"]

# A metric maps an [T x N] return block to an [N] performance vector. Higher is
# better; only the *ordering* it induces matters for CSCV.
Metric = Callable[[np.ndarray], np.ndarray]

_ANNUALISATION = 252.0  # trading days; cancels in ranking but keeps Sharpe scale


def sharpe_metric(block: np.ndarray) -> np.ndarray:
    """Annualised Sharpe ratio per configuration.

    ``SR_n = mean(r_n) / std(r_n, ddof=1) * sqrt(252)``  (Sharpe, 1966).

    Columns with zero variance yield ``-inf`` so they never rank as IS-best
    (a flat config carries no information). NaNs in the input propagate to a
    safe ``-inf`` rather than poisoning the argmax.

    Parameters
    ----------
    block : np.ndarray, shape (rows, N)
        Per-period returns for each configuration.

    Returns
    -------
    np.ndarray, shape (N,)
    """
    mean = block.mean(axis=0)
    std = block.std(axis=0, ddof=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        sr = mean / std * np.sqrt(_ANNUALISATION)
    # zero/NaN variance -> not a valid candidate
    sr = np.where(np.isfinite(sr), sr, -np.inf)
    return sr


def _validate(returns_matrix: np.ndarray, n_splits: int) -> None:
    if returns_matrix.ndim != 2:
        raise ValueError(
            f"returns_matrix must be 2-D [T x N_configs], got {returns_matrix.ndim}-D"
        )
    t_rows, n_configs = returns_matrix.shape
    if n_configs < 2:
        raise ValueError(
            f"need >= 2 configs to rank IS-best OOS, got {n_configs} config(s)"
        )
    if n_splits < 2 or n_splits % 2 != 0:
        raise ValueError(f"n_splits must be an even integer >= 2, got {n_splits}")
    if n_splits > t_rows:
        raise ValueError(
            f"n_splits ({n_splits}) cannot exceed number of rows ({t_rows})"
        )


def probability_of_backtest_overfitting(
    returns_matrix: np.ndarray,
    n_splits: int = 16,
    metric: Metric = sharpe_metric,
) -> float:
    """Estimate the Probability of Backtest Overfitting via CSCV.

    Implements Bailey, Borwein, López de Prado & Zhu (2017), §3 (CSCV) and the
    PBO estimator of Eq. 6. See the module docstring for the full derivation and
    per-step equation references.

    Parameters
    ----------
    returns_matrix : np.ndarray, shape (T, N_configs)
        Per-period returns; column ``n`` is the return series of configuration
        ``n``. ``T`` is the time dimension that CSCV partitions.
    n_splits : int, default 16
        Number of disjoint row sub-matrices ``S`` (must be even). The estimator
        enumerates all ``C(S, S/2)`` symmetric IS/OOS splits — e.g. ``S=8`` gives
        ``C(8,4)=70`` combinations, ``S=16`` gives ``C(16,8)=12870``.
    metric : Callable[[np.ndarray], np.ndarray], default ``sharpe_metric``
        Performance functional mapping an ``[rows x N]`` block to an ``[N]``
        vector; higher = better. Only the induced ranking matters.

    Returns
    -------
    float
        PBO ∈ [0, 1]: relative frequency of splits whose IS-optimal config has
        a non-positive OOS logit (``λ ≤ 0``), i.e. ranks at/below the OOS median.

    Raises
    ------
    ValueError
        If the input is not 2-D, has < 2 configs, ``n_splits`` is not an even
        integer ≥ 2, or ``n_splits`` exceeds the number of rows.

    Notes
    -----
    Rows are truncated to ``S * (T // S)`` so all sub-matrices are equal-sized,
    as required by the symmetric construction (paper §3.1). The estimator is
    fully deterministic — identical input yields identical output.
    """
    returns_matrix = np.asarray(returns_matrix, dtype=float)
    _validate(returns_matrix, n_splits)

    t_rows, n_configs = returns_matrix.shape
    s = n_splits
    block = t_rows // s
    usable = block * s
    # Equal-sized sub-matrices: trailing partial rows are dropped (paper §3.1).
    trimmed = returns_matrix[:usable]
    # sub_blocks[i] is the i-th disjoint row sub-matrix, shape (block, N).
    sub_blocks = [trimmed[i * block : (i + 1) * block] for i in range(s)]

    all_indices = set(range(s))
    half = s // 2
    n_below_median = 0  # count of λ_c <= 0 (Eq. 6 indicator sum)
    n_combos = 0

    for is_idx in combinations(range(s), half):
        oos_idx = tuple(sorted(all_indices - set(is_idx)))

        is_block = np.vstack([sub_blocks[i] for i in is_idx])
        oos_block = np.vstack([sub_blocks[i] for i in oos_idx])

        r_is = metric(is_block)        # R^c   (paper Eq. 2)
        r_oos = metric(oos_block)      # R̄^c

        n_star = int(np.argmax(r_is))  # n*_c  (paper Eq. 3)

        # OOS rank of n*_c: 1 = worst .. N = best. Average-rank ties so a config
        # tied at the median maps to ω̄ = 0.5 → λ = 0 (counted as overfit).
        rank = _average_rank(r_oos)[n_star]  # r_c (paper Eq. 4)

        omega = rank / (n_configs + 1.0)     # ω̄_c ∈ (0, 1)  (paper Eq. 4)
        # logit; ω̄ <= 0.5  ⇔  λ <= 0  ⇔  at/below OOS median (paper Eq. 5)
        lam = np.log(omega / (1.0 - omega))

        if lam <= 0.0:
            n_below_median += 1
        n_combos += 1

    # PBO = relative frequency of overfit splits (paper Eq. 6).
    return n_below_median / n_combos


def _average_rank(values: np.ndarray) -> np.ndarray:
    """1-based average ranks (1 = smallest). Ties share their mean rank.

    Average ranking keeps the median anchor exact: a config tied with the
    middle of the distribution receives the median rank, so ``ω̄`` lands on 0.5
    and ``λ`` on 0, correctly classified as 'not beating the median'.
    """
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    ranks[order] = np.arange(1, len(values) + 1, dtype=float)
    # resolve ties to the average of their rank positions
    unique_vals, inv, counts = np.unique(values, return_inverse=True, return_counts=True)
    if np.any(counts > 1):
        sums = np.zeros(len(unique_vals))
        np.add.at(sums, inv, ranks)
        avg = sums / counts
        ranks = avg[inv]
    return ranks
