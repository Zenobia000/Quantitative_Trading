#!/usr/bin/env bash
#
# backup.sh — daily backup of the three non-reproducible assets (doc 14 §4, doc 13 §D.2):
#   1. TimescaleDB telemetry  → gzipped plain pg_dump   ($BACKUP_DEST/pg/<date>.sql.gz)
#   2. reports/               → runs ledger JSONL + after-close markers (rsync mirror)
#   3. data/parquet*          → paid FinLab ingest + survivorship-clean cache (rsync mirror)
#
# Standalone / single-machine (ADR-031). $BACKUP_DEST is a LOCAL path — an external
# drive or NAS mount point — supplied by the environment, never hardcoded.
#
# Any pg_dump / rsync failure aborts the whole run (FAIL) and alerts Discord; success
# also alerts Discord. A missing Discord token degrades to a local log line, never a crash.
#
# Usage:
#   BACKUP_DEST=/mnt/nas/qt-backup deploy/backup.sh        # full backup
#   deploy/backup.sh --prune-only <dir> <keep>             # retention helper (used by tests)
#
# Restore steps live in deploy/README.md § Restore.

set -Eeuo pipefail

# --------------------------------------------------------------------------- #
# Paths & config (defaults mirror docker-compose.yml; override via env)         #
# --------------------------------------------------------------------------- #
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"

PG_SERVICE="${PG_SERVICE:-timescaledb}"        # docker-compose service name
PG_USER="${POSTGRES_USER:-quant}"              # docker-compose POSTGRES_USER default
PG_DB="${POSTGRES_DB:-quant_trading}"          # docker-compose POSTGRES_DB default
PG_KEEP="${PG_KEEP:-14}"                        # retain the newest N pg dumps

DATE="$(date +%F)"                              # YYYY-MM-DD (host clock, assumed Asia/Taipei)
CURRENT_STEP="init"

# Inline Python for the Discord side-channel. argv: <ok|error> <message>.
# Exit 0 = sent, exit 3 = skipped (missing token / import / network) → caller logs locally.
readonly NOTIFY_PY='
import sys
kind = sys.argv[1] if len(sys.argv) > 1 else "ok"
msg = sys.argv[2] if len(sys.argv) > 2 else ""
try:
    from quant_platform.services.monitoring_ops.discord_notifier import notify_info, notify_error
    if kind == "ok":
        notify_info(msg)
    else:
        notify_error("backup", msg)
except Exception as exc:  # missing DISCORD_BOT_TOKEN / network down / import error
    print(f"discord notify skipped: {exc}", file=sys.stderr)
    raise SystemExit(3)
'

