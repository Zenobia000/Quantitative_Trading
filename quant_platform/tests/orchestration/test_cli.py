"""orchestration.cli — run (dry-run / real) + list-stages + after-close."""
from __future__ import annotations

from datetime import date

from click.testing import CliRunner

from quant_platform.services.strategy_runtime import cli as cli_mod
from quant_platform.services.strategy_runtime.cli import cli


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


# --------------------------------------------------------------------------- #
# after-close subcommand — wired to the injectable orchestration core         #
# --------------------------------------------------------------------------- #
class _FakeSummary:
    ok = True

    def summary(self) -> str:
        return "REPLAY: 1/1 sessions green"


def test_after_close_dry_run_does_not_build_session_runner(monkeypatch):
    # dry-run must never construct the production runner (no finlab/DB touched).
    def _explode(*_a, **_k):
        raise AssertionError("session runner must not be built in dry-run")

    monkeypatch.setattr(cli_mod, "build_session_runner", _explode)
    res = CliRunner().invoke(
        cli,
        ["after-close", "--strategy", "inst_flow", "--date", "2026-07-02",
         "--dry-run", "--force"],
    )
    assert res.exit_code == 0, res.output
    assert "DRY_RUN" in res.output or "dry" in res.output.lower()


def test_after_close_success_exit_zero(monkeypatch):
    calls: list[tuple[str, date]] = []

    def _fake_builder(strategy, universe, equity, *, fresh=False):
        def _run(strat, as_of):
            calls.append((strat, as_of))
            return _FakeSummary()
        return _run

    monkeypatch.setattr(cli_mod, "build_session_runner", _fake_builder)
    monkeypatch.setattr(cli_mod, "safe_discord_notify", lambda *_a, **_k: None)
    with CliRunner().isolated_filesystem():
        # A real after-close run now requires an active觀察艙 berth (ADR-033).
        from quant_platform.services.governance_release.watch_registry import enroll
        enroll("inst_flow", 0.908, date(2026, 7, 2))
        res = CliRunner().invoke(
            cli,
            ["after-close", "--strategy", "inst_flow", "--date", "2026-07-02",
             "--force", "--universe", "2330,2317"],
        )
    assert res.exit_code == 0, res.output
    assert calls == [("inst_flow", date(2026, 7, 2))]


def test_after_close_fresh_flag_is_forwarded(monkeypatch):
    """--fresh reaches build_session_runner so restore can be opted out of."""
    seen: dict[str, bool] = {}

    def _fake_builder(strategy, universe, equity, *, fresh=False):
        seen["fresh"] = fresh
        return lambda strat, as_of: _FakeSummary()

    monkeypatch.setattr(cli_mod, "build_session_runner", _fake_builder)
    monkeypatch.setattr(cli_mod, "safe_discord_notify", lambda *_a, **_k: None)
    with CliRunner().isolated_filesystem():
        from quant_platform.services.governance_release.watch_registry import enroll
        enroll("inst_flow", 0.908, date(2026, 7, 2))
        res = CliRunner().invoke(
            cli,
            ["after-close", "--strategy", "inst_flow", "--date", "2026-07-02",
             "--force", "--universe", "2330,2317", "--fresh"],
        )
    assert res.exit_code == 0, res.output
    assert seen == {"fresh": True}


def test_after_close_non_trading_day_exit_zero(monkeypatch):
    # No --universe and the REAL build_session_runner: the trading-day guard must
    # short-circuit BEFORE the (universe-requiring) runner is ever built, so a
    # weekend / holiday fire is a clean no-op instead of a "no universe" crash.
    monkeypatch.setattr(cli_mod, "safe_discord_notify", lambda *_a, **_k: None)
    with CliRunner().isolated_filesystem():
        res = CliRunner().invoke(
            cli,
            ["after-close", "--strategy", "inst_flow", "--date", "2026-07-04",  # Saturday
             "--force"],
        )
    assert res.exit_code == 0, res.output
    assert "not a TWSE trading day" in res.output
    assert res.exception is None  # no traceback leaked


def test_after_close_failed_session_exit_nonzero(monkeypatch):
    class _FailSummary:
        ok = False

        def summary(self) -> str:
            return "REPLAY: 0/1 sessions green"

    def _fake_builder(strategy, universe, equity, *, fresh=False):
        return lambda strat, as_of: _FailSummary()

    monkeypatch.setattr(cli_mod, "build_session_runner", _fake_builder)
    monkeypatch.setattr(cli_mod, "safe_discord_notify", lambda *_a, **_k: None)
    with CliRunner().isolated_filesystem():
        from quant_platform.services.governance_release.watch_registry import enroll
        enroll("inst_flow", 0.908, date(2026, 7, 2))  # admit so we test FAILED, not NOT_ENROLLED
        res = CliRunner().invoke(
            cli,
            ["after-close", "--strategy", "inst_flow", "--date", "2026-07-02",
             "--force", "--universe", "2330"],
        )
    assert res.exit_code == 1, res.output
    assert "FAILED" in res.output
