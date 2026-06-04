"""Run gate-as-code — ADR-016 edge gate + ADR-019 §11 health checks.

Pure functions, no IO. Feed a run's metrics dict, get per-criterion PASS/FAIL +
signed gap. Strategy-agnostic '審判庭': judges any run (v2/v3/v3.1/...) objectively,
replacing the human-brain-against-ADR check that risks self-deception.

Thresholds live in ``DEFAULT_GATE`` (data, not logic) so tuning a threshold is a
visible, recordable decision — never a silent edit.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

_OPS = {
    ">": lambda v, t: v > t,
    ">=": lambda v, t: v >= t,
    "<": lambda v, t: v < t,
    "<=": lambda v, t: v <= t,
}


class GateStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCOMPLETE = "INCOMPLETE"  # a gated metric was missing — cannot claim PASS


@dataclass(frozen=True)
class Criterion:
    key: str
    op: str          # one of >, >=, <, <=
    threshold: float
    kind: str        # "edge" (ADR-016) | "health" (ADR-019 anti-overfit)
    label: str

    def check(self, value: float) -> bool:
        return _OPS[self.op](value, self.threshold)

    def gap(self, value: float) -> float:
        """Signed toward pass: positive = margin to spare, negative = shortfall."""
        if self.op in (">", ">="):
            return value - self.threshold
        return self.threshold - value


@dataclass(frozen=True)
class CriterionResult:
    criterion: Criterion
    value: float | None
    passed: bool | None  # None = metric missing
    gap: float | None


@dataclass(frozen=True)
class GateResult:
    results: tuple[CriterionResult, ...]

    @property
    def status(self) -> GateStatus:
        if any(r.passed is None for r in self.results):
            return GateStatus.INCOMPLETE
        return GateStatus.PASS if all(r.passed for r in self.results) else GateStatus.FAIL

    @property
    def passed(self) -> bool:
        return self.status is GateStatus.PASS

    def failing(self) -> list[CriterionResult]:
        return [r for r in self.results if r.passed is False]

    def missing(self) -> list[CriterionResult]:
        return [r for r in self.results if r.passed is None]

    def summary(self) -> str:
        lines = [f"GATE: {self.status.value}"]
        for r in self.results:
            if r.passed is None:
                lines.append(f"  [N/A ] {r.criterion.label}: metric '{r.criterion.key}' missing")
            else:
                mark = "PASS" if r.passed else "FAIL"
                lines.append(
                    f"  [{mark}] {r.criterion.label}: "
                    f"{r.value:.4g} {r.criterion.op} {r.criterion.threshold:.4g} "
                    f"(gap {r.gap:+.4g})"
                )
        return "\n".join(lines)


# ADR-016 edge gate (K1/K2/K3) + ADR-019 §11 anti-overfit health checks.
# (four-layer-specific: struct1_pct/churn_pct/avg_hold are entry-quality checks.)
DEFAULT_GATE: tuple[Criterion, ...] = (
    Criterion("cagr", ">", 0.18, "edge", "K1 CAGR>18%"),
    Criterion("sharpe", ">", 1.0, "edge", "K2 Sharpe>1.0"),
    Criterion("slippage_sharpe", ">", 1.0, "edge", "K3 滑點 0.3% 下 Sharpe>1.0"),
    Criterion("struct1_pct", "<", 0.30, "health", "structure==1 中段進場<30%"),
    Criterion("churn_pct", "<", 0.20, "health", "churn<20%"),
    Criterion("avg_hold", ">=", 6.0, "health", "平均持有>=6 bar"),
)

# Momentum gate: the SAME strategy-agnostic edge criteria (K1/K2/K3) + a
# momentum-appropriate health check (diversification) instead of the four-layer
# entry-quality ones. Demonstrates the gate is data, not four-layer-bound.
MOMENTUM_GATE: tuple[Criterion, ...] = (
    Criterion("cagr", ">", 0.18, "edge", "K1 CAGR>18%"),
    Criterion("sharpe", ">", 1.0, "edge", "K2 Sharpe>1.0"),
    Criterion("slippage_sharpe", ">", 1.0, "edge", "K3 滑點 0.3% 下 Sharpe>1.0"),
    Criterion("avg_holdings", ">=", 5.0, "health", "平均持有檔數>=5 (分散，非單壓)"),
)


def evaluate_gate(
    metrics: Mapping[str, float],
    gate: tuple[Criterion, ...] = DEFAULT_GATE,
) -> GateResult:
    """Judge a run's metrics against the gate. Missing metric → INCOMPLETE (not PASS)."""
    out: list[CriterionResult] = []
    for c in gate:
        v = metrics.get(c.key)
        if v is None:
            out.append(CriterionResult(c, None, None, None))
        else:
            fv = float(v)
            out.append(CriterionResult(c, fv, c.check(fv), c.gap(fv)))
    return GateResult(tuple(out))


def cross_window_consistent(
    metrics_a: Mapping[str, float],
    metrics_b: Mapping[str, float],
    keys: tuple[str, ...] = ("cagr", "sharpe"),
) -> bool:
    """True if both windows agree in sign on each key (ADR-019 §11: no
    one-window-positive / other-deep-negative single-window-luck pattern)."""
    for k in keys:
        a, b = metrics_a.get(k), metrics_b.get(k)
        if a is None or b is None:
            return False
        if (a > 0) != (b > 0):
            return False
    return True
