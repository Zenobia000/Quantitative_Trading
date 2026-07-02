# after-close scheduler — install (systemd user timer / cron)

Fires the forward paper session once per weekday after the TWSE close, collecting
live OOS. The CLI guards a real-calendar run itself (trading-day → 14:30 gate →
idempotency → 觀察艙 enrollment), so a weekend / holiday / early / duplicate fire is
a clean no-op (exit 0); a genuine daily-flow failure exits non-zero and alerts
Discord, while a strategy with no active觀察艙 berth is refused before it runs.

## Prerequisites

- `uv` on PATH and the project installed with the **exact XTAI holiday calendar**:

  ```bash
  uv sync --all-extras        # or, minimally: uv sync --extra mainframe
  ```

  The `mainframe` extra installs `exchange_calendars` (XTAI). Without it the
  scheduler falls back to a Mon–Fri approximation that treats weekday Taiwan public
  / lunar holidays as sessions — it over-fires on ~10–15 days/year, and each such
  day is a false Discord alert source that would drown a 3-month observation in
  noise. Installing the extra is therefore a data-quality prerequisite, not optional
  polish (the calendar mode is logged once at first fire — see doc 14 §3).
- `.env` filled with `FINLAB_API_TOKEN`, `POSTGRES_*`, and `DISCORD_*` (gitignored).
- **The strategy is enrolled in the觀察艙** (ADR-033): a real after-close run is
  refused unless the strategy holds an active berth. Enroll it *before* installing
  the timer:

  ```bash
  uv run python -m backtest_platform.orchestration.cli \
      watch enroll --strategy inst_flow --dsr 0.908
  uv run python -m backtest_platform.orchestration.cli watch status
  ```

## Option A — systemd user timer (recommended)

```bash
mkdir -p ~/.config/systemd/user
cp deploy/after-close.service deploy/after-close.timer ~/.config/systemd/user/
# Edit WorkingDirectory / EnvironmentFile / --universe in the .service to your paths.
systemctl --user daemon-reload
systemctl --user enable --now after-close.timer
loginctl enable-linger "$USER"        # let the timer run while you're logged out
systemctl --user list-timers after-close.timer   # verify next trigger
journalctl --user -u after-close.service -n 50    # inspect the last run
```

Back-fill a missed session manually:

```bash
uv run python -m backtest_platform.orchestration.cli \
    after-close --strategy inst_flow --date 2026-07-01 --universe 2330,2317
```

## Cross-day position restore

Each session rehydrates the strategy's book from telemetry before running, so the
portfolio risk gates (EX-002 / EX-004 / EX-007) see yesterday's holdings instead of
starting from an empty book: cash from the latest `equity_snapshots`, positions
folded from the persisted fills (`data.db_reader.load_broker_state`). The first ever
session (no telemetry) starts fresh; a DB failure fails the session loudly (exit 1 +
Discord alert) rather than silently starting empty. Pass `--fresh` to opt out and
force an empty-book start:

```bash
uv run python -m backtest_platform.orchestration.cli \
    after-close --strategy inst_flow --universe 2330,2317 --fresh
```

## Option B — cron

```bash
crontab -e   # paste deploy/after-close.cron.example, edit path + universe
```

Cron has no per-line timezone: the example assumes the host clock is Asia/Taipei
(use 06:35 UTC otherwise). The systemd timer's `OnCalendar=... Asia/Taipei` is
timezone-correct and preferred.
