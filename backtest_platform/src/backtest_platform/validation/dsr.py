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
    "deflated_sharpe_from_returns",
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


#: Fraction of the single-trial Sharpe-estimator sampling variance below which a
#: supplied ``sharpe_variance`` is treated as a units mistake (see the guard). A
#: genuine cross-trial V[SR_n] is at least the estimation noise of one trial, so a
#: value far below that floor is almost always a raw returns variance in disguise.
_SHARPE_VARIANCE_FLOOR_FRACTION: float = 0.5


def _single_trial_sharpe_variance(sr: float, n_obs: int, skew: float, kurtosis: float) -> float:
    """Asymptotic sampling variance of a per-period Sharpe estimate (Lo 2002).

    Equals the PSR denominator variance divided by ``(n_obs - 1)``. This is the
    dispersion one trial's Sharpe already carries from estimation noise alone, so
    it is the natural lower bound on any honest cross-trial ``V[SR_n]``.
    """
    return (1.0 - skew * sr + (kurtosis - 1.0) / 4.0 * sr**2) / (n_obs - 1)


def _validate_dsr_inputs(
    sr: float, n_trials: int, n_obs: int, skew: float, kurtosis: float, sharpe_variance: float
) -> None:
    """Fail fast on non-finite inputs and the classic annualized-SR + returns-variance
    units mistake that silently inflated inst_flow's DSR to 1.0 (ADR-030)."""
    for name, value in (
        ("sr", sr), ("skew", skew), ("kurtosis", kurtosis), ("sharpe_variance", sharpe_variance)
    ):
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite, got {value!r}")
    if n_obs <= 1:
        raise ValueError(f"n_obs must be > 1 to estimate DSR, got {n_obs}")
    # Deflation is only active for n_trials > 1; an explicit 0 variance ("no
    # cross-trial dispersion") is legitimate and left alone.
    if n_trials > 1 and sharpe_variance > 0.0:
        floor = _SHARPE_VARIANCE_FLOOR_FRACTION * _single_trial_sharpe_variance(
            sr, n_obs, skew, kurtosis
        )
        if floor > 0.0 and sharpe_variance < floor:
            raise ValueError(
                f"sharpe_variance {sharpe_variance:.3g} is below the single-trial "
                f"estimator floor {floor:.3g} for n_obs={n_obs}; this is the signature "
                "of a units error — DSR needs the cross-trial variance of PER-PERIOD "
                "Sharpe estimates V[SR_n], not a raw daily-returns variance (dev_docs/18 §4.4)"
            )


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

    Raises
    ------
    ValueError
        On non-finite inputs, ``n_obs <= 1``, or a ``sharpe_variance`` far below
        the single-trial estimator floor (the annualized-SR + returns-variance
        units mistake — see :func:`_validate_dsr_inputs`).
    """
    _validate_dsr_inputs(sr, n_trials, n_obs, skew, kurtosis, sharpe_variance)
    sr_star = expected_max_sharpe(n_trials, sharpe_variance)
    return psr(sr, n_obs=n_obs, skew=skew, kurtosis=kurtosis, sr_benchmark=sr_star)


def deflated_sharpe_from_returns(returns, *, n_trials: int) -> float:
    """Trials-deflated Sharpe straight from a daily-returns series (ADR-036 促成的
    升格：原 ``research/workflows/truth_gate.py::_deflated_sharpe``，搬進 validation
    層成為單一真相源——truth gate 與 portfolio gate 共用同一條單位正確的路徑).

    DSR needs PER-PERIOD statistics — never the ×√252 annualized Sharpe（ADR-030
    修正的單位 bug）。Sharpe 以原始日報酬 ``mean / std`` 重算；``V[SR_n]`` 用
    null-hypothesis floor（Lo 2002 estimator variance）—— pre-registered 單一
    config 沒有 sweep landscape 可量測時**最寬鬆的誠實通縮**。Degenerate 輸入
    （< 2 筆、零變異）回 0.0。
    """
    import numpy as np
    import pandas as pd

    arr = np.asarray(returns, dtype=float)
    arr = arr[np.isfinite(arr)]
    n_obs = arr.size
    if n_obs < 2:
        return 0.0
    sd = float(arr.std(ddof=0))
    if sd <= 0.0:
        return 0.0
    sr_pp = float(arr.mean()) / sd
    s = pd.Series(arr)
    skew = float(s.skew()) if n_obs > 3 else 0.0
    kurt = float(s.kurtosis()) + 3.0 if n_obs > 3 else 3.0  # pandas excess → raw
    estimator_var = (1.0 - skew * sr_pp + (kurt - 1.0) / 4.0 * sr_pp**2) / (n_obs - 1)
    sharpe_variance = max(estimator_var, 0.0)
    return deflated_sharpe_ratio(
        sr=sr_pp, n_trials=n_trials, n_obs=n_obs,
        skew=skew, kurtosis=kurt, sharpe_variance=sharpe_variance,
    )
