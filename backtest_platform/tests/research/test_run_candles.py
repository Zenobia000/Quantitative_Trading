"""``research.run_candles`` — OHLC candles + entry/exit markers (Trade Review K-line).

Pure transforms are tested without the parquet cache; ``build_candles`` is tested
against a real temp parquet so the cache-miss → ``None`` (typed-empty) path is
exercised end to end.
"""
from __future__ import annotations

import pandas as pd
import pytest

from backtest_platform.research import run_candles


def _bars(dates: list[str]) -> pd.DataFrame:
    """A minimal daily_bars frame with a distinct close per day."""
    return pd.DataFrame(
        {
            "stock_id": ["2330"] * len(dates),
            "trade_date": pd.to_datetime(dates),
            "open": [10.0 + i for i in range(len(dates))],
            "high": [11.0 + i for i in range(len(dates))],
            "low": [9.0 + i for i in range(len(dates))],
            "close": [10.5 + i for i in range(len(dates))],
            "volume": [1000 + i for i in range(len(dates))],
        }
    )


# --- bars_to_candles (pure) ------------------------------------------------
def test_bars_to_candles_shape_and_order():
    out = run_candles.bars_to_candles(_bars(["2020-01-03", "2020-01-02", "2020-01-01"]))
    assert [c["time"] for c in out] == ["2020-01-01", "2020-01-02", "2020-01-03"]
    first = out[0]
    assert set(first) == {"time", "open", "high", "low", "close", "volume"}
    assert isinstance(first["open"], float) and isinstance(first["volume"], int)


def test_bars_to_candles_empty_is_empty_list():
    assert run_candles.bars_to_candles(None) == []
    assert run_candles.bars_to_candles(_bars([]).iloc[0:0]) == []


# --- sig_to_markers (pure) -------------------------------------------------
def _sig(rows: list[tuple[str, str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.to_datetime([r[0] for r in rows]),
            "action": [r[1] for r in rows],
            "close": [r[2] for r in rows],
        }
    )


def test_sig_to_markers_pairs_entry_exit():
    sig = _sig(
        [
            ("2020-01-01", "buy", 100.0),
            ("2020-01-02", "hold", 105.0),
            ("2020-01-03", "exit", 110.0),
        ]
    )
    markers = run_candles.sig_to_markers(sig)
    assert [m["kind"] for m in markers] == ["entry", "exit"]
    assert markers[0]["time"] == "2020-01-01" and markers[0]["price"] == 100.0
    assert markers[1]["time"] == "2020-01-03"
    assert markers[1]["ret"] == pytest.approx(0.10)


def test_sig_to_markers_stoploss_closes_a_round_trip():
    sig = _sig([("2020-01-01", "buy", 100.0), ("2020-01-02", "stoploss", 90.0)])
    markers = run_candles.sig_to_markers(sig)
    assert markers[1]["kind"] == "exit"
    assert markers[1]["ret"] == pytest.approx(-0.10)


def test_sig_to_markers_dangling_open_position_emits_nothing():
    sig = _sig([("2020-01-01", "buy", 100.0), ("2020-01-02", "hold", 105.0)])
    assert run_candles.sig_to_markers(sig) == []


def test_sig_to_markers_empty_or_no_action_col():
    assert run_candles.sig_to_markers(None) == []
    assert run_candles.sig_to_markers(pd.DataFrame({"close": [1.0]})) == []


# --- derive_markers dispatch ----------------------------------------------
def test_derive_markers_skips_non_four_layer():
    record = {"strategy": "momentum", "params": {}}
    assert run_candles.derive_markers(record, "2330", None, None) == []


_FLOW_COLS = (
    "foreign_buy", "trust_buy", "dealer_buy", "top_broker_buy", "key_broker_buy",
    "gov_broker_buy", "geo_broker_buy", "day_trade_volume", "margin_offset_volume",
)


def test_derive_markers_four_layer_uses_loader():
    # A tiny synthetic loader returning a merged frame (daily bars + zeroed flow
    # columns, exactly what load_merged_parquet yields on no institutional/broker
    # data); derive_markers must run the four-layer signal pipeline over it —
    # real signals, injected data, no parquet.
    dates = pd.bdate_range("2019-06-01", periods=200)
    merged = pd.DataFrame(
        {
            "stock_id": ["2330"] * len(dates),
            "trade_date": dates,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 1000,
            **{c: 0 for c in _FLOW_COLS},
        }
    )
    out = run_candles.derive_markers(
        {"strategy": "four_layer", "params": {}},
        "2330",
        None,
        None,
        loader=lambda _sid: merged,
    )
    assert isinstance(out, list)  # flat price → no signals; still a valid (empty) list


# --- build_candles orchestration ------------------------------------------
def test_build_candles_missing_parquet_returns_none(tmp_path):
    record = {"strategy": "four_layer", "stocks": ["2330"], "params": {}}
    assert run_candles.build_candles(record, "2330", parquet_dir=tmp_path) is None


def test_build_candles_reads_parquet_and_slices_window(tmp_path):
    _bars(["2019-12-31", "2020-01-01", "2020-06-30", "2021-01-01"]).to_parquet(
        tmp_path / "daily_bars__2330.parquet"
    )
    record = {
        "strategy": "momentum",  # skip marker derivation → candles only
        "stocks": ["2330"],
        "window": ["2020-01-01", "2020-12-31"],
        "params": {},
    }
    payload = run_candles.build_candles(record, "2330", parquet_dir=tmp_path)
    assert payload is not None
    times = [c["time"] for c in payload["candles"]]
    assert times == ["2020-01-01", "2020-06-30"]  # 2019/2021 sliced out
    assert payload["markers"] == []


def test_build_candles_marker_failure_degrades_to_candles_only(tmp_path):
    _bars(["2020-01-01", "2020-01-02"]).to_parquet(tmp_path / "daily_bars__2330.parquet")
    # four_layer + a params dict that will blow up StrategyConfig(**params) → markers
    # must degrade to [] while the candles still render.
    record = {
        "strategy": "four_layer",
        "stocks": ["2330"],
        "window": ["2020-01-01", "2020-12-31"],
        "params": {"box_period": -999},  # invalid → StrategyConfig raises
    }
    payload = run_candles.build_candles(record, "2330", parquet_dir=tmp_path)
    assert payload is not None
    assert len(payload["candles"]) == 2
    assert payload["markers"] == []