# --------------------------------------------------------------------------- #
# Helpers                                                                        #
# --------------------------------------------------------------------------- #
log() { printf '%s [backup] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }

# notify <ok|error> <message...> — never aborts the script (side channel).
notify() {
    local kind="${1:-ok}"; shift || true
    local msg="${*:-}"
    if ! command -v uv >/dev/null 2>&1; then
        log "DISCORD-DEGRADED (uv not found) [${kind}] ${msg}"
        return 0
    fi
    if ( cd "$PROJECT_ROOT" && uv run python -c "$NOTIFY_PY" "$kind" "$msg" ); then
        return 0
    fi
    # exit 3 (skipped) or any other non-zero → degrade to a local echo of the message.
    log "DISCORD-DEGRADED [${kind}] ${msg}"
    return 0
}

fail() {
    log "FAIL: $*"
    notify error "Backup FAILED on $(hostname): $*"
    exit 1
}

on_error() {
    local rc=$?
    trap - ERR
    fail "unexpected error (line ${BASH_LINENO[0]:-?}, exit ${rc}); step=${CURRENT_STEP}"
}

# prune_pg_dumps <dir> <keep> — keep the newest <keep> *.sql.gz, delete older.
# Filenames are ISO dates (YYYY-MM-DD.sql.gz) so lexical sort == chronological.
prune_pg_dumps() {
    local dir="$1" keep="$2"
    [[ -d "$dir" ]] || return 0
    local -a files=()
    mapfile -t files < <(find "$dir" -maxdepth 1 -type f -name '*.sql.gz' | sort -r)
    local i=0 f
    for f in "${files[@]}"; do
        i=$((i + 1))
        if (( i > keep )); then
            rm -f -- "$f"
            log "pruned old pg dump: $(basename "$f")"
        fi
    done
}

validate_config() {
    if [[ -z "${BACKUP_DEST:-}" ]]; then
        echo "[backup] ERROR: BACKUP_DEST env var is required — set it to your backup mount" \
             "(e.g. /mnt/nas/qt-backup). Aborting." >&2
        exit 1
    fi
    if [[ ! -d "$BACKUP_DEST" ]]; then
        echo "[backup] ERROR: BACKUP_DEST '$BACKUP_DEST' is not a directory" \
             "(is the backup drive / NAS mounted?). Aborting." >&2
        exit 1
    fi
}

# --------------------------------------------------------------------------- #
# Backup steps                                                                   #
# --------------------------------------------------------------------------- #
backup_timescaledb() {
    CURRENT_STEP="pg_dump"
    local pg_dir="$BACKUP_DEST/pg"
    local dump_file="$pg_dir/${DATE}.sql.gz"
    mkdir -p "$pg_dir"

    # Container must be up AND the DB ready — pg_isready doubles as a liveness probe.
    if ! docker compose -f "$COMPOSE_FILE" exec -T "$PG_SERVICE" \
            pg_isready -U "$PG_USER" -d "$PG_DB" >/dev/null 2>&1; then
        fail "TimescaleDB service '$PG_SERVICE' not reachable (pg_isready failed) — container down?"
    fi

    log "dumping ${PG_DB} → ${dump_file}"
    docker compose -f "$COMPOSE_FILE" exec -T "$PG_SERVICE" \
        pg_dump -U "$PG_USER" "$PG_DB" | gzip > "$dump_file" \
        || fail "pg_dump/gzip failed for database '$PG_DB'"
    [[ -s "$dump_file" ]] || fail "pg_dump produced an empty file ($dump_file)"

    local dump_size
    dump_size="$(du -h "$dump_file" | cut -f1)"
    log "pg dump ok (${dump_size})"
    prune_pg_dumps "$pg_dir" "$PG_KEEP"
    PG_SUMMARY="pg=${DATE}.sql.gz (${dump_size})"
}

backup_reports() {
    CURRENT_STEP="rsync reports"
    if [[ -d "$PROJECT_ROOT/reports" ]]; then
        log "rsync reports/ → $BACKUP_DEST/reports/"
        rsync -a --delete "$PROJECT_ROOT/reports/" "$BACKUP_DEST/reports/" \
            || fail "rsync of reports/ failed"
    else
        log "reports/ not present yet — skipping"
    fi
}

backup_parquet() {
    CURRENT_STEP="rsync parquet"
    local -a dirs=()
    shopt -s nullglob
    dirs=("$PROJECT_ROOT"/data/parquet*)
    shopt -u nullglob
    if (( ${#dirs[@]} == 0 )); then
        log "no data/parquet* dirs yet — skipping"
        return 0
    fi
    local d name
    for d in "${dirs[@]}"; do
        [[ -d "$d" ]] || continue
        name="$(basename "$d")"
        log "rsync ${name}/ (incl. manifest) → $BACKUP_DEST/data/$name/"
        rsync -a --delete "$d/" "$BACKUP_DEST/data/$name/" \
            || fail "rsync of data/${name}/ failed"
    done
}

# --------------------------------------------------------------------------- #
# Main                                                                          #
# --------------------------------------------------------------------------- #
main() {
    # Retention helper mode — no BACKUP_DEST / docker needed (used by the smoke test).
    if [[ "${1:-}" == "--prune-only" ]]; then
        if [[ $# -ne 3 ]]; then
            echo "usage: $0 --prune-only <dir> <keep>" >&2
            exit 2
        fi
        prune_pg_dumps "$2" "$3"
        exit 0
    fi

    validate_config
    trap on_error ERR

    log "backup start → $BACKUP_DEST (pg keep=${PG_KEEP})"
    PG_SUMMARY=""
    backup_timescaledb
    backup_reports
    backup_parquet

    log "backup complete"
    notify ok "Backup OK on $(hostname): ${PG_SUMMARY}; reports/ + data/parquet* synced to $BACKUP_DEST"
}

main "$@"
