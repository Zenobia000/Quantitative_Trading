"""Unit tests for zipline_adapter/cli.py — programmatic backtest entry.

Mocks `zipline.run_algorithm` (heavyweight) and exercises:
- _ensure_bundle_registered() — side-effect import of finmind_bundle
- _resolve_zipline_root() — explicit > env > project-local
- _format_perf_summary() — DataFrame → dict aggregation
- _maybe_write_tearsheet() — graceful degrade when quantstats missing
- _maybe_notify_discord() — no-op when DISCORD_BOT_TOKEN absent
- backtest_run / list_bundles Click CLI commands
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from click.testing import CliRunner

from backtest_platform.engines.zipline_adapter import cli as cli_mod


# --------------------------------------------------------------------------- #
# _ensure_bundle_registered
# --------------------------------------------------------------------------- #


def test_ensure_bundle_registered_imports_finmind_bundle():
    """Should import without raising; module-level register() runs as side-effect."""
    # Just make sure the call doesn't blow up; idempotent re-import is fine.
    cli_mod._ensure_bundle_registered()


# --------------------------------------------------------------------------- #
# _resolve_zipline_root
# --------------------------------------------------------------------------- #


def test_resolve_zipline_root_explicit_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("ZIPLINE_ROOT", str(tmp_path / "env_root"))
    explicit = tmp_path / "explicit"
    explicit.mkdir()
    assert cli_mod._resolve_zipline_root(explicit) == explicit.resolve()


def test_resolve_zipline_root_env_when_no_explicit(tmp_path, monkeypatch):
    env_root = tmp_path / "env_root"
    monkeypatch.setenv("ZIPLINE_ROOT", str(env_root))
    assert cli_mod._resolve_zipline_root(None) == env_root.resolve()


def test_resolve_zipline_root_default_when_no_explicit_no_env(tmp_path, monkeypatch):
    monkeypatch.delenv("ZIPLINE_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)
    result = cli_mod._resolve_zipline_root(None)
    # Default: <cwd>/data/zipline
    assert result == (tmp_path / "data" / "zipline").resolve()


# --------------------------------------------------------------------------- #
# _format_perf_summary
# --------------------------------------------------------------------------- #


def test_format_perf_summary_empty_returns_defaults():
    summary = cli_mod._format_perf_summary(pd.DataFrame(), capital_base=1_000_000)
    assert summary == {"bars": 0, "final_value": 1_000_000, "total_return": 0.0}


def test_format_perf_summary_single_bar_omits_sharpe():
    """Sharpe / std needs ≥ 2 bars."""
    idx = pd.DatetimeIndex([pd.Timestamp("2024-01-02")])
    perf = pd.DataFrame(
        {"portfolio_value": [1_010_000], "returns": [0.01]},
        index=idx,
    )
    summary = cli_mod._format_perf_summary(perf, capital_base=1_000_000)
    assert summary["bars"] == 1
    assert summary["final_value"] == 1_010_000
    assert summary["total_return"] == pytest.approx(0.01)
    assert "sharpe_naive" not in summary


def test_format_perf_summary_counts_trades_from_transactions():
    """Trade counts come from actual fills, NOT the ffill-corrupted action_* cols.

    Regression guard: zipline `record()` forward-fills action columns on days
    without that action, so summing them inflates counts (a single early buy
    read as ~1000 buys). The summary must count transactions instead.
    """
    idx = pd.bdate_range("2024-01-02", periods=3)
    perf = pd.DataFrame(
        {
            "portfolio_value": [1_000_000, 1_010_000, 1_020_000],
            "returns": [0.0, 0.01, 0.0099],
            "n_evaluated": [1, 2, 1],
            # ffilled action col present but MUST be ignored for counting
            "action_buy": [1, 1, 1],
            "transactions": [
                [{"amount": 1000, "price": 100.0}],   # buy
                [],
                [{"amount": -1000, "price": 110.0}],  # sell
            ],
        },
        index=idx,
    )
    summary = cli_mod._format_perf_summary(perf, capital_base=1_000_000)
    assert summary["bars"] == 3
    assert summary["n_evaluated_total"] == 4
    assert summary["n_buys"] == 1
    assert summary["n_sells"] == 1
    assert summary["n_round_trips"] == 1
    assert "action_totals" not in summary  # removed — was ffill-corrupted
    assert "sharpe_naive" in summary  # ≥ 2 bars with std > 0
    assert summary["mean_daily_return"] > 0


def test_format_perf_summary_zero_std_omits_sharpe():
    """Sharpe denominator zero → not computed."""
    idx = pd.bdate_range("2024-01-02", periods=3)
    perf = pd.DataFrame(
        {"portfolio_value": [1_000_000, 1_000_000, 1_000_000], "returns": [0.0, 0.0, 0.0]},
        index=idx,
    )
    summary = cli_mod._format_perf_summary(perf, capital_base=1_000_000)
    assert summary["std_daily_return"] == 0
    assert "sharpe_naive" not in summary


# --------------------------------------------------------------------------- #
# _maybe_write_tearsheet
# --------------------------------------------------------------------------- #


def test_maybe_write_tearsheet_returns_none_when_too_few_bars(tmp_path):
    perf = pd.DataFrame({"returns": [0.0]}, index=pd.DatetimeIndex([pd.Timestamp("2024-01-02")]))
    assert cli_mod._maybe_write_tearsheet(perf, tmp_path, "run1") is None


def test_maybe_write_tearsheet_returns_none_when_quantstats_missing(tmp_path, monkeypatch):
    """Graceful degrade if quantstats not installed (validation extra)."""
    idx = pd.bdate_range("2024-01-02", periods=5)
    perf = pd.DataFrame({"returns": [0.01] * 5}, index=idx)

    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "quantstats":
            raise ImportError("quantstats stub")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert cli_mod._maybe_write_tearsheet(perf, tmp_path, "run1") is None


def test_maybe_write_tearsheet_invokes_quantstats(tmp_path):
    idx = pd.bdate_range("2024-01-02", periods=5)
    perf = pd.DataFrame({"returns": [0.01, -0.005, 0.002, 0.003, 0.001]}, index=idx)

    fake_qs = MagicMock()
    fake_qs.reports = MagicMock()
    fake_qs.reports.html = MagicMock()
    with patch.dict("sys.modules", {"quantstats": fake_qs}):
        result = cli_mod._maybe_write_tearsheet(perf, tmp_path, "run123")

    assert result == tmp_path / "tearsheet__run123.html"
    fake_qs.reports.html.assert_called_once()
    # Output dir was created
    assert tmp_path.exists()


# --------------------------------------------------------------------------- #
# _maybe_notify_discord
# --------------------------------------------------------------------------- #


def test_maybe_notify_discord_noop_without_token(monkeypatch):
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
    # Should return without error even with no notifier
    cli_mod._maybe_notify_discord(summary={"start": "x"}, run_id="r1")


def test_maybe_notify_discord_sends_when_token_set(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("DISCORD_CHANNEL_ID", "1234567890")

    summary = {
        "start": "2024-01-02",
        "end": "2024-02-29",
        "bars": 40,
        "total_return": 0.05,
        "final_value": 1_050_000,
        "n_buys": 3,
        "n_sells": 3,
        "n_round_trips": 3,
    }
    mock_notifier = MagicMock()
    mock_notifier_cls = MagicMock(return_value=mock_notifier)

    with patch(
        "backtest_platform.monitoring.discord_notifier.DiscordNotifier",
        mock_notifier_cls,
    ):
        cli_mod._maybe_notify_discord(summary, run_id="r1")

    mock_notifier.send.assert_called_once()
    sent_kwargs = mock_notifier.send.call_args.kwargs
    assert "Backtest finished" in sent_kwargs["content"]
    assert "5.0000%" in sent_kwargs["content"]


def test_maybe_notify_discord_swallows_send_exception(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "fake")
    summary = {
        "start": "x", "end": "y", "bars": 1,
        "total_return": 0.0, "final_value": 0,
        "n_buys": 0, "n_sells": 0, "n_round_trips": 0,
    }
    mock_notifier = MagicMock()
    mock_notifier.send.side_effect = RuntimeError("network down")
    with patch(
        "backtest_platform.monitoring.discord_notifier.DiscordNotifier",
        return_value=mock_notifier,
    ):
        # Must not raise
        cli_mod._maybe_notify_discord(summary, run_id="r1")


# --------------------------------------------------------------------------- #
# CLI commands (Click runner)
# --------------------------------------------------------------------------- #


def _fake_perf() -> pd.DataFrame:
    idx = pd.bdate_range("2024-01-02", periods=10)
    return pd.DataFrame(
        {
            "portfolio_value": [1_000_000 + i * 1000 for i in range(10)],
            "returns": [0.001] * 10,
            "n_evaluated": [1] * 10,
            "action_buy": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            "action_hold": [0, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        },
        index=idx,
    )


def test_backtest_run_persists_summary_and_perf(tmp_path, monkeypatch):
    runner = CliRunner()

    fake_perf = _fake_perf()
    fake_run = MagicMock(return_value=fake_perf)

    # Patch run_algorithm at import site (cli does `from zipline import run_algorithm`)
    fake_zipline = MagicMock()
    fake_zipline.run_algorithm = fake_run

    with (
        patch.dict("sys.modules", {"zipline": fake_zipline}),
        patch.object(cli_mod, "_ensure_bundle_registered"),
    ):
        result = runner.invoke(
            cli_mod.cli,
            [
                "backtest-run",
                "--stocks", "2330",
                "--start", "2024-01-02",
                "--end", "2024-01-15",
                "--capital-base", "1000000",
                "--zipline-root", str(tmp_path / "zr"),
                "--output-dir", str(tmp_path / "out"),
            ],
        )

    assert result.exit_code == 0, result.output
    # run_algorithm called
    fake_run.assert_called_once()
    # Files persisted
    out_dir = tmp_path / "out"
    summaries = list(out_dir.glob("summary__*.json"))
    perfs = list(out_dir.glob("perf__*.pkl"))
    assert len(summaries) == 1
    assert len(perfs) == 1
    summary = json.loads(summaries[0].read_text(encoding="utf-8"))
    assert summary["bars"] == 10
    assert "Backtest Summary" in result.output


def test_backtest_run_sets_env_vars(tmp_path, monkeypatch):
    """UNIVERSE_FINMIND and ZIPLINE_ROOT must be set BEFORE zipline import."""
    runner = CliRunner()
    fake_perf = _fake_perf()
    fake_zipline = MagicMock(run_algorithm=MagicMock(return_value=fake_perf))

    captured = {}

    def capture_run(*args, **kwargs):
        captured["UNIVERSE_FINMIND"] = os.environ.get("UNIVERSE_FINMIND")
        captured["ZIPLINE_ROOT"] = os.environ.get("ZIPLINE_ROOT")
        return fake_perf

    fake_zipline.run_algorithm = capture_run

    with (
        patch.dict("sys.modules", {"zipline": fake_zipline}),
        patch.object(cli_mod, "_ensure_bundle_registered"),
    ):
        result = runner.invoke(
            cli_mod.cli,
            [
                "backtest-run",
                "--stocks", "2330,2454",
                "--start", "2024-01-02",
                "--end", "2024-01-15",
                "--zipline-root", str(tmp_path / "zr"),
                "--output-dir", str(tmp_path / "out"),
            ],
        )

    assert result.exit_code == 0, result.output
    assert captured["UNIVERSE_FINMIND"] == "2330,2454"
    assert captured["ZIPLINE_ROOT"] == str((tmp_path / "zr").resolve())


def test_backtest_run_with_tearsheet_flag(tmp_path):
    runner = CliRunner()
    fake_perf = _fake_perf()
    fake_zipline = MagicMock(run_algorithm=MagicMock(return_value=fake_perf))

    fake_qs = MagicMock()
    fake_qs.reports = MagicMock()

    with (
        patch.dict("sys.modules", {"zipline": fake_zipline, "quantstats": fake_qs}),
        patch.object(cli_mod, "_ensure_bundle_registered"),
    ):
        result = runner.invoke(
            cli_mod.cli,
            [
                "backtest-run",
                "--stocks", "2330",
                "--start", "2024-01-02",
                "--end", "2024-01-15",
                "--zipline-root", str(tmp_path / "zr"),
                "--output-dir", str(tmp_path / "out"),
                "--tearsheet",
            ],
        )

    assert result.exit_code == 0, result.output
    fake_qs.reports.html.assert_called_once()


def test_list_bundles_includes_finmind():
    runner = CliRunner()
    result = runner.invoke(cli_mod.cli, ["list-bundles"])
    assert result.exit_code == 0, result.output
    # finmind is registered at module import (side-effect of _ensure_bundle_registered)
    assert "finmind" in result.output


# --------------------------------------------------------------------------- #
# ingest command
# --------------------------------------------------------------------------- #
_FB = "backtest_platform.engines.zipline_adapter.bundles.finmind_bundle"


def test_ingest_dry_run_lists_universe_without_calling_helper():
    runner = CliRunner()
    with patch(f"{_FB}.ingest_universe") as m:
        res = runner.invoke(
            cli_mod.cli,
            ["ingest", "--start", "2020-01-01", "--end", "2024-12-31", "--dry-run"],
        )
    assert res.exit_code == 0, res.output
    m.assert_not_called()
    assert "2330" in res.output and "2891" in res.output  # first + last default


def test_ingest_default_universe_invokes_helper():
    from backtest_platform.engines.zipline_adapter.bundles.finmind_bundle import (
        DEFAULT_UNIVERSE,
        UniverseIngestResult,
    )

    runner = CliRunner()
    with patch(f"{_FB}.ingest_universe") as m:
        m.return_value = UniverseIngestResult(
            bundles={s: MagicMock() for s in DEFAULT_UNIVERSE}, failed_symbols=[]
        )
        res = runner.invoke(
            cli_mod.cli, ["ingest", "--start", "2020-01-01", "--end", "2024-12-31"]
        )
    assert res.exit_code == 0, res.output
    universe_arg = m.call_args.args[0]
    assert universe_arg == list(DEFAULT_UNIVERSE)


def test_ingest_stocks_override():
    from backtest_platform.engines.zipline_adapter.bundles.finmind_bundle import (
        UniverseIngestResult,
    )

    runner = CliRunner()
    with patch(f"{_FB}.ingest_universe") as m:
        m.return_value = UniverseIngestResult(
            bundles={"2330": MagicMock(), "2454": MagicMock()}, failed_symbols=[]
        )
        res = runner.invoke(
            cli_mod.cli,
            ["ingest", "--start", "2020-01-01", "--end", "2024-12-31",
             "--stocks", "2330,2454"],
        )
    assert res.exit_code == 0, res.output
    assert m.call_args.args[0] == ["2330", "2454"]


def test_ingest_all_fail_exits_nonzero():
    runner = CliRunner()
    with patch(f"{_FB}.ingest_universe", side_effect=RuntimeError("all failed")):
        res = runner.invoke(
            cli_mod.cli, ["ingest", "--start", "2020-01-01", "--end", "2024-12-31"]
        )
    assert res.exit_code == 1
    assert "failed" in res.output.lower()


def test_ingest_partial_failure_warns_exit_zero():
    from backtest_platform.engines.zipline_adapter.bundles.finmind_bundle import (
        UniverseIngestResult,
    )

    runner = CliRunner()
    with patch(f"{_FB}.ingest_universe") as m:
        m.return_value = UniverseIngestResult(
            bundles={"2330": MagicMock()}, failed_symbols=["9999"]
        )
        res = runner.invoke(
            cli_mod.cli,
            ["ingest", "--start", "2020-01-01", "--end", "2024-12-31",
             "--stocks", "2330,9999"],
        )
    assert res.exit_code == 0, res.output
    assert "9999" in res.output
