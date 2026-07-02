"""truth_gate 審判庭 judgement fixes (ADR-030) — pins the four proven defects.

These tests drive ``run_truth_gate`` through a controllable fake runner (injected
by monkeypatching the ``get_strategy`` seam) so the daily-returns series, and thus
every downstream statistic, is deterministic. The point is to nail the *verdict*,
not merely that a float came back:

  * DSR is computed in PER-PERIOD units (annualized SR × √252 fed to the deflater
    inflated inst_flow's DSR to 1.0 — the CRITICAL bug).
  * The OOS holdout window ``[oos_start, is_end]`` is actually executed.
  * ``survivorship_clean`` is config-driven and defaults to False (never a hardwired
    green light).
  * A REAL verdict flows into the ADR-025 SizingGate → a position recommendation.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
from pydantic import BaseModel

from backtest_platform.research.workflows import truth_gate as tg_mod
from backtest_platform.research.workflows.config import TruthGateConfig
from backtest_platform.research.workflows.truth_gate import TruthGateResult, run_truth_gate
from backtest_platform.strategies.protocol import StrategyRun
from backtest_platform.validation.two_stage_gate import DSR_MIN


class _RecConfig(BaseModel):
    """Minimal frozen config with a ``slip_rate`` field (so ``_add_slippage`` works)."""

    model_config = {"frozen": True}
    slip_rate: float = 0.001


def _returns_with_annual_sharpe(ann_sharpe: float, n: int = 1260, std: float = 0.01) -> pd.Series:
    """Deterministic daily returns whose per-period Sharpe == ``ann_sharpe / √252``.

    A standard-normal sample is normalized to exact mean 0 / population std 1, then
    rescaled so ``mean / std(ddof=0)`` equals the target per-period Sharpe exactly.
    """
    rng = np.random.default_rng(0)
    r = rng.normal(0.0, 1.0, n)
    r = (r - r.mean()) / r.std()  # exact mean 0, population std 1
    per_period = ann_sharpe / np.sqrt(252)
    return pd.Series(r * std + per_period * std)


class _FakeRunner:
    """Records every ``(start, end)`` window and returns a controllable StrategyRun."""

    config_model = _RecConfig
    title = "fake"

    def __init__(self, ann_sharpe: float, n: int = 1260):
        self.ann_sharpe = ann_sharpe
        self.n = n
        self.windows: list[tuple] = []

    def run(self, symbols, start, end, config, loader):
        self.windows.append((start, end))
        metrics = {
            "sharpe": self.ann_sharpe,
            "slippage_sharpe": max(self.ann_sharpe, 0.1),
            "cagr": 0.2, "maxdd": -0.1, "trades": 10, "bars": self.n,
        }
        return StrategyRun(metrics, _returns_with_annual_sharpe(self.ann_sharpe, self.n))


def _cfg(*, n_trials: int, survivorship_clean: bool | None = None) -> TruthGateConfig:
    extra = {} if survivorship_clean is None else {"survivorship_clean": survivorship_clean}
    return TruthGateConfig(
        strategy="fake",
        fixed_config=_RecConfig(),
        symbols=["A", "B"],
        is_start=date(2015, 1, 1),
        oos_start=date(2021, 1, 1),
        is_end=date(2024, 12, 31),
        n_trials=n_trials,
        n_wfa_folds=3,
        **extra,
    )


def _run(runner: _FakeRunner, monkeypatch, cfg: TruthGateConfig) -> TruthGateResult:
    monkeypatch.setattr(tg_mod, "get_strategy", lambda name: runner)
    return run_truth_gate(cfg, loader=lambda s: pd.DataFrame())


# --------------------------------------------------------------------------- #
# Bug #1 — DSR unit error: annualized SR must NOT deflate to ~1.0
# --------------------------------------------------------------------------- #


def test_dsr_uses_per_period_units_and_rejects_modest_sharpe(monkeypatch):
    """Annualized Sharpe 0.333 searched over 16 trials → DSR far below the 0.95 bar.

    Under the old bug (annualized SR + daily returns variance) this deflated to
    1.000000 (certain skill). The correct per-period computation makes it a
    coin-flip-or-worse → REJECTED. This is the judgement-level oracle.
    """
    runner = _FakeRunner(ann_sharpe=0.333)
    result = _run(runner, monkeypatch, _cfg(n_trials=16, survivorship_clean=True))
    assert result.dsr < DSR_MIN            # 0.95 bar — old bug returned ~1.0
    assert result.dsr < 0.5                # ~0.145 — not remotely "certain skill"
    assert result.verdict == "REJECTED"
    assert any("dsr" in reason.lower() for reason in result.reasons)


def test_strong_strategy_still_clears_dsr_bar(monkeypatch):
    """A genuine, lightly-searched Sharpe-3 strategy still passes DSR>0.95."""
    runner = _FakeRunner(ann_sharpe=3.0)
    result = _run(runner, monkeypatch, _cfg(n_trials=2, survivorship_clean=True))
    assert result.dsr > DSR_MIN


# --------------------------------------------------------------------------- #
# Bug #2 — OOS holdout [oos_start, is_end] must actually be evaluated
# --------------------------------------------------------------------------- #


def test_oos_holdout_window_is_executed(monkeypatch):
    runner = _FakeRunner(ann_sharpe=1.0)
    _run(runner, monkeypatch, _cfg(n_trials=4, survivorship_clean=True))
    assert (date(2021, 1, 1), date(2024, 12, 31)) in runner.windows


def test_oos_holdout_sharpe_surfaced_in_details(monkeypatch):
    runner = _FakeRunner(ann_sharpe=1.0)
    result = _run(runner, monkeypatch, _cfg(n_trials=4, survivorship_clean=True))
    assert "oos_holdout_sharpe" in result.details
    assert result.details["oos_holdout_sharpe"] == 1.0


# --------------------------------------------------------------------------- #
# Bug #3 — survivorship_clean is config-driven and defaults to False
# --------------------------------------------------------------------------- #


def test_survivorship_defaults_false_and_rejects(monkeypatch):
    """A stellar strategy is still REJECTED when survivorship is not declared clean."""
    runner = _FakeRunner(ann_sharpe=3.0)
    result = _run(runner, monkeypatch, _cfg(n_trials=2))  # survivorship_clean unset
    assert result.verdict == "REJECTED"
    assert any("survivorship" in reason.lower() for reason in result.reasons)


def test_survivorship_declared_clean_is_not_rejected_on_survivorship(monkeypatch):
    runner = _FakeRunner(ann_sharpe=3.0)
    result = _run(runner, monkeypatch, _cfg(n_trials=2, survivorship_clean=True))
    assert not any("survivorship" in reason.lower() for reason in result.reasons)


# --------------------------------------------------------------------------- #
# Bug #5 — SizingGate (ADR-025 stage 2) is wired: REAL → a position size
# --------------------------------------------------------------------------- #


def test_real_verdict_produces_position_size(monkeypatch):
    runner = _FakeRunner(ann_sharpe=3.0)
    result = _run(runner, monkeypatch, _cfg(n_trials=2, survivorship_clean=True))
    assert result.verdict == "REAL"
    assert result.position_size > 0.0


def test_rejected_verdict_has_zero_position_size(monkeypatch):
    runner = _FakeRunner(ann_sharpe=0.333)
    result = _run(runner, monkeypatch, _cfg(n_trials=16, survivorship_clean=True))
    assert result.verdict == "REJECTED"
    assert result.position_size == 0.0
