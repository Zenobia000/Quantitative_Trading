"""compare_runs / rank_by — multi-run side-by-side comparison (8.G.5b).

Pure data processing over the runs ledger: take the dicts produced by
``run_and_judge`` / stored by ``runs_store`` (each carrying ``run_id``,
``metrics``, ``gate_status``, ``hypothesis``) and read them *relatively* —
the discipline the gate review §6 calls for (the offline sim's absolute CAGR
is not trustworthy, but the cross-run ordering and deltas are).

Three reads per comparison:

* **delta** — each run's metric minus the baseline's (the "did this change
  help?" question, answered per metric).
* **ranking** — cross-run ordering per metric, direction-aware (edge metrics
  higher-is-better, health metrics lower-is-better).
* **sign consistency** — do all runs agree in sign on a metric? Generalizes
  ``validation.gate_state.cross_window_consistent`` from 2 windows to N runs:
  a metric that flips sign across runs is a single-run-luck red flag.

No IO, no parquet — pure functions over plain dicts.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

DEFAULT_METRIC_KEYS: tuple[str, ...] = ("cagr", "sharpe", "struct1_pct", "churn_pct")

# Health metrics where a *smaller* value is better (rank ascending). Everything
# else (edge metrics: cagr, sharpe, ...) is higher-is-better (rank descending).
LOWER_IS_BETTER: frozenset[str] = frozenset({"struct1_pct", "churn_pct", "maxdd"})


@dataclass(frozen=True)
class RunComparison:
    """One run's reading relative to the baseline + its cross-run ranks."""

    run_id: str
    is_baseline: bool
    metrics: Mapping[str, float]
    delta: Mapping[str, float]   # this run − baseline, per metric_key
    rank: Mapping[str, int]      # 1-based position among all runs, per metric_key
    gate_status: str | None
    hypothesis: str | None


@dataclass(frozen=True)
class CompareReport:
    """Side-by-side comparison of N runs against one baseline."""

    baseline_id: str | None
    metric_keys: tuple[str, ...]
    comparisons: tuple[RunComparison, ...]
    rankings: Mapping[str, tuple[str, ...]]   # metric_key -> run_ids best→worst
    sign_consistent: Mapping[str, bool]       # metric_key -> all runs agree in sign?

    def by_id(self, run_id: str) -> RunComparison:
        """Look up one run's comparison; raises KeyError if absent."""
        for c in self.comparisons:
            if c.run_id == run_id:
                return c
        raise KeyError(run_id)


def _metric(record: Mapping, key: str) -> float | None:
    """Pull one metric value from a ledger record, None if absent/non-numeric."""
    metrics = record.get("metrics") or {}
    v = metrics.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _sort_key(record: Mapping, metric: str, descending: bool) -> float:
    """Sort key that pushes missing metrics to the worst end regardless of dir."""
    v = _metric(record, metric)
    if v is None:
        # Missing → worst: -inf when ranking descending, +inf when ascending,
        # so it always lands last after the direction flip below.
        return float("-inf") if descending else float("inf")
    return v


def rank_by(
    records: Sequence[Mapping],
    metric: str,
    descending: bool = True,
) -> list[dict]:
    """Return records sorted by ``metric``; missing-metric records sink last.

    Pure: the input sequence is not mutated. Stable for ties (preserves the
    input order among equal values) — ``sorted`` is stable, and the missing
    sentinel is direction-aware so absent metrics always land at the end.
    """
    decorated = sorted(
        records,
        key=lambda rec: _sort_key(rec, metric, descending),
        reverse=descending,
    )
    return [dict(rec) for rec in decorated]


def _ranking_for(records: Sequence[Mapping], metric: str) -> tuple[str, ...]:
    """Run ids ordered best→worst for one metric (direction-aware)."""
    descending = metric not in LOWER_IS_BETTER
    ordered = rank_by(records, metric, descending=descending)
    return tuple(str(r.get("run_id")) for r in ordered)


def _sign_consistent_for(records: Sequence[Mapping], metric: str) -> bool:
    """True if every run agrees in sign on ``metric``.

    Generalizes ``cross_window_consistent`` (2 windows) to N runs. A missing
    value on any run breaks consistency (cannot claim agreement on a gap), and
    an empty set is trivially consistent.
    """
    signs: set[bool] = set()
    for r in records:
        v = _metric(r, metric)
        if v is None:
            return False
        signs.add(v > 0)
    return len(signs) <= 1


def compare_runs(
    records: Sequence[Mapping],
    baseline_id: str | None = None,
    metric_keys: tuple[str, ...] = DEFAULT_METRIC_KEYS,
) -> CompareReport:
    """Compare N runs side-by-side against a baseline.

    Parameters
    ----------
    records:
        Runs-ledger dicts (``run_id`` / ``metrics`` / ``gate_status`` /
        ``hypothesis``), e.g. from ``runs_store.read_runs``.
    baseline_id:
        Which run is the reference for deltas. ``None`` defaults to the first
        record (the natural "before" in an append-only ledger). A given-but-
        absent id raises ``KeyError``.
    metric_keys:
        Which metrics to compare. Defaults to the edge+health quartet.

    Returns a frozen :class:`CompareReport`. Empty input yields an empty report.
    """
    if not records:
        return CompareReport(
            baseline_id=None,
            metric_keys=tuple(metric_keys),
            comparisons=(),
            rankings={},
            sign_consistent={},
        )

    by_id = {str(r.get("run_id")): r for r in records}

    if baseline_id is None:
        baseline_id = str(records[0].get("run_id"))
    elif baseline_id not in by_id:
        raise KeyError(
            f"baseline_id {baseline_id!r} not in records "
            f"(have {sorted(by_id)})"
        )

    baseline = by_id[baseline_id]

    # Cross-run rankings + sign consistency, per metric.
    rankings = {k: _ranking_for(records, k) for k in metric_keys}
    sign_consistent = {k: _sign_consistent_for(records, k) for k in metric_keys}
    rank_pos = {
        k: {rid: i + 1 for i, rid in enumerate(order)}
        for k, order in rankings.items()
    }

    comparisons: list[RunComparison] = []
    for r in records:
        rid = str(r.get("run_id"))
        run_metrics = {k: _metric(r, k) for k in metric_keys}
        delta: dict[str, float] = {}
        for k in metric_keys:
            rv, bv = _metric(r, k), _metric(baseline, k)
            if rv is None or bv is None:
                continue
            delta[k] = rv - bv
        comparisons.append(
            RunComparison(
                run_id=rid,
                is_baseline=(rid == baseline_id),
                metrics={k: v for k, v in run_metrics.items() if v is not None},
                delta=delta,
                rank={k: rank_pos[k][rid] for k in metric_keys},
                gate_status=r.get("gate_status"),
                hypothesis=r.get("hypothesis"),
            )
        )

    return CompareReport(
        baseline_id=baseline_id,
        metric_keys=tuple(metric_keys),
        comparisons=tuple(comparisons),
        rankings=rankings,
        sign_consistent=sign_consistent,
    )
