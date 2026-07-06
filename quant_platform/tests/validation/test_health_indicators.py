"""health_indicators — v2.md §4.3.1 green/yellow/red 13-indicator table (6.1.3)."""
from __future__ import annotations

from quant_platform.services.research_validation.validation.health_indicators import (
    HEALTH_INDICATORS,
    HealthLight,
    health_check,
)

# A fully-green metrics dict (every §4.3.1 indicator in the green band).
_GREEN = {
    "cagr": 0.25, "sharpe": 1.3, "sortino": 2.0, "calmar": 0.7,
    "max_drawdown": -0.15, "mar_ratio": 0.8, "win_rate": 0.55,
    "profit_factor": 2.0, "avg_win_loss": 1.8, "expectancy": 0.4,
    "avg_hold_days": 10.0, "longest_dd_months": 3.0, "worst_month": -0.05,
}


def test_table_has_13_indicators() -> None:
    assert len(HEALTH_INDICATORS) == 13


def test_all_green_dict_is_all_green() -> None:
    rep = health_check(_GREEN)
    assert rep.all_green
    assert rep.counts["green"] == 13
    assert rep.counts["na"] == 0


def test_higher_indicator_tiers() -> None:
    # sharpe: green >1.0, yellow 0.5-1.0, red <0.5
    assert health_check({**_GREEN, "sharpe": 1.2}).rows[1].light is HealthLight.GREEN
    assert health_check({**_GREEN, "sharpe": 0.8}).rows[1].light is HealthLight.YELLOW
    assert health_check({**_GREEN, "sharpe": 0.3}).rows[1].light is HealthLight.RED


def test_lower_indicator_uses_abs() -> None:
    # max_drawdown: green <25%, red >40% (signed in engine → abs)
    by_key = {r.key: r for r in health_check({**_GREEN, "max_drawdown": -0.20}).rows}
    assert by_key["max_drawdown"].light is HealthLight.GREEN
    assert health_check({**_GREEN, "max_drawdown": -0.30}).rows[4].light is HealthLight.YELLOW
    assert health_check({**_GREEN, "max_drawdown": -0.45}).rows[4].light is HealthLight.RED


def test_range_indicator_avg_hold() -> None:
    # avg_hold_days: green 5-20, red <2 or >60, else yellow
    get = lambda v: {r.key: r for r in health_check({**_GREEN, "avg_hold_days": v}).rows}["avg_hold_days"].light
    assert get(10) is HealthLight.GREEN
    assert get(3) is HealthLight.YELLOW   # 2-5 band
    assert get(40) is HealthLight.YELLOW  # 20-60 band
    assert get(1) is HealthLight.RED
    assert get(80) is HealthLight.RED


def test_worst_month_signed_higher() -> None:
    # worst_month: green >-10%, yellow -10~-15%, red <-15%
    get = lambda v: {r.key: r for r in health_check({**_GREEN, "worst_month": v}).rows}["worst_month"].light
    assert get(-0.05) is HealthLight.GREEN
    assert get(-0.12) is HealthLight.YELLOW
    assert get(-0.20) is HealthLight.RED


def test_aliases_resolve_engine_metric_names() -> None:
    # is_harness emits maxdd / win / avg_hold — aliases must map onto canonical keys
    m = {**_GREEN}
    del m["max_drawdown"], m["win_rate"], m["avg_hold_days"]
    m |= {"maxdd": -0.15, "win": 0.55, "avg_hold": 10.0}
    by_key = {r.key: r for r in health_check(m).rows}
    assert by_key["max_drawdown"].light is HealthLight.GREEN
    assert by_key["win_rate"].light is HealthLight.GREEN
    assert by_key["avg_hold_days"].light is HealthLight.GREEN


def test_missing_metric_is_na_not_green() -> None:
    rep = health_check({"cagr": 0.25})  # only one metric present
    assert rep.counts["na"] == 12
    assert not rep.all_green
    by_key = {r.key: r for r in rep.rows}
    assert by_key["sharpe"].light is HealthLight.NA
    assert by_key["cagr"].light is HealthLight.GREEN


def test_report_serializes() -> None:
    d = health_check(_GREEN).to_dict()
    assert d["all_green"] is True
    assert len(d["rows"]) == 13
    assert d["counts"]["green"] == 13
    assert {"key", "label", "value", "light"} <= set(d["rows"][0])
