"""Tests for `finmind_bundle.py` — universe resolution + frame normalization."""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from backtest_platform.data.schemas import ETLBundle
from backtest_platform.engines.zipline_adapter.bundles.finmind_bundle import (
    DEFAULT_UNIVERSE,
    _build_asset_metadata,
    _iter_daily_bars,
    _resolve_cache_dir,
    _resolve_universe,
    _to_zipline_daily_frame,
)


class FakeCalendar:
    """Minimal stub for `_to_zipline_daily_frame` — exposes `sessions_in_range()`."""

    def __init__(self, sessions: list[pd.Timestamp]):
        self._sessions = pd.DatetimeIndex(sessions)

    def sessions_in_range(self, start, end):
        # zipline calendars return tz-aware; mimic that
        mask = (self._sessions >= start) & (self._sessions <= end)
        return self._sessions[mask]


def _make_daily_bars(dates: list[date], volumes: list[int]) -> pd.DataFrame:
    """Synthetic OHLCV — open/high/low/close = 100.0 for simplicity."""
    return pd.DataFrame(
        {
            "stock_id": ["2330"] * len(dates),
            "trade_date": dates,
            "open": [100.0] * len(dates),
            "high": [101.0] * len(dates),
            "low": [99.0] * len(dates),
            "close": [100.5] * len(dates),
            "volume": volumes,
            "adj_factor": [1.0] * len(dates),
        }
    )


def _make_empty_etl_bundle() -> ETLBundle:
    """Empty bundle for edge-case tests."""
    return ETLBundle(
        stock_id="2330",
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 3),
        daily_bars=_make_daily_bars([date(2024, 1, 2)], [1000]).iloc[0:0],
        institutional=pd.DataFrame(),
        broker_chips=pd.DataFrame(),
    )


# ===== _resolve_universe =====


def test_resolve_universe_default_when_no_env():
    assert _resolve_universe({}) == list(DEFAULT_UNIVERSE)


def test_resolve_universe_env_var_overrides_default():
    universe = _resolve_universe({"UNIVERSE_FINMIND": "2330,2454,2317"})
    assert universe == ["2330", "2454", "2317"]


def test_resolve_universe_env_var_handles_whitespace():
    universe = _resolve_universe({"UNIVERSE_FINMIND": " 2330 , 2454 ,  ,2317 "})
    assert universe == ["2330", "2454", "2317"]


def test_resolve_universe_file_path(tmp_path):
    f = tmp_path / "universe.txt"
    f.write_text("2330\n2454\n# 註解\n  \n2317\n", encoding="utf-8")
    universe = _resolve_universe({"UNIVERSE_FILE": str(f)})
    # Implementation does not strip comments; current behavior keeps them
    assert "2330" in universe
    assert "2454" in universe
    assert "2317" in universe


# ===== _resolve_cache_dir =====


def test_resolve_cache_dir_default():
    from backtest_platform.engines.zipline_adapter.bundles.finmind_bundle import (
        DEFAULT_CACHE_DIR,
    )

    assert _resolve_cache_dir({}) == DEFAULT_CACHE_DIR


def test_resolve_cache_dir_env_override(tmp_path):
    assert _resolve_cache_dir({"FINMIND_PARQUET_CACHE": str(tmp_path)}) == tmp_path


# ===== _to_zipline_daily_frame — the critical missing-session fill logic =====


def test_to_zipline_daily_frame_empty_input_returns_empty():
    cal = FakeCalendar([])
    result = _to_zipline_daily_frame(_make_empty_etl_bundle(), cal)
    assert result.empty
    assert list(result.columns) == ["open", "high", "low", "close", "volume"]


def test_to_zipline_daily_frame_fills_missing_session_with_ffill():
    """The core fix for plan v3.0: FinMind 偶有缺失 sessions（停止交易日等），
    zipline 要求每 session 都有 row → ffill OHLC + volume=0。"""
    # FinMind 給 3 個 sessions but XTAI calendar 認為 4 個 sessions in range
    df = _make_daily_bars(
        [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 5)],  # missing 1/4
        [1000, 1200, 1500],
    )
    bundle = ETLBundle(
        stock_id="2330",
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 5),
        daily_bars=df,
        institutional=pd.DataFrame(),
        broker_chips=pd.DataFrame(),
    )
    # Calendar has all 4 sessions
    cal = FakeCalendar(
        [
            pd.Timestamp("2024-01-02"),
            pd.Timestamp("2024-01-03"),
            pd.Timestamp("2024-01-04"),  # the missing one
            pd.Timestamp("2024-01-05"),
        ]
    )

    result = _to_zipline_daily_frame(bundle, cal)

    assert len(result) == 4, "result must cover all 4 sessions"
    assert result.loc[pd.Timestamp("2024-01-04"), "close"] == 100.5, "ffill from 1/3"
    assert result.loc[pd.Timestamp("2024-01-04"), "volume"] == 0, "no trading → volume=0"
    assert result.loc[pd.Timestamp("2024-01-05"), "volume"] == 1500


