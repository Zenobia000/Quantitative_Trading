"""Deflated / Probabilistic Sharpe Ratio (Bailey & López de Prado).

Pure, self-contained, IO-free statistical functions for D-class robustness
checks (dev_docs/18 §4.3 PSR + §4.4 DSR). The Sharpe ratio of a backtest is a
*point estimate*; with non-normal returns and many tried configurations it
systematically overstates skill. PSR and DSR turn that point estimate into a
probability that the true Sharpe exceeds a benchmark, correcting for

  - estimation noise (finite ``n_obs``),
  - non-normality (``skew`` ``γ3`` and ``kurtosis`` ``γ4``), and
  - selection bias from running ``n_trials`` configurations (DSR only).

References
----------
- Bailey, D. H. & López de Prado, M. (2012). "The Sharpe Ratio Efficient
  Frontier." *Journal of Risk*, 15(2). — PSR closed form, eq. for the
  Probabilistic Sharpe Ratio (see dev_docs/18 §4.3).
- Bailey, D. H. & López de Prado, M. (2014). "The Deflated Sharpe Ratio:
  Correcting for Selection Bias, Backtest Overfitting, and Non-Normality."
  *Journal of Portfolio Management*, 40(5). — DSR = PSR(SR*) and the expected
  maximum-Sharpe deflation threshold SR* (reference table 5.2; dev_docs/18 §4.4).

All functions match the formula structure in dev_docs/18 §4 exactly:
``γ3`` ↔ ``skew``, ``γ4`` ↔ ``kurtosis`` (raw, so a Gaussian has ``γ4 = 3``).
"""
from __future__ import annotations

import math

from scipy.stats import norm

__all__ = [
    "EULER_MASCHERONI",
    "psr",
    "expected_max_sharpe",
    "deflated_sharpe_ratio",
]

# Euler–Mascheroni constant γ, used in the Bailey expected-maximum approximation.
EULER_MASCHERONI: float = 0.5772156649015329


def psr(
    sr: float,
    n_obs: int,
    skew: float,
    kurtosis: float,
    sr_benchmark: float = 0.0,
) -> float:
    r"""Probabilistic Sharpe Ratio — Bailey & López de Prado (2012).

    Probability that the *true* Sharpe ratio exceeds ``sr_benchmark`` given the
    observed (non-annualized, per-period consistent) Sharpe ``sr`` estimated from
    ``n_obs`` returns with sample skewness ``γ3`` and kurtosis ``γ4``:

    .. math::

        \widehat{PSR}(SR^\*) = \Phi\!\left(
            \frac{(\widehat{SR} - SR^\*)\,\sqrt{n-1}}
                 {\sqrt{1 - \gamma_3\,\widehat{SR} + \frac{\gamma_4 - 1}{4}\,\widehat{SR}^2}}
        \right)

    where :math:`\Phi` is the standard-normal CDF. Matches dev_docs/18 §4.3.

    Parameters
    ----------
    sr:
        Observed Sharpe ratio estimate :math:`\widehat{SR}` (same periodicity as
        the moments; do **not** mix an annualized SR with per-period moments).
    n_obs:
        Number of return observations :math:`n` used to estimate ``sr``
        (must be ``> 1`` so that ``sqrt(n - 1)`` is real and positive).
    skew:
        Sample skewness :math:`\gamma_3` of the returns (0 for Gaussian).
    kurtosis:
        Sample (raw, non-excess) kurtosis :math:`\gamma_4` of the returns
        (3 for Gaussian).
    sr_benchmark:
        Threshold Sharpe :math:`SR^\*` to beat. ``0`` tests "is the strategy
        better than no skill"; for DSR this is the deflated SR* threshold.

    Returns
    -------
    float
        A probability in ``[0, 1]``.
    """
    if n_obs <= 1:
        raise ValueError(f"n_obs must be > 1 to estimate PSR, got {n_obs}")

    variance = 1.0 - skew * sr + (kurtosis - 1.0) / 4.0 * sr**2
    if variance <= 0.0:
        # Degenerate denominator (extreme skew/kurtosis vs SR). The standardized
        # statistic diverges; sign of the numerator decides the limiting prob.
        if sr > sr_benchmark:
            return 1.0
        if sr < sr_benchmark:
            return 0.0
        return 0.5

    z = (sr - sr_benchmark) * math.sqrt(n_obs - 1) / math.sqrt(variance)
    return float(norm.cdf(z))


