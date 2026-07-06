"""research.cli — evaluate + candidates commands (rebuild Goal 3/4)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from click.testing import CliRunner

from quant_platform.services.research_validation.cli import cli


def _gen_parquet(out: Path, symbols, n_bars=500):
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(0)
    dates = pd.date_range("2018-01-01", periods=n_bars, freq="B")
    for sid in symbols:
        close = 100.0 * np.exp(np.cumsum(rng.normal(0.0004, 0.012, n_bars)))
        pd.DataFrame({"stock_id": sid, "trade_date": dates, "open": close, "high": close * 1.01,
                      "low": close * 0.99, "close": close, "volume": rng.integers(1_000_000, 9_000_000, n_bars),
                      "adj_factor": np.ones(n_bars)}).to_parquet(out / f"daily_bars__{sid}.parquet")
        pd.DataFrame({"stock_id": sid, "trade_date": dates,
                      "foreign_buy": rng.integers(-500_000, 600_000, n_bars),
                      "trust_buy": rng.integers(-200_000, 200_000, n_bars),
                      "dealer_buy": rng.integers(-100_000, 100_000, n_bars)}).to_parquet(out / f"institutional__{sid}.parquet")
        pd.DataFrame({"stock_id": sid, "trade_date": dates,
                      "top_broker_buy": rng.integers(0, 100_000, n_bars), "key_broker_buy": rng.integers(0, 50_000, n_bars),
                      "gov_broker_buy": rng.integers(0, 30_000, n_bars), "geo_broker_buy": rng.integers(0, 20_000, n_bars),
                      "day_trade_volume": rng.integers(0, 500_000, n_bars),
                      "margin_offset_volume": rng.integers(0, 200_000, n_bars)}).to_parquet(out / f"broker_chips__{sid}.parquet")


def test_evaluate_unknown_profile_errors():
    runner = CliRunner()
    result = runner.invoke(cli, ["evaluate", "--strategy", "momentum", "--profile", "ghost"])
    assert result.exit_code != 0
    assert "unknown evaluation profile" in result.output


def test_evaluate_and_candidates_flow():
    runner = CliRunner()
    with runner.isolated_filesystem():
        data_dir = Path("synth").resolve()
        _gen_parquet(data_dir, ["2330", "2317", "2454"])
        ev = runner.invoke(cli, [
            "evaluate", "--strategy", "momentum", "--profile", "quick_triage",
            "--data-dir", str(data_dir), "--symbols", "2330,2317,2454",
            "--start", "2019-01-01", "--end", "2020-12-31",
        ])
        assert ev.exit_code == 0, ev.output
        assert "evaluation_id=" in ev.output
        assert "candidate cand_momentum" in ev.output

        lst = runner.invoke(cli, ["candidates", "list"])
        assert "cand_momentum" in lst.output

        dec = runner.invoke(cli, ["candidates", "decide", "--candidate", "cand_momentum",
                                  "--action", "keep", "--label", "weak"])
        assert dec.exit_code == 0
        assert "triaged → weak" in dec.output

        # not-recommended select without reason → clean CLI error
        bad = runner.invoke(cli, ["candidates", "select-live-oos", "--candidate", "cand_momentum"])
        assert bad.exit_code != 0

        ok = runner.invoke(cli, ["candidates", "select-live-oos", "--candidate", "cand_momentum",
                                 "--override", "--reason", "paper look"])
        assert ok.exit_code == 0
        assert "live_oos_selected" in ok.output


def test_candidates_decide_unknown_candidate_errors():
    runner = CliRunner()
    with runner.isolated_filesystem():
        r = runner.invoke(cli, ["candidates", "decide", "--candidate", "cand_ghost",
                                "--action", "keep", "--label", "weak"])
        assert r.exit_code != 0
