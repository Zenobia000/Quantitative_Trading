"""CLI surface for the觀察艙 registry — `watch enroll` / `watch status`.

Runs inside an isolated filesystem so the default ``reports/watch_registry.jsonl``
lands under a tmp cwd; no network, no calendar extra (weekday fallback is fine).
"""
from __future__ import annotations

from click.testing import CliRunner

from backtest_platform.orchestration.cli import cli


def test_watch_enroll_admits_paper_watch_band_dsr():
    runner = CliRunner()
    with runner.isolated_filesystem():
        res = runner.invoke(
            cli,
            ["watch", "enroll", "--strategy", "inst_flow",
             "--dsr", "0.908", "--enrolled-on", "2026-07-02"],
        )
        assert res.exit_code == 0, res.output
        assert "inst_flow" in res.output
        assert "active" in res.output.lower() or "觀察艙" in res.output

        # status now lists the active berth
        st = runner.invoke(cli, ["watch", "status"])
        assert st.exit_code == 0, st.output
        assert "inst_flow" in st.output


def test_watch_enroll_rejects_out_of_band_dsr():
    runner = CliRunner()
    with runner.isolated_filesystem():
        res = runner.invoke(
            cli,
            ["watch", "enroll", "--strategy", "rejected_one",
             "--dsr", "0.80", "--enrolled-on", "2026-07-02"],
        )
        assert res.exit_code != 0  # REJECTED-band DSR may not enter the觀察艙
        assert "0.90" in res.output or "PAPER_WATCH" in res.output or "band" in res.output.lower()


def test_watch_status_empty_is_clean():
    runner = CliRunner()
    with runner.isolated_filesystem():
        st = runner.invoke(cli, ["watch", "status"])
        assert st.exit_code == 0, st.output


def test_watch_pause_then_resume_round_trip():
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(cli, ["watch", "enroll", "--strategy", "inst_flow",
                            "--dsr", "0.908", "--enrolled-on", "2026-07-02"])
        paused = runner.invoke(cli, ["watch", "pause", "--strategy", "inst_flow"])
        assert paused.exit_code == 0, paused.output
        assert "paused" in paused.output.lower()
        # a paused berth drops out of the active-only status list
        assert "inst_flow" not in runner.invoke(cli, ["watch", "status"]).output

        resumed = runner.invoke(cli, ["watch", "resume", "--strategy", "inst_flow"])
        assert resumed.exit_code == 0, resumed.output
        assert "inst_flow" in runner.invoke(cli, ["watch", "status"]).output


def test_watch_pause_unknown_strategy_fails():
    runner = CliRunner()
    with runner.isolated_filesystem():
        res = runner.invoke(cli, ["watch", "pause", "--strategy", "never_enrolled"])
        assert res.exit_code != 0
        assert "未進觀察艙" in res.output or "no berth" in res.output.lower()
