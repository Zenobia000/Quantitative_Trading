"""Portfolio gate (ADR-036) — pod/sleeve combine + sizing policy + stop-outs.

The ADR-036 thesis test: two modest-Sharpe, low-correlation sleeves blend into
a portfolio whose deflated Sharpe beats either standalone — the diversification
premium the standalone-only 審判庭 could not see.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest_platform.validation.portfolio_gate import (
    apply_stop_outs,
    combine_returns,
    portfolio_gate_report,
    sleeve_weights,
)
from backtest_platform.validation.two_stage_gate import SizingConfig, SizingInput


def _dates(n: int, start: str = "2025-01-01") -> pd.DatetimeIndex:
    return pd.bdate_range(start, periods=n)


def _sleeve(n: int, sharpe_pp: float, seed: int, vol: float = 0.01) -> pd.Series:
    """Deterministic synthetic daily returns with per-period Sharpe ≈ sharpe_pp."""
    rng = np.random.RandomState(seed)
    noise = rng.normal(0.0, vol, n)
    return pd.Series(noise + sharpe_pp * vol, index=_dates(n))


# ---------------------------------------------------------------------------
# combine_returns
# ---------------------------------------------------------------------------
def test_combine_returns_equal_weight_default() -> None:
    a = pd.Series([0.01, 0.02], index=_dates(2))
    b = pd.Series([0.03, 0.04], index=_dates(2))
    out = combine_returns({"a": a, "b": b})
    assert out.tolist() == pytest.approx([0.02, 0.03])


def test_combine_returns_custom_weights_renormalized() -> None:
    a = pd.Series([0.01, 0.01], index=_dates(2))
    b = pd.Series([0.03, 0.03], index=_dates(2))
    # weights 3:1 (sum 4 → renormalized 0.75/0.25)
    out = combine_returns({"a": a, "b": b}, weights={"a": 3.0, "b": 1.0})
    assert out.tolist() == pytest.approx([0.015, 0.015])


def test_combine_returns_inner_joins_on_dates() -> None:
    a = pd.Series([0.01, 0.02, 0.03], index=_dates(3))
    b = pd.Series([0.10, 0.20], index=_dates(3)[1:])  # misses first day
    out = combine_returns({"a": a, "b": b})
    assert len(out) == 2
    assert out.iloc[0] == pytest.approx((0.02 + 0.10) / 2)


def test_combine_returns_single_sleeve_passthrough() -> None:
    a = pd.Series([0.01, -0.02], index=_dates(2))
    out = combine_returns({"solo": a})
    assert out.tolist() == pytest.approx(a.tolist())


def test_combine_returns_empty_raises() -> None:
    with pytest.raises(ValueError, match="sleeve"):
        combine_returns({})


def test_combine_returns_unknown_weight_key_raises() -> None:
    a = pd.Series([0.01], index=_dates(1))
    with pytest.raises(ValueError, match="weight"):
        combine_returns({"a": a}, weights={"a": 1.0, "ghost": 1.0})


# ---------------------------------------------------------------------------
# sleeve_weights — ADR-025 SizingGate 的首個生產呼叫者 + hysteresis
# ---------------------------------------------------------------------------
def test_sleeve_weights_maps_compute_position_size() -> None:
    w = sleeve_weights({"s1": SizingInput(oos_sharpe=1.0)})  # saturated conviction
    assert w == {"s1": pytest.approx(SizingConfig().max_weight)}


def test_sleeve_weights_orthogonal_beats_correlated() -> None:
    w = sleeve_weights(
        {
            "orthogonal": SizingInput(oos_sharpe=0.9, correlation_to_fleet=0.1),
            "clone": SizingInput(oos_sharpe=0.9, correlation_to_fleet=0.9),
        }
    )
    assert w["orthogonal"] > w["clone"] * 5  # diversification factor 0.9 vs 0.1


def test_sleeve_weights_hysteresis_keeps_previous_on_small_change() -> None:
    prev = {"s1": 0.20}
    w = sleeve_weights(
        {"s1": SizingInput(oos_sharpe=0.9)},  # raw = 0.25*0.9 = 0.225 (+12.5% < 20%)
        previous=prev,
        hysteresis=0.2,
    )
    assert w["s1"] == pytest.approx(0.20)  # unchanged — no capital churn on noise


def test_sleeve_weights_hysteresis_moves_on_large_change() -> None:
    prev = {"s1": 0.10}
    w = sleeve_weights(
        {"s1": SizingInput(oos_sharpe=0.9)},  # raw 0.225 (+125% > 20%)
        previous=prev,
        hysteresis=0.2,
    )
    assert w["s1"] == pytest.approx(0.225)


def test_sleeve_weights_new_sleeve_ignores_hysteresis() -> None:
    w = sleeve_weights(
        {"new": SizingInput(oos_sharpe=1.0)}, previous={}, hysteresis=0.2
    )
    assert w["new"] == pytest.approx(0.25)


# ---------------------------------------------------------------------------
# apply_stop_outs — pod 式離散停損
# ---------------------------------------------------------------------------
def test_apply_stop_outs_zeroes_breached_sleeve() -> None:
    out = apply_stop_outs(
        {"ok": 0.2, "bleeding": 0.25},
        drawdowns={"ok": -0.05, "bleeding": -0.16},
        max_drawdown=0.15,
    )
    assert out == {"ok": 0.2, "bleeding": 0.0}


def test_apply_stop_outs_boundary_not_breached() -> None:
    out = apply_stop_outs({"s": 0.2}, drawdowns={"s": -0.15}, max_drawdown=0.15)
    assert out == {"s": 0.2}  # 停損是「超過」不是「達到」


def test_apply_stop_outs_missing_drawdown_untouched() -> None:
    out = apply_stop_outs({"s": 0.2}, drawdowns={}, max_drawdown=0.15)
    assert out == {"s": 0.2}


def test_apply_stop_outs_is_immutable() -> None:
    weights = {"s": 0.2}
    apply_stop_outs(weights, drawdowns={"s": -0.9}, max_drawdown=0.15)
    assert weights == {"s": 0.2}  # input never mutated


# ---------------------------------------------------------------------------
# portfolio_gate_report — ADR-036 核心論點
# ---------------------------------------------------------------------------
def test_portfolio_report_diversification_premium() -> None:
    """兩個中等 per-period Sharpe、低相關艙位：合成 DSR > 兩者 standalone DSR。"""
    n = 500
    cand = _sleeve(n, sharpe_pp=0.05, seed=7)
    fleet = _sleeve(n, sharpe_pp=0.05, seed=99)  # independent noise → low corr

    rep = portfolio_gate_report("cand", cand, {"fleet_a": fleet}, n_trials=1)

    assert 0.0 <= rep.standalone_dsr <= 1.0
    assert rep.portfolio_dsr > rep.standalone_dsr  # the diversification premium
    assert abs(rep.correlation_to_fleet) < 0.3
    assert rep.n_obs == n
    assert rep.sleeve_ids == ("cand", "fleet_a")


def test_portfolio_report_clone_gets_no_premium() -> None:
    """與艦隊近乎複製的候選：合成不該顯著優於 standalone。"""
    n = 500
    cand = _sleeve(n, sharpe_pp=0.05, seed=7)
    clone = cand * 1.001  # correlation ≈ 1

    rep = portfolio_gate_report("cand", cand, {"clone": clone}, n_trials=1)

    assert rep.correlation_to_fleet > 0.99
    assert rep.portfolio_dsr == pytest.approx(rep.standalone_dsr, abs=0.05)


def test_portfolio_report_empty_fleet_portfolio_equals_standalone() -> None:
    cand = _sleeve(300, sharpe_pp=0.05, seed=3)
    rep = portfolio_gate_report("cand", cand, {}, n_trials=1)
    assert rep.portfolio_dsr == pytest.approx(rep.standalone_dsr)
    assert rep.correlation_to_fleet == 0.0
    assert rep.sleeve_ids == ("cand",)


def test_portfolio_report_carries_suggested_weight() -> None:
    """報告附 ADR-025 sizing 建議權重（oos_sharpe 用 per-period→年化換算前的輸入由呼叫者給）。"""
    cand = _sleeve(300, sharpe_pp=0.05, seed=3)
    rep = portfolio_gate_report(
        "cand", cand, {}, n_trials=1, candidate_oos_sharpe=0.9
    )
    assert rep.suggested_weight == pytest.approx(0.25 * 0.9)  # corr 0 → no penalty


# ---------------------------------------------------------------------------
# DSR 升格 oracle — deflated_sharpe_from_returns 必須与 truth_gate 舊路徑一致
# ---------------------------------------------------------------------------
def test_deflated_sharpe_from_returns_matches_truth_gate_oracle() -> None:
    """單一真相源檢查：validation.dsr 的公開函式 == truth_gate 委派後的結果。"""
    from backtest_platform.research.workflows.truth_gate import _deflated_sharpe
    from backtest_platform.validation.dsr import deflated_sharpe_from_returns

    r = _sleeve(400, sharpe_pp=0.06, seed=42)
    assert deflated_sharpe_from_returns(r, n_trials=24) == pytest.approx(
        _deflated_sharpe(r, 24)
    )


def test_deflated_sharpe_from_returns_degenerate_inputs() -> None:
    from backtest_platform.validation.dsr import deflated_sharpe_from_returns

    assert deflated_sharpe_from_returns(pd.Series(dtype=float), n_trials=1) == 0.0
    assert deflated_sharpe_from_returns(pd.Series([0.01]), n_trials=1) == 0.0
    assert deflated_sharpe_from_returns(pd.Series([0.01] * 50), n_trials=1) == 0.0  # zero var
