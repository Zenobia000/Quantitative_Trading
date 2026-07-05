"""research.cli — branches create / list / evaluate / compare (rebuild Goal 9)."""
from __future__ import annotations

import re
from pathlib import Path

from click.testing import CliRunner

from backtest_platform.research.cli import cli
from tests.research.test_cli_evaluate import _gen_parquet

_SYMS = ["2330", "2317", "2454"]


def _seed_parent(runner, data_dir: Path) -> str:
    ev = runner.invoke(cli, [
        "evaluate", "--strategy", "momentum", "--profile", "quick_triage",
        "--data-dir", str(data_dir), "--symbols", ",".join(_SYMS),
        "--start", "2019-01-01", "--end", "2020-12-31", "--no-ingest",
    ])
    assert ev.exit_code == 0, ev.output
    m = re.search(r"evaluation_id=(\S+)", ev.output)
    assert m, ev.output
    return m.group(1)


def test_branches_create_list_evaluate_compare_flow():
    runner = CliRunner()
    with runner.isolated_filesystem():
        data_dir = Path("synth").resolve()
        _gen_parquet(data_dir, _SYMS)
        parent_eval = _seed_parent(runner, data_dir)

        create = runner.invoke(cli, [
            "branches", "create", "--parent", parent_eval,
            "--set", "lookback_days=90", "--note", "longer window",
        ])
        assert create.exit_code == 0, create.output
        assert "applies_to_rerun=True" in create.output
        bid = create.output.split()[0]

        lst = runner.invoke(cli, ["branches", "list"])
        assert bid in lst.output and "momentum" in lst.output

        # compare before evaluate → prompt, not error.
        pre = runner.invoke(cli, ["branches", "compare", "--branch", bid])
        assert pre.exit_code == 0
        assert "not yet evaluated" in pre.output

        ev = runner.invoke(cli, ["branches", "evaluate", "--branch", bid, "--data-dir", str(data_dir)])
        assert ev.exit_code == 0, ev.output
        assert "status=evaluated" in ev.output

        cmp = runner.invoke(cli, ["branches", "compare", "--branch", bid])
        assert cmp.exit_code == 0, cmp.output
        assert "sharpe" in cmp.output
        assert "decision:" in cmp.output


def test_branches_create_illegal_key_errors():
    runner = CliRunner()
    with runner.isolated_filesystem():
        data_dir = Path("synth").resolve()
        _gen_parquet(data_dir, _SYMS)
        parent_eval = _seed_parent(runner, data_dir)
        r = runner.invoke(cli, ["branches", "create", "--parent", parent_eval, "--set", "bogus=1"])
        assert r.exit_code != 0
        assert "illegal config_delta key" in r.output


def test_branches_create_unknown_parent_errors():
    runner = CliRunner()
    with runner.isolated_filesystem():
        r = runner.invoke(cli, ["branches", "create", "--parent", "eval_ghost", "--set", "x=1"])
        assert r.exit_code != 0
