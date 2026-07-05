"""Trial-count → Deflated-Sharpe gate (8.G.4).

Comparing or scanning more configurations makes a high backtest Sharpe more
likely to be luck than edge — "the more you try, the closer you get to false
significance". This module turns that selection-bias intuition into an operable
guardrail on top of :mod:`backtest_platform.validation.dsr`:

- :class:`TrialsCounter` — accumulate how many trials (configs / comparisons /
  scans) were actually run, so the deflation count is auditable rather than
  guessed.
- :func:`deflated_sharpe_pass` — the boolean bar: compute the Deflated Sharpe
  Ratio for ``n_trials`` and test it against ADR-016's ``DSR > 0.95``.
- :func:`trials_deflated_criterion` — a gate-pluggable
  ``(label, passed, dsr_value, n_trials)`` structure so the question "I tried N
  times, what did my Sharpe get deflated to?" is visible in the gate summary.

The actual DSR math lives in ``validation.dsr`` (Bailey & López de Prado 2014);
this module only does *accounting* and *gating* around it. ADR-016 sets the M3
acceptance bar at ``DSR > 0.95`` (see dev_docs/18 §4.4).
"""
from __future__ import annotations

from dataclasses import dataclass

from backtest_platform.validation.dsr import deflated_sharpe_ratio

__all__ = [
    "DSR_THRESHOLD",
    "TrialsCounter",
    "TrialsDeflatedResult",
    "deflated_sharpe_pass",
    "trials_deflated_criterion",
]

# ADR-016 M3 acceptance bar: a strategy must clear DSR > 0.95 to be credible
# after correcting for how many configurations were searched.
DSR_THRESHOLD: float = 0.95


class TrialsCounter:
    """Mutable, cumulative count of trials (configs / comparisons / scans) run.

    Each :meth:`record` adds to the running total exposed by :attr:`n_trials`,
    which then feeds the deflation in :func:`deflated_sharpe_pass` /
    :func:`trials_deflated_criterion`. Kept deliberately small and mutable: it is
    an *accumulator* (a tally that grows as a search proceeds), not an immutable
    value object.

    Parameters
    ----------
    n_trials:
        Starting count, ``>= 0`` (default ``0``). Use a non-zero seed to resume a
        tally carried over from an earlier search phase.
    """

    __slots__ = ("_n",)

    def __init__(self, n_trials: int = 0) -> None:
        if n_trials < 0:
            raise ValueError(f"n_trials must be >= 0, got {n_trials}")
        self._n = int(n_trials)

    @property
    def n_trials(self) -> int:
        """Cumulative number of trials recorded so far."""
        return self._n

    def record(self, count: int = 1) -> int:
        """Add ``count`` trials to the tally and return the new total.

        Parameters
        ----------
        count:
            Number of trials to add, must be ``>= 1`` (default ``1``). A batch of
            comparisons can be recorded in one call.

        Returns
        -------
        int
            The updated :attr:`n_trials`.
        """
        if count < 1:
            raise ValueError(f"count must be >= 1, got {count}")
        self._n += int(count)
        return self._n

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"TrialsCounter(n_trials={self._n})"


@dataclass(frozen=True)
class TrialsDeflatedResult:
    """Gate-pluggable outcome of the trials → DSR deflation check.

    Unpacks as ``(label, passed, dsr_value, n_trials)`` so it can be appended to
    a gate's result list while still exposing named fields. ``label`` is built to
    surface both the trial count and the deflated DSR for the gate summary.
    """

    label: str
    passed: bool
    dsr_value: float
    n_trials: int

    def __iter__(self):
        """Allow ``label, passed, dsr_value, n_trials = result`` unpacking."""
        yield self.label
        yield self.passed
        yield self.dsr_value
        yield self.n_trials


def deflated_sharpe_pass(
    sr: float,
    n_trials: int,
    n_obs: int,
    skew: float,
    kurtosis: float,
    sharpe_variance: float,
    threshold: float = DSR_THRESHOLD,
) -> bool:
    """Does the Deflated Sharpe clear the bar after ``n_trials`` were searched?

    Computes :func:`~backtest_platform.validation.dsr.deflated_sharpe_ratio` and
    tests it with a **strict** ``>`` against ``threshold`` (ADR-016 ``DSR > 0.95``
    by default). Because the deflation threshold ``SR*`` grows with ``n_trials``,
    the returned DSR is non-increasing in ``n_trials`` — so the same realized
    Sharpe can flip from pass to fail purely by virtue of having compared more
    configurations.

    Parameters
    ----------
    sr:
        Observed Sharpe ratio of the selected strategy.
    n_trials:
        Number of configurations / comparisons searched (``>= 1``). Drives the
        selection-bias deflation.
    n_obs:
        Number of return observations behind ``sr`` (``> 1``).
    skew, kurtosis:
        Sample skewness ``γ3`` and raw kurtosis ``γ4`` of the returns.
    sharpe_variance:
        Cross-trial variance of the Sharpe estimates ``V[SR_n]``.
    threshold:
        DSR bar to clear, strictly (default :data:`DSR_THRESHOLD` = 0.95).

    Returns
    -------
    bool
        ``True`` iff ``DSR > threshold``.
    """
    dsr = deflated_sharpe_ratio(
        sr=sr,
        n_trials=n_trials,
        n_obs=n_obs,
        skew=skew,
        kurtosis=kurtosis,
        sharpe_variance=sharpe_variance,
    )
    return dsr > threshold


def trials_deflated_criterion(
    sr: float,
    n_trials: int,
    n_obs: int,
    skew: float,
    kurtosis: float,
    sharpe_variance: float,
    threshold: float = DSR_THRESHOLD,
) -> TrialsDeflatedResult:
    """Build a gate-pluggable ``(label, passed, dsr_value, n_trials)`` result.

    Same inputs as :func:`deflated_sharpe_pass`, but returns the full
    :class:`TrialsDeflatedResult` so a gate / report can show *why* a run did or
    did not clear the trials-deflated bar — the trial count and the deflated DSR
    are both surfaced in ``label``.

    Returns
    -------
    TrialsDeflatedResult
        Frozen, tuple-unpackable record of the deflation check.
    """
    dsr = deflated_sharpe_ratio(
        sr=sr,
        n_trials=n_trials,
        n_obs=n_obs,
        skew=skew,
        kurtosis=kurtosis,
        sharpe_variance=sharpe_variance,
    )
    passed = dsr > threshold
    label = (
        f"D4 trials-deflated DSR>{threshold:.4g} "
        f"(n_trials={n_trials}, DSR={dsr:.4g})"
    )
    return TrialsDeflatedResult(
        label=label,
        passed=passed,
        dsr_value=float(dsr),
        n_trials=int(n_trials),
    )
