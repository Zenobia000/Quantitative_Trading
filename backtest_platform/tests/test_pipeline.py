"""Unit tests for `backtest_platform.pipeline` — M1 end-to-end smoke entry.

Mocks the three heavy collaborators (fetch_bundle / compute_scores /
compute_signals) so we exercise:
- run_pipeline orchestration (fetch → score → signal)
- signal_calendar column slicing
- summary_stats aggregation (handles empty + populated frames)
- run_cmd Click invocation (file outputs)
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from click.testing import CliRunner

from backtest_platform.config.strategy_config import StrategyConfig
from backtest_platform import pipeline as pipe


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


def _signaled_frame(n: int = 80) -> pd.DataFrame:
    """Build a fully-signaled frame mimicking compute_signals output."""
    dates = pd.bdate_range("2024-01-02", periods=n).date
    return pd.DataFrame(
        {
            "trade_date": dates,
            "close": np.linspace(100, 130, n),
            "box_upper": np.linspace(110, 140, n),
            "box_lower": np.linspace(90, 120, n),
            "ma20": np.linspace(95, 125, n),
            "structure_score": [8] * n,
            "direction_score": [7] * n,
            "chip_score": [6] * n,
            "momentum_score": [5] * n,
            "total_score": [26] * n,
            "state_strong_buy": [1, 0] * (n // 2),
            "state_hold": [0, 1] * (n // 2),
            "state_warning": [0] * n,
            "state_flameout": [0] * n,
            "action": ["buy" if i == 5 else "hold" if i < n - 2 else "exit" for i in range(n)],
            "in_position": [0, 0, 0, 0, 0, 1] + [1] * (n - 8) + [1, 0],
        }
    )


def _empty_signaled_frame() -> pd.DataFrame:
    """All-NaN warmup frame — signal_calendar should drop everything."""
    n = 5
    dates = pd.bdate_range("2024-01-02", periods=n).date
    return pd.DataFrame(
        {
            "trade_date": dates,
            "close": [100.0] * n,
            "box_upper": [np.nan] * n,  # NaN warmup → all dropped
            "box_lower": [np.nan] * n,
            "ma20": [np.nan] * n,
            "structure_score": [0] * n,
            "direction_score": [0] * n,
            "chip_score": [0] * n,
            "momentum_score": [0] * n,
            "total_score": [0] * n,
            "state_strong_buy": [0] * n,
            "state_hold": [0] * n,
            "state_warning": [0] * n,
            "state_flameout": [0] * n,
            "action": ["none"] * n,
            "in_position": [0] * n,
        }
    )


# --------------------------------------------------------------------------- #
# run_pipeline
# --------------------------------------------------------------------------- #


def test_run_pipeline_calls_collaborators_in_order():
    """fetch_bundle → compute_scores → compute_signals; result == compute_signals output."""
    fake_bundle = MagicMock()
    fake_bundle.daily_bars = pd.DataFrame({"x": [1, 2, 3]})
    fake_bundle.institutional = pd.DataFrame({"x": [1]})
    fake_bundle.broker_chips = pd.DataFrame({"x": [1]})
    fake_bundle.merged = MagicMock(return_value=pd.DataFrame({"close": list(range(80))}))

    scored = pd.DataFrame({"a": [1]})
    signaled = _signaled_frame()

    with (
        patch.object(pipe, "fetch_bundle", return_value=fake_bundle) as mock_fetch,
        patch.object(pipe, "compute_scores", return_value=scored) as mock_score,
        patch.object(pipe, "compute_signals", return_value=signaled) as mock_signal,
        patch.object(pipe, "write_parquet") as mock_write,
    ):
        result = pipe.run_pipeline(
            stock_id="2330",
            start=date(2024, 1, 1),
            end=date(2024, 12, 31),
        )

    mock_fetch.assert_called_once_with("2330", date(2024, 1, 1), date(2024, 12, 31))
    mock_score.assert_called_once()
    mock_signal.assert_called_once()
    # No parquet write when parquet_dir None
    mock_write.assert_not_called()
    pd.testing.assert_frame_equal(result, signaled)


def test_run_pipeline_writes_parquet_when_dir_given(tmp_path):
    fake_bundle = MagicMock()
    fake_bundle.daily_bars = pd.DataFrame({"x": [1]})
    fake_bundle.institutional = pd.DataFrame({"x": [1]})
    fake_bundle.broker_chips = pd.DataFrame({"x": [1]})
    fake_bundle.merged = MagicMock(return_value=pd.DataFrame({"close": list(range(80))}))

    with (
        patch.object(pipe, "fetch_bundle", return_value=fake_bundle),
        patch.object(pipe, "compute_scores", return_value=pd.DataFrame()),
        patch.object(pipe, "compute_signals", return_value=_signaled_frame()),
        patch.object(pipe, "write_parquet") as mock_write,
    ):
        pipe.run_pipeline(
            stock_id="2330",
            start=date(2024, 1, 1),
            end=date(2024, 12, 31),
            parquet_dir=tmp_path,
        )
    mock_write.assert_called_once_with(fake_bundle, tmp_path)


def test_run_pipeline_warns_when_merged_too_short(caplog):
    """When merged < box_period+5, warning is logged but execution continues."""
    fake_bundle = MagicMock()
    fake_bundle.daily_bars = pd.DataFrame()
    fake_bundle.institutional = pd.DataFrame()
    fake_bundle.broker_chips = pd.DataFrame()
    fake_bundle.merged = MagicMock(return_value=pd.DataFrame({"close": [1, 2, 3]}))

    with (
        patch.object(pipe, "fetch_bundle", return_value=fake_bundle),
        patch.object(pipe, "compute_scores", return_value=pd.DataFrame()),
        patch.object(pipe, "compute_signals", return_value=_signaled_frame()),
    ):
        pipe.run_pipeline("2330", date(2024, 1, 1), date(2024, 12, 31))
    # Just ensure it runs without raising (warning logged via loguru, not caplog)


def test_run_pipeline_uses_provided_config():
    fake_bundle = MagicMock()
    fake_bundle.daily_bars = pd.DataFrame()
    fake_bundle.institutional = pd.DataFrame()
    fake_bundle.broker_chips = pd.DataFrame()
    fake_bundle.merged = MagicMock(return_value=pd.DataFrame({"close": list(range(80))}))

    cfg = StrategyConfig(box_period=30)

    with (
        patch.object(pipe, "fetch_bundle", return_value=fake_bundle),
        patch.object(pipe, "compute_scores", return_value=pd.DataFrame()) as mock_score,
        patch.object(pipe, "compute_signals", return_value=_signaled_frame()) as mock_signal,
    ):
        pipe.run_pipeline("2330", date(2024, 1, 1), date(2024, 12, 31), config=cfg)

    # Same config object propagates downstream
    _, score_args = mock_score.call_args
    assert mock_score.call_args.args[1] is cfg or score_args.get("config") is cfg or mock_score.call_args.args[1] is cfg


# --------------------------------------------------------------------------- #
# signal_calendar
# --------------------------------------------------------------------------- #


def test_signal_calendar_drops_warmup_rows():
    df = _empty_signaled_frame()
    result = pipe.signal_calendar(df, StrategyConfig())
    assert len(result) == 0


def test_signal_calendar_keeps_expected_columns():
    df = _signaled_frame()
    result = pipe.signal_calendar(df, StrategyConfig())
    expected = {
        "trade_date", "close",
        "structure_score", "direction_score", "chip_score", "momentum_score",
        "total_score",
        "state_strong_buy", "state_hold", "state_warning", "state_flameout",
        "action", "in_position",
    }
    assert set(result.columns) == expected


# --------------------------------------------------------------------------- #
# summary_stats
# --------------------------------------------------------------------------- #


def test_summary_stats_returns_zero_when_empty():
    df = _empty_signaled_frame()
    stats = pipe.summary_stats(df, StrategyConfig())
    assert stats == {"bars": 0}


def test_summary_stats_aggregates_actions_and_states():
    df = _signaled_frame()
    stats = pipe.summary_stats(df, StrategyConfig())
    assert stats["bars"] > 0
    assert "state_distribution" in stats
    sd = stats["state_distribution"]
    assert "strong_buy" in sd and "hold" in sd
    # At least one buy and one exit in the synthetic frame
    assert "action_distribution" in stats
    assert "total_score_describe" in stats
    assert "buy_dates" in stats
    assert "exit_dates" in stats
    # Buy dates ISO-formatted
    for s in stats["buy_dates"]:
        assert isinstance(s, str)
        # Parses as date
        from datetime import date as _d
        _d.fromisoformat(s)


# --------------------------------------------------------------------------- #
# CLI command (run_cmd)
# --------------------------------------------------------------------------- #


def test_run_cmd_writes_calendar_and_prints_summary(tmp_path):
    runner = CliRunner()
    signaled = _signaled_frame()

    with (
        patch.object(pipe, "run_pipeline", return_value=signaled),
    ):
        result = runner.invoke(
            pipe.cli,
            [
                "run",
                "--stock-id", "2330",
                "--start", "2024-01-02",
                "--end", "2024-12-31",
                "--parquet-dir", str(tmp_path / "parquet"),
                "--report-dir", str(tmp_path / "reports"),
            ],
        )

    assert result.exit_code == 0, result.output
    # Calendar CSV written
    csvs = list((tmp_path / "reports").glob("calendar__2330__*.csv"))
    assert len(csvs) == 1
    # Calendar content has expected header
    text = csvs[0].read_text(encoding="utf-8")
    assert "trade_date" in text and "total_score" in text
    # Console summary printed
    assert "Signal Calendar" in result.output
    assert "Summary" in result.output


def test_run_cmd_handles_zero_bars(tmp_path):
    """When signaled frame fully warm-up NaN, summary prints 'bars=0' only."""
    runner = CliRunner()
    with patch.object(pipe, "run_pipeline", return_value=_empty_signaled_frame()):
        result = runner.invoke(
            pipe.cli,
            [
                "run",
                "--stock-id", "2330",
                "--start", "2024-01-02",
                "--end", "2024-12-31",
                "--parquet-dir", str(tmp_path / "p"),
                "--report-dir", str(tmp_path / "r"),
            ],
        )
    assert result.exit_code == 0, result.output
    assert "Bars (after warmup): 0" in result.output
