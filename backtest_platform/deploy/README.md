# after-close scheduler — install (systemd user timer / cron)

Fires the forward paper session once per weekday after the TWSE close, collecting
live OOS. The CLI guards a real-calendar run itself (trading-day → 14:30 gate →
idempotency → 觀察艙 enrollment), so a weekend / holiday / early / duplicate fire is
a clean no-op (exit 0); a genuine daily-flow failure exits non-zero and alerts
Discord, while a strategy with no active觀察艙 berth is refused before it runs.

## Prerequisites

- `uv` on PATH and the project installed with the **exact XTAI holiday calendar**:

  ```bash
  uv sync --all-extras        # or, minimally: uv sync --extra calendar
  ```

  The `calendar` extra installs `exchange_calendars` (XTAI). Without it the
  scheduler falls back to a Mon–Fri approximation that treats weekday Taiwan public
  / lunar holidays as sessions — it over-fires on ~10–15 days/year, and each such
  day is a false Discord alert source that would drown a 3-month observation in
  noise. Installing the extra is therefore a data-quality prerequisite, not optional
  polish (the calendar mode is logged once at first fire — see doc 14 §3).
- `.env` filled with `FINLAB_API_TOKEN`, `POSTGRES_*`, and `DISCORD_*` (gitignored).
- **The strategy holds an active觀察艙 berth** (ADR-033): a real after-close run is
  refused unless the strategy holds an active berth. As of ADR-040 (Goal 10) the
  **primary** way a berth comes to exist is the **live-OOS selection queue**: an
  operator selects a candidate for Live OOS in the Candidate Pool, and the timer's
  `ExecStartPre` (`live-oos consume`) enrolls the berth on the next fire. So the
  normal path needs no manual enroll — just select the candidate. The manual CLI
  remains for ops override / testing:

  ```bash
  # Preferred: select in the Candidate Pool UI (or `candidates select-live-oos`),
  # then the after-close.service ExecStartPre consumes the queue and enrolls the berth.
  uv run python -m backtest_platform.orchestration.cli live-oos consume   # what ExecStartPre runs
  uv run python -m backtest_platform.orchestration.cli live-oos list      # inspect the queue

  # Manual override (ops / testing) — enroll a berth directly:
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

---

# backup — daily backup of the non-reproducible assets

`backup.sh` backs up the three assets that cannot be regenerated (doc 14 §4, doc 13 §D.2):

| Asset | Source | Destination | Method |
| :--- | :--- | :--- | :--- |
| TimescaleDB telemetry | `timescaledb` container (`quant_trading` DB) | `$BACKUP_DEST/pg/<date>.sql.gz` | gzipped plain `pg_dump`, newest **14** kept |
| Runs ledger + markers | `reports/` | `$BACKUP_DEST/reports/` | `rsync -a --delete` mirror |
| Paid FinLab + clean cache | `data/parquet*` (incl. manifest) | `$BACKUP_DEST/data/<name>/` | `rsync -a --delete` mirror |

`$BACKUP_DEST` is a **local** path — an external drive or NAS mount point (standalone /
single-machine, ADR-031). It is never hardcoded; set it via env / `.env`. If it is unset
or not a mounted directory the script exits 1 with a clear message. Every run alerts Discord
(success **and** failure via `monitoring.discord_notifier`); a missing `DISCORD_BOT_TOKEN`
degrades to a local log line, never a crash. Any `pg_dump` / `rsync` failure aborts the whole
run and fires a Discord error alert (RPO 24h / RTO < 1h).

## Prerequisites

- The docker stack up (`docker compose up -d`) — `pg_dump` runs inside the `timescaledb` container.
- `BACKUP_DEST` set to a mounted backup path, e.g. `/mnt/nas/qt-backup` (put it in `.env`).
- `uv` on PATH (used only for the Discord alert; the backup itself works without it).

Manual run:

```bash
BACKUP_DEST=/mnt/nas/qt-backup bash deploy/backup.sh
# override retention (default 14 pg dumps):  PG_KEEP=30 BACKUP_DEST=... bash deploy/backup.sh
```

## Option A — systemd user timer (recommended)

```bash
mkdir -p ~/.config/systemd/user
cp deploy/backup.service deploy/backup.timer ~/.config/systemd/user/
# Ensure BACKUP_DEST is in .env (EnvironmentFile), or:
#   systemctl --user edit backup.service   → [Service] Environment=BACKUP_DEST=/mnt/nas/qt
systemctl --user daemon-reload
systemctl --user enable --now backup.timer
loginctl enable-linger "$USER"                  # let it run while you're logged out
systemctl --user list-timers backup.timer       # verify next trigger (15:30 Asia/Taipei)
journalctl --user -u backup.service -n 50        # inspect the last run
```

## Option B — cron

```bash
crontab -e   # paste deploy/backup.cron.example, edit the absolute path
```

The cron line sources `.env` (so `BACKUP_DEST` lives there) and logs to
`reports/backup.cron.log`. The systemd timer's `OnCalendar=... Asia/Taipei` is
timezone-correct and preferred (cron assumes the host clock is Asia/Taipei).

## Restore

```bash
# 1. TimescaleDB — decompress the chosen dump and pipe into psql inside the container.
#    (--clean handled by the dump; drop/recreate the DB first if you want a pristine load.)
gunzip -c "$BACKUP_DEST/pg/2026-07-02.sql.gz" \
    | docker compose exec -T timescaledb psql -U quant -d quant_trading

# 2. reports/ + data/parquet* — reverse rsync from the backup back into the checkout.
rsync -a "$BACKUP_DEST/reports/" reports/
rsync -a "$BACKUP_DEST/data/parquet/" data/parquet/
rsync -a "$BACKUP_DEST/data/parquet_finlab_universe/" data/parquet_finlab_universe/
```

Recovery drill (quarterly, doc 14 §4.2): delete one day of data → restore → run
`uv run python -m backtest_platform.research.cli truth-gate --strategy <s> --dry-run` smoke.

