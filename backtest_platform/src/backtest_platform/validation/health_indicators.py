"""Strategy health-check table (6.1.3) — v2.md §4.3.1 green/yellow/red tiers.

Complements the binary edge gate (``gate_state``): where the gate answers
"is this a deployable edge? (pass/fail)", this answers "how healthy is the
strategy across 13 dimensions? (green/yellow/red)" — a richer diagnostic for the
research/validate UI, not a deploy gate.

Thresholds are **data** (``HEALTH_INDICATORS``), transcribed verbatim from
``strategy/archive/v2.md`` §4.3.1, so tuning a band is a visible, recordable edit rather
than buried logic. Pure functions, no IO. Each indicator reads its metric (or an
alias) from the metrics dict; a missing metric yields ``na`` (never silently
green). Tiering directions:

- ``higher``  : green if ``v > green``; red if ``v < red``; else yellow.
- ``lower``   : green if ``|v| < green``; red if ``|v| > red``; else yellow.
- ``range``   : green if ``green_lo <= v <= green_hi``; red if outside
                ``[red_lo, red_hi]``; else yellow.

(``max_drawdown`` / ``worst_month`` are stored signed in the engine; ``lower``
uses ``abs`` and ``worst_month`` is modelled ``higher`` on its signed value so
-8% is greener than -16%.)
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum


class HealthLight(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    NA = "na"  # metric missing — cannot assess


@dataclass(frozen=True)
class HealthIndicator:
    """One §4.3.1 row: where to read it, which way is better, and the bands."""

    key: str
    label: str
    kind: str  # "higher" | "lower" | "range"
    green: float | tuple[float, float]
    red: float | tuple[float, float]
    aliases: tuple[str, ...] = ()

    def read(self, metrics: Mapping[str, float]) -> float | None:
        for k in (self.key, *self.aliases):
            v = metrics.get(k)
            if v is not None:
                return float(v)
        return None

    def light(self, value: float | None) -> HealthLight:
        if value is None:
            return HealthLight.NA
        if self.kind == "higher":
            assert not isinstance(self.green, tuple) and not isinstance(self.red, tuple)
            if value > self.green:
                return HealthLight.GREEN
            if value < self.red:
                return HealthLight.RED
            return HealthLight.YELLOW
        if self.kind == "lower":
            assert not isinstance(self.green, tuple) and not isinstance(self.red, tuple)
            v = abs(value)
            if v < self.green:
                return HealthLight.GREEN
            if v > self.red:
                return HealthLight.RED
            return HealthLight.YELLOW
        # range
        assert isinstance(self.green, tuple) and isinstance(self.red, tuple)
        g_lo, g_hi = self.green
        r_lo, r_hi = self.red
        if g_lo <= value <= g_hi:
            return HealthLight.GREEN
        if value < r_lo or value > r_hi:
            return HealthLight.RED
        return HealthLight.YELLOW


# v2.md §4.3.1 主要指標 — 13 rows, thresholds verbatim. Aliases map the engine's
# is_harness metric names (maxdd / win / avg_hold) onto the canonical keys.
HEALTH_INDICATORS: tuple[HealthIndicator, ...] = (
    HealthIndicator("cagr", "CAGR（含生存者偏誤 buffer）", "higher", 0.18, 0.08),
    HealthIndicator("sharpe", "Sharpe Ratio", "higher", 1.0, 0.5),
    HealthIndicator("sortino", "Sortino Ratio", "higher", 1.5, 1.0),
    HealthIndicator("calmar", "Calmar Ratio", "higher", 0.5, 0.3),
    HealthIndicator("max_drawdown", "Max Drawdown", "lower", 0.25, 0.40, aliases=("maxdd",)),
    HealthIndicator("mar_ratio", "MAR Ratio (CAGR/MaxDD)", "higher", 0.5, 0.3),
    HealthIndicator("win_rate", "勝率", "higher", 0.45, 0.35, aliases=("win",)),
    HealthIndicator("profit_factor", "Profit Factor", "higher", 1.5, 1.2),
    HealthIndicator("avg_win_loss", "Avg Win / Avg Loss", "higher", 1.5, 1.0),
    HealthIndicator("expectancy", "Expectancy (R)", "higher", 0.3, 0.1),
    HealthIndicator("avg_hold_days", "平均持倉天數", "range", (5.0, 20.0), (2.0, 60.0), aliases=("avg_hold",)),
    HealthIndicator("longest_dd_months", "最長 DD 期間（月）", "lower", 6.0, 12.0),
    HealthIndicator("worst_month", "單月最大虧損", "higher", -0.10, -0.15),
)


@dataclass(frozen=True)
class HealthRow:
    """One assessed indicator — pairs the spec/value with its tier light."""

    key: str
    label: str
    value: float | None
    light: HealthLight


@dataclass(frozen=True)
class HealthReport:
    """The full 13-row health table + a roll-up of light counts."""

    rows: tuple[HealthRow, ...]

    @property
    def counts(self) -> dict[str, int]:
        out = {light.value: 0 for light in HealthLight}
        for r in self.rows:
            out[r.light.value] += 1
        return out

    @property
    def all_green(self) -> bool:
        """v2.md §4.3.1 通過標準：所有（可評估）指標達綠燈，且無缺漏。"""
        return all(r.light is HealthLight.GREEN for r in self.rows)

    def by_light(self, light: HealthLight) -> list[HealthRow]:
        return [r for r in self.rows if r.light is light]

    def to_dict(self) -> dict:
        return {
            "rows": [
                {"key": r.key, "label": r.label, "value": r.value, "light": r.light.value}
                for r in self.rows
            ],
            "counts": self.counts,
            "all_green": self.all_green,
        }


def health_check(
    metrics: Mapping[str, float],
    indicators: tuple[HealthIndicator, ...] = HEALTH_INDICATORS,
) -> HealthReport:
    """Assess a run's metrics against the §4.3.1 green/yellow/red table."""
    rows = tuple(
        HealthRow(ind.key, ind.label, val := ind.read(metrics), ind.light(val))
        for ind in indicators
    )
    return HealthReport(rows)
