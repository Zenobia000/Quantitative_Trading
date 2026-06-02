"""RunConfig — the run object. Forces a hypothesis (anti-overfit pre-registration)."""
from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from backtest_platform.research.run_config import RunConfig


def _cfg(**kw):
    base = dict(
        hypothesis="v3 放寬四層進場是否在雙窗有一致正期望",
        preset="v3",
        stocks=("2330", "1101"),
        is_start=date(2020, 1, 1),
        is_end=date(2024, 12, 31),
    )
    base.update(kw)
    return RunConfig(**base)


def test_runconfig_minimal_valid() -> None:
    c = _cfg()
    assert c.preset == "v3"
    assert c.engine == "sim"  # default
    assert c.stocks == ("2330", "1101")


def test_hypothesis_is_required_and_nonempty() -> None:
    with pytest.raises(ValidationError):
        _cfg(hypothesis="")
    with pytest.raises(ValidationError):
        _cfg(hypothesis="   ")


def test_window_must_be_ordered() -> None:
    with pytest.raises(ValidationError, match="is_start"):
        _cfg(is_start=date(2024, 1, 1), is_end=date(2020, 1, 1))


def test_unknown_preset_rejected() -> None:
    with pytest.raises(ValidationError):
        _cfg(preset="bogus")


def test_config_is_frozen() -> None:
    c = _cfg()
    with pytest.raises(ValidationError):
        c.preset = "v2"  # type: ignore[misc]


def test_run_id_is_stable_for_same_inputs() -> None:
    # deterministic id from inputs (no wall-clock) so the same run is identifiable
    assert _cfg().run_id == _cfg().run_id
    assert _cfg(preset="v2").run_id != _cfg(preset="v3").run_id