def expected_max_sharpe(n_trials: int, variance_of_sharpes: float) -> float:
    r"""Expected maximum Sharpe across ``n_trials`` independent trials — the
    deflation threshold :math:`SR^\*` of Bailey & López de Prado (2014).

    Approximates :math:`E[\max_n SR_n]` for ``n_trials`` (= ``N``) candidate
    configurations whose Sharpe estimates have dispersion
    ``variance_of_sharpes`` (= :math:`V[SR_n]`):

    .. math::

        SR^\* = \sqrt{V[SR_n]}\,\Big[
            (1 - \gamma)\,\Phi^{-1}\!\Big(1 - \tfrac{1}{N}\Big)
            + \gamma\,\Phi^{-1}\!\Big(1 - \tfrac{1}{N\,e}\Big)
        \Big]

    where :math:`\gamma` is the Euler–Mascheroni constant and :math:`\Phi^{-1}`
    the standard-normal quantile (inverse CDF). Matches dev_docs/18 §4.4.

    The intuition: even with **no** real edge, the best of ``N`` random
    backtests has an expected Sharpe well above zero. ``SR*`` is exactly that
    "luck floor" — a strategy must clear it to be credible.

    Parameters
    ----------
    n_trials:
        Number of independent backtests / configurations tried, :math:`N \ge 1`.
        ``N == 1`` means no multiple testing ⇒ no deflation ⇒ ``SR* = 0``.
    variance_of_sharpes:
        Cross-trial variance of the Sharpe estimates, :math:`V[SR_n] \ge 0`.
        ``0`` ⇒ no dispersion to deflate ⇒ ``SR* = 0``.

    Returns
    -------
    float
        The deflated Sharpe threshold :math:`SR^\*` (non-negative).
    """
    if n_trials < 1:
        raise ValueError(f"n_trials must be >= 1, got {n_trials}")
    if variance_of_sharpes < 0.0:
        raise ValueError(
            f"variance_of_sharpes must be >= 0, got {variance_of_sharpes}"
        )

    # No multiple testing or no dispersion ⇒ nothing to deflate. This also avoids
    # Φ⁻¹(1 - 1/1) = Φ⁻¹(0) = -inf for the single-trial case.
    if n_trials == 1 or variance_of_sharpes == 0.0:
        return 0.0

    g = EULER_MASCHERONI
    z1 = norm.ppf(1.0 - 1.0 / n_trials)
    z2 = norm.ppf(1.0 - 1.0 / (n_trials * math.e))
    return float(math.sqrt(variance_of_sharpes) * ((1.0 - g) * z1 + g * z2))


def deflated_sharpe_ratio(
    sr: float,
    n_trials: int,
    n_obs: int,
    skew: float,
    kurtosis: float,
    sharpe_variance: float,
) -> float:
    r"""Deflated Sharpe Ratio — Bailey & López de Prado (2014).

    The probability that the strategy's true Sharpe exceeds the selection-bias
    benchmark :math:`SR^\*` (the expected max Sharpe under no skill):

    .. math::

        DSR = \widehat{PSR}(SR^\*),\quad
        SR^\* = E[\max_n SR_n]

    i.e. ``deflated_sharpe_ratio = psr(sr, ..., sr_benchmark=expected_max_sharpe
    (n_trials, sharpe_variance))``. Matches dev_docs/18 §4.4 (D 類). ADR-016 sets
    the M3 acceptance bar at ``DSR > 0.95``.

    Parameters
    ----------
    sr:
        Observed Sharpe ratio of the selected strategy.
    n_trials:
        Number of configurations searched (drives the deflation ``SR*``).
    n_obs:
        Number of return observations behind ``sr`` (``> 1``).
    skew, kurtosis:
        Sample skewness ``γ3`` and raw kurtosis ``γ4`` of the returns.
    sharpe_variance:
        Cross-trial variance of the Sharpe estimates, :math:`V[SR_n]`.

    Returns
    -------
    float
        A probability in ``[0, 1]``; higher = more robust to overfitting.
    """
    sr_star = expected_max_sharpe(n_trials, sharpe_variance)
    return psr(sr, n_obs=n_obs, skew=skew, kurtosis=kurtosis, sr_benchmark=sr_star)
