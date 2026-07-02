"""Smoke tests for ``deploy/backup.sh``.

The script is pure bash (no Python source to unit-test), so we cover the two
behaviours that are cheap to exercise without a live docker/NAS stack:

1. ``bash -n`` — the script parses.
2. The ``BACKUP_DEST`` guard exits 1 with a clear message when it is unset.
3. The ``--prune-only`` retention helper keeps the newest N dumps and no more.

We run the script with a hermetic environment (PATH only) so a developer's
``.env`` / exported ``BACKUP_DEST`` can never leak in and mask the guard test.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

PLATFORM_ROOT = Path(__file__).resolve().parents[2]
BACKUP_SH = PLATFORM_ROOT / "deploy" / "backup.sh"


def _hermetic_env() -> dict[str, str]:
    """Only PATH — nothing that could supply BACKUP_DEST or DISCORD_* from the shell."""
    return {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}


def test_script_exists_and_is_executable() -> None:
    assert BACKUP_SH.is_file(), f"missing {BACKUP_SH}"
    assert os.access(BACKUP_SH, os.X_OK), "backup.sh should be executable"


def test_bash_syntax_ok() -> None:
    result = subprocess.run(
        ["bash", "-n", str(BACKUP_SH)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_missing_backup_dest_exits_1() -> None:
    result = subprocess.run(
        ["bash", str(BACKUP_SH)],
        capture_output=True,
        text=True,
        env=_hermetic_env(),
    )
    assert result.returncode == 1, (result.returncode, result.stdout, result.stderr)
    assert "BACKUP_DEST" in (result.stdout + result.stderr)


def test_nonexistent_backup_dest_exits_1(tmp_path: Path) -> None:
    missing = tmp_path / "not-mounted"  # deliberately not created
    result = subprocess.run(
        ["bash", str(BACKUP_SH)],
        capture_output=True,
        text=True,
        env={**_hermetic_env(), "BACKUP_DEST": str(missing)},
    )
    assert result.returncode == 1, (result.returncode, result.stdout, result.stderr)
    assert "not a directory" in (result.stdout + result.stderr)


def test_prune_keeps_newest_n(tmp_path: Path) -> None:
    pg_dir = tmp_path / "pg"
    pg_dir.mkdir()
    # 20 ISO-dated dumps; lexical order == chronological order.
    for day in range(1, 21):
        (pg_dir / f"2026-01-{day:02d}.sql.gz").write_text("x")

    result = subprocess.run(
        ["bash", str(BACKUP_SH), "--prune-only", str(pg_dir), "14"],
        capture_output=True,
        text=True,
        env=_hermetic_env(),
    )
    assert result.returncode == 0, result.stderr

    remaining = sorted(p.name for p in pg_dir.glob("*.sql.gz"))
    assert len(remaining) == 14
    assert remaining[0] == "2026-01-07.sql.gz"   # oldest kept
    assert remaining[-1] == "2026-01-20.sql.gz"  # newest kept


def test_prune_is_noop_below_limit(tmp_path: Path) -> None:
    pg_dir = tmp_path / "pg"
    pg_dir.mkdir()
    for name in ("2026-02-01.sql.gz", "2026-02-02.sql.gz"):
        (pg_dir / name).write_text("x")

    result = subprocess.run(
        ["bash", str(BACKUP_SH), "--prune-only", str(pg_dir), "14"],
        capture_output=True,
        text=True,
        env=_hermetic_env(),
    )
    assert result.returncode == 0, result.stderr
    assert len(list(pg_dir.glob("*.sql.gz"))) == 2


def test_prune_only_bad_args_exits_2(tmp_path: Path) -> None:
    result = subprocess.run(
        ["bash", str(BACKUP_SH), "--prune-only", str(tmp_path)],  # missing <keep>
        capture_output=True,
        text=True,
        env=_hermetic_env(),
    )
    assert result.returncode == 2, (result.returncode, result.stdout, result.stderr)


@pytest.mark.parametrize("keep", ["0", "3"])
def test_prune_respects_keep_count(tmp_path: Path, keep: str) -> None:
    pg_dir = tmp_path / "pg"
    pg_dir.mkdir()
    for day in range(1, 6):  # 5 dumps
        (pg_dir / f"2026-03-{day:02d}.sql.gz").write_text("x")

    result = subprocess.run(
        ["bash", str(BACKUP_SH), "--prune-only", str(pg_dir), keep],
        capture_output=True,
        text=True,
        env=_hermetic_env(),
    )
    assert result.returncode == 0, result.stderr
    assert len(list(pg_dir.glob("*.sql.gz"))) == int(keep)