def test_to_zipline_daily_frame_drops_non_session_dates():
    """FinMind 偶見資料溢出 XTAI calendar（如資料登錄錯誤的週末）→ drop。"""
    df = _make_daily_bars(
        [date(2024, 1, 2), date(2024, 1, 6)],  # 1/6 is Saturday — not a session
        [1000, 999],
    )
    bundle = ETLBundle(
        stock_id="2330",
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 6),
        daily_bars=df,
        institutional=pd.DataFrame(),
        broker_chips=pd.DataFrame(),
    )
    cal = FakeCalendar([pd.Timestamp("2024-01-02")])  # only 1/2 is a session

    result = _to_zipline_daily_frame(bundle, cal)
    assert len(result) == 1
    assert pd.Timestamp("2024-01-06") not in result.index


def test_to_zipline_daily_frame_volume_is_int64():
    df = _make_daily_bars([date(2024, 1, 2)], [1234])
    bundle = ETLBundle(
        stock_id="2330",
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 2),
        daily_bars=df,
        institutional=pd.DataFrame(),
        broker_chips=pd.DataFrame(),
    )
    cal = FakeCalendar([pd.Timestamp("2024-01-02")])
    result = _to_zipline_daily_frame(bundle, cal)
    # zipline-reloaded daily writer requires int volume
    assert result["volume"].dtype == "int64"


# ===== _build_asset_metadata =====


def test_build_asset_metadata_required_columns():
    """zipline-reloaded asset_db_writer expects these columns."""
    df = _make_daily_bars([date(2024, 1, 2)], [1000])
    bundle = ETLBundle(
        stock_id="2330",
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 2),
        daily_bars=df,
        institutional=pd.DataFrame(),
        broker_chips=pd.DataFrame(),
    )
    sid_map = {"2330": 0}
    metadata = _build_asset_metadata(sid_map, {"2330": bundle})

    expected_cols = {
        "symbol",
        "asset_name",
        "start_date",
        "end_date",
        "first_traded",
        "auto_close_date",
        "exchange",
    }
    assert expected_cols.issubset(set(metadata.columns))
    assert metadata.loc[0, "symbol"] == "2330"
    assert metadata.loc[0, "exchange"] == "XTAI"
    # auto_close_date should be 1 day after end_date
    assert metadata.loc[0, "auto_close_date"] == pd.Timestamp("2024-01-03")


def test_build_asset_metadata_multiple_symbols():
    bundles = {
        sym: ETLBundle(
            stock_id=sym,
            start_date=date(2024, 1, 2),
            end_date=date(2024, 6, 30),
            daily_bars=_make_daily_bars([date(2024, 1, 2)], [1000]),
            institutional=pd.DataFrame(),
            broker_chips=pd.DataFrame(),
        )
        for sym in ("2330", "2454", "2317")
    }
    sid_map = {sym: idx for idx, sym in enumerate(bundles)}
    metadata = _build_asset_metadata(sid_map, bundles)
    assert len(metadata) == 3
    assert set(metadata["symbol"]) == {"2330", "2454", "2317"}


# ===== _iter_daily_bars =====


def test_iter_daily_bars_yields_pairs():
    frames = {
        "2330": pd.DataFrame(
            {"open": [100.0]},
            index=pd.DatetimeIndex([pd.Timestamp("2024-01-02")]),
        ),
        "2454": pd.DataFrame(
            {"open": [200.0]},
            index=pd.DatetimeIndex([pd.Timestamp("2024-01-02")]),
        ),
    }
    sid_map = {"2330": 0, "2454": 1}
    pairs = list(_iter_daily_bars(sid_map, frames))
    assert len(pairs) == 2
    assert pairs[0][0] == 0
    assert pairs[1][0] == 1


def test_iter_daily_bars_skips_empty_frames():
    frames = {
        "2330": pd.DataFrame(),  # empty
        "2454": pd.DataFrame(
            {"open": [200.0]},
            index=pd.DatetimeIndex([pd.Timestamp("2024-01-02")]),
        ),
    }
    sid_map = {"2330": 0, "2454": 1}
    pairs = list(_iter_daily_bars(sid_map, frames))
    assert len(pairs) == 1
    assert pairs[0][0] == 1  # only 2454 yielded
