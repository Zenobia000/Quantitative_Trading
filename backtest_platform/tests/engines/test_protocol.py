"""Engine Protocol (5.C.1) — abstract backtest interface + SimEngine.

Tests use a synthetic injected loader (NOT cache-gated; no parquet required).
The point of this layer: upper code asks ``get_engine(name).run(...)`` and gets a
metrics dict, without binding to sim/zipline/vectorbt internals.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from backtest_platform.strategies.four_layer_resonance.config import StrategyConfig
from backtest_platform.engines.protocol import (
    Engine,
    EngineName,
    SimEngine,
    get_engine,
)


def _synthetic_loader(sid: str) -> pd.DataFrame:
    """A rising-trend frame with positive flows → produces entries (mirrors the
    is_harness test fixture so SimEngine output is comparable)."""
    n = 260
    dates = pd.date_range("2019-05-01", periods=n, freq="D")
    close = np.linspace(50, 135, n) + np.sin(np.arange(n) / 4.0) * 1.5
    return pd.DataFrame({
        "trade_date": dates, "stock_id": sid,
        "open": close - 0.3, "high": close * 1.03, "low": close * 0.97,
        "close": close, "volume": 5000,
        "foreign_buy": 120, "trust_buy": 60, "dealer_buy": 10,
        "top_broker_buy": 90, "key_broker_buy": 50, "gov_broker_buy": 5, "geo_broker_buy": 5,
        "day_trade_volume": 500, "margin_offset_volume": 100,
    })


_STOCKS = ["AAA", "BBB"]
_START = date(2019, 11, 1)
_END = date(2020, 1, 14)
#: Default four-layer config — replaces the removed ``get_preset("v3")`` (ADR-028).
_CONFIG = StrategyConfig()


# --- Protocol conformance -------------------------------------------------

def test_simengine_satisfies_engine_protocol() -> None:
    eng = SimEngine(loader=_synthetic_loader)
    # runtime_checkable Protocol: structural isinstance check
    assert isinstance(eng, Engine)


def test_engine_is_runtime_checkable_and_rejects_non_conformers() -> None:
    class NotAnEngine:
        pass

    assert not isinstance(NotAnEngine(), Engine)


# --- SimEngine.run → metrics dict ----------------------------------------

def test_simengine_run_returns_metrics_dict() -> None:
    eng = SimEngine(loader=_synthetic_loader)
    m = eng.run(_STOCKS, _START, _END, _CONFIG)
    assert isinstance(m, dict)
    for k in ("cagr", "sharpe", "slippage_sharpe", "struct1_pct", "churn_pct",
              "avg_hold", "trades", "maxdd", "bars"):
        assert k in m, f"missing metric {k}"
    assert m["bars"] > 0


def test_simengine_run_accepts_arbitrary_strategy_config() -> None:
    # not a named preset — proves run() takes a StrategyConfig, not a preset name
    custom = StrategyConfig(entry_min_layers=3, entry_min_structure=2,
                            entry_first_cross_only=False, entry_confirm_days=2)
    eng = SimEngine(loader=_synthetic_loader)
    m = eng.run(_STOCKS, _START, _END, custom)
    assert isinstance(m, dict)
    assert m["bars"] > 0


def test_simengine_empty_when_window_has_no_data() -> None:
    eng = SimEngine(loader=_synthetic_loader)
    m = eng.run(_STOCKS, date(2010, 1, 1), date(2010, 6, 1), _CONFIG)
    assert m["trades"] == 0


def test_simengine_default_loader_is_load_merged_parquet() -> None:
    from backtest_platform.research.is_harness import load_merged_parquet

    assert SimEngine().loader is load_merged_parquet


# --- get_engine resolution ------------------------------------------------

def test_get_engine_sim_returns_simengine() -> None:
    eng = get_engine("sim")
    assert isinstance(eng, SimEngine)
    assert isinstance(eng, Engine)


def test_get_engine_passes_loader_to_simengine() -> None:
    eng = get_engine("sim", loader=_synthetic_loader)
    assert isinstance(eng, SimEngine)
    assert eng.loader is _synthetic_loader


def test_get_engine_unknown_name_raises_valueerror() -> None:
    with pytest.raises(ValueError, match="unknown engine"):
        get_engine("nope")  # type: ignore[arg-type]


@pytest.mark.parametrize("name", ["zipline", "vectorbt"])
def test_get_engine_stub_engines_are_engine_but_run_raises(name: EngineName) -> None:
    eng = get_engine(name)
    assert isinstance(eng, Engine)
    with pytest.raises(NotImplementedError):
        eng.run(_STOCKS, _START, _END, _CONFIG)


def test_engine_name_literal_values() -> None:
    import typing

    assert set(typing.get_args(EngineName)) == {"sim", "zipline", "vectorbt"}
