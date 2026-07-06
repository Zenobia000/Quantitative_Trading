"""RunConfig — the run object. Forces a hypothesis (anti-overfit pre-registration).

Post-ADR-028: ``preset`` is gone; a run names a registered ``strategy`` plus a
``params`` dict. Strategy-name + params validation happens at dispatch time
(``_run_is_core``), not here — so RunConfig stays decoupled from concrete
strategy types and intentionally does NOT reject unknown strategy names.
"""
from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from quant_platform.packages.domain.run_config import RunConfig


def _cfg(**kw):
    base = dict(
        hypothesis="four_layer 放寬四層進場是否在雙窗有一致正期望",
        strategy="four_layer",
        params={},
        stocks=("2330", "1101"),
        is_start=date(2020, 1, 1),
        is_end=date(2024, 12, 31),
    )
    base.update(kw)
    return RunConfig(**base)


def test_runconfig_minimal_valid() -> None:
    c = _cfg()
    assert c.strategy == "four_layer"
    assert c.params == {}
    assert c.engine == "sim"  # default
    assert c.stocks == ("2330", "1101")


def test_params_carries_strategy_inputs() -> None:
    c = _cfg(params={"lookback_days": 120})
    assert c.params == {"lookback_days": 120}


def test_hypothesis_is_required_and_nonempty() -> None:
    with pytest.raises(ValidationError):
        _cfg(hypothesis="")
    with pytest.raises(ValidationError):
        _cfg(hypothesis="   ")


def test_window_must_be_ordered() -> None:
    with pytest.raises(ValidationError, match="is_start"):
        _cfg(is_start=date(2024, 1, 1), is_end=date(2020, 1, 1))


def test_config_is_frozen() -> None:
    c = _cfg()
    with pytest.raises(ValidationError):
        c.strategy = "momentum"  # type: ignore[misc]


def test_run_id_is_stable_for_same_inputs() -> None:
    # deterministic id from inputs (no wall-clock) so the same run is identifiable
    assert _cfg().run_id == _cfg().run_id


def test_run_id_differs_when_strategy_or_params_differ() -> None:
    assert _cfg(strategy="four_layer").run_id != _cfg(strategy="momentum").run_id
    assert _cfg(params={}).run_id != _cfg(params={"lookback_days": 120}).run_id
