"""Executable re-export shim (W5.1c) — cli moved to services.strategy_runtime.cli.

Kept executable so `python -m backtest_platform.orchestration.cli` (systemd/cron)
still works while the canonical path is now
`python -m backtest_platform.services.strategy_runtime.cli`.
"""
from backtest_platform.services.strategy_runtime.cli import cli

__all__ = ["cli"]

if __name__ == "__main__":
    cli()
