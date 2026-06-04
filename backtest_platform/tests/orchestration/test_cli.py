"""orchestration.cli — run (dry-run / real) + list-stages."""
from __future__ import annotations

from click.testing import CliRunner

from backtest_platform.orchestration.cli import cli


def test_run_dry_run_passes():
    res = CliRunner().invoke(cli, ["run", "--dry-run"])
    assert res.exit_code == 0, res.output
    assert "FLOW: OK" in res.output


def test_run_real_without_collaborators_fails_clean():
    # --real with no injected collaborators → first stage reports the gap, exit 1
    res = CliRunner().invoke(cli, ["run", "--real"])
    assert res.exit_code == 1
    assert "FLOW: FAILED @ etl" in res.output
    assert "missing collaborator 'ingest'" in res.output


def test_list_stages():
    res = CliRunner().invoke(cli, ["list-stages"])
    assert res.exit_code == 0, res.output
    assert res.output.split() == ["etl", "signals", "risk_gate", "orders", "log"]
