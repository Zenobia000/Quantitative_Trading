#!/usr/bin/env python3
"""Contract-drift guard for the backtest platform.

Runs three independent, environment-light checks and fails (exit 1) if any
finds drift. Designed to run from the repo root, both locally
(``python scripts/check_openapi_drift.py``) and in CI.

Check A — OpenAPI drift
    Dumps the *live* OpenAPI spec from the running FastAPI app
    (``backtest_platform.api.app:app``) via ``uv run`` and compares it, in a
    canonical (key-sorted) form, against the committed ``frontend/openapi.json``.
    A mismatch means the frontend contract snapshot is stale — regenerate it
    with ``npm run gen:api`` after re-dumping the spec.

Check B — runs DDL / db_writer column alignment
    Parses the ``runs`` table column list from the TimescaleDB init DDL
    (``backtest_platform/docker/timescaledb/init.sql``) and the ``_RUNS_COLS``
    tuple from ``data/db_writer.py`` (via ``ast`` — no import, no heavy deps).
    Every column db_writer inserts into must exist in the DDL, and every
    NOT NULL column without a DEFAULT must be supplied by db_writer. Either
    violation means an ``INSERT INTO runs`` would fail at runtime.

Check C — data_source literals vs the DataSource enum
    Static-scans ``api/routers/*.py`` + ``api/envelope.py`` (via ``ast`` — no
    import) for every ``{"data_source": ...}`` dict assignment; each value must be
    a ``DataSource`` enum member reference or a string equal to a member value.
    An unknown literal (a re-introduced uncoordinated token / a typo) fails —
    keeping the seven-literal sprawl from creeping back (A1).

Exit codes
    0  no drift
    1  drift detected (contract mismatch — the actionable failure)
    2  a check could not run (missing tool/file — infrastructure error)
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (all derived from this file's location — repo-root independent)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backtest_platform"
OPENAPI_SNAPSHOT = REPO_ROOT / "frontend" / "openapi.json"
INIT_SQL = BACKEND_DIR / "docker" / "timescaledb" / "init.sql"
# _RUNS_COLS moved db_writer.py → runs_writer.py in W5.2c (db_writer split).
RUNS_WRITER = BACKEND_DIR / "src" / "backtest_platform" / "data" / "runs_writer.py"
API_DIR = BACKEND_DIR / "src" / "backtest_platform" / "api"
ENVELOPE_PY = API_DIR / "envelope.py"
ROUTERS_DIR = API_DIR / "routers"

#: Cache the (expensive) live-spec dump so the checks dump once, not repeatedly.
_LIVE_SPEC_CACHE: dict | None = None


class DriftError(Exception):
    """Raised when a check finds a contract mismatch (→ exit 1)."""


class CheckInfraError(Exception):
    """Raised when a check cannot run at all (→ exit 2)."""


# ===========================================================================
# Check A — OpenAPI drift
# ===========================================================================
def dump_live_openapi() -> dict:
    """Return the live OpenAPI spec by importing the FastAPI app under ``uv``.

    Writes to a temp file (not stdout) so incidental import-time logging never
    corrupts the JSON payload. ``--extra api`` self-provisions fastapi so the
    caller need not pre-sync the full dev environment.
    """
    global _LIVE_SPEC_CACHE
    if _LIVE_SPEC_CACHE is not None:
        return _LIVE_SPEC_CACHE
    fd, tmp_path = tempfile.mkstemp(suffix=".openapi.json")
    os.close(fd)
    dump_code = (
        "import json;"
        "from backtest_platform.api.app import app;"
        f"json.dump(app.openapi(), open({tmp_path!r}, 'w'), sort_keys=True)"
    )
    try:
        proc = subprocess.run(
            ["uv", "run", "--extra", "api", "python", "-c", dump_code],
            cwd=BACKEND_DIR,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise CheckInfraError(
                "failed to dump live OpenAPI spec via `uv run`:\n"
                f"{proc.stderr.strip() or proc.stdout.strip()}"
            )
        with open(tmp_path) as fh:
            _LIVE_SPEC_CACHE = json.load(fh)
        return _LIVE_SPEC_CACHE
    except FileNotFoundError as exc:  # uv not on PATH
        raise CheckInfraError(f"`uv` not found on PATH: {exc}") from exc
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def _summarize_openapi_diff(live: dict, snapshot: dict) -> list[str]:
    """Human-readable path-level summary of where two specs diverge."""
    lines: list[str] = []
    if live.get("info", {}).get("version") != snapshot.get("info", {}).get("version"):
        lines.append(
            f"  info.version: live={live.get('info', {}).get('version')!r} "
            f"snapshot={snapshot.get('info', {}).get('version')!r}"
        )
    live_paths = set(live.get("paths", {}))
    snap_paths = set(snapshot.get("paths", {}))
    for p in sorted(live_paths - snap_paths):
        lines.append(f"  + path only in LIVE code (missing from snapshot): {p}")
    for p in sorted(snap_paths - live_paths):
        lines.append(f"  - path only in SNAPSHOT (removed from code): {p}")
    for p in sorted(live_paths & snap_paths):
        if live["paths"][p] != snapshot["paths"][p]:
            live_ops = set(live["paths"][p])
            snap_ops = set(snapshot["paths"][p])
            if live_ops != snap_ops:
                lines.append(
                    f"  ~ path {p}: operations differ "
                    f"(live={sorted(live_ops)} snapshot={sorted(snap_ops)})"
                )
            else:
                lines.append(f"  ~ path {p}: operation definition/schema differs")
    live_schemas = set(live.get("components", {}).get("schemas", {}))
    snap_schemas = set(snapshot.get("components", {}).get("schemas", {}))
    for s in sorted(live_schemas - snap_schemas):
        lines.append(f"  + schema only in LIVE code: {s}")
    for s in sorted(snap_schemas - live_schemas):
        lines.append(f"  - schema only in SNAPSHOT: {s}")
    return lines


def check_openapi_drift() -> None:
    """Compare live spec vs committed snapshot; raise DriftError on mismatch."""
    if not OPENAPI_SNAPSHOT.exists():
        raise CheckInfraError(f"snapshot not found: {OPENAPI_SNAPSHOT}")
    live = dump_live_openapi()
    with open(OPENAPI_SNAPSHOT) as fh:
        snapshot = json.load(fh)

    if json.dumps(live, sort_keys=True) == json.dumps(snapshot, sort_keys=True):
        print("[OK] OpenAPI: live spec matches frontend/openapi.json")
        return

    summary = _summarize_openapi_diff(live, snapshot)
    detail = "\n".join(summary) if summary else "  (specs differ below path level)"
    raise DriftError(
        "OpenAPI drift: live FastAPI spec != frontend/openapi.json\n"
        f"{detail}\n"
        "  fix: re-dump the spec and run `npm run gen:api` in frontend/"
    )


# ===========================================================================
# Check B — runs DDL / db_writer column alignment
# ===========================================================================
def parse_runs_ddl_columns(sql_text: str) -> dict[str, dict[str, bool]]:
    """Parse the ``runs`` table body into ``{col: {not_null, has_default, is_pk}}``.

    Handles nested parens (CHECK(...) constraints) by balanced-paren matching and
    splits column definitions on top-level commas only.
    """
    # Strip line comments first: a trailing ``-- ...`` bleeds into the next
    # comma-split segment (and its parens skew depth tracking). Cut each line at
    # its first ``--`` before any structural parsing.
    sql_text = "\n".join(re.split(r"--", ln, maxsplit=1)[0] for ln in sql_text.splitlines())

    m = re.search(r"CREATE TABLE IF NOT EXISTS\s+runs\s*\(", sql_text, re.IGNORECASE)
    if not m:
        raise CheckInfraError("could not locate `CREATE TABLE ... runs (` in init.sql")

    # Balanced-paren scan from the opening '(' of the column list.
    start = m.end() - 1
    depth = 0
    end = None
    for i in range(start, len(sql_text)):
        ch = sql_text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end is None:
        raise CheckInfraError("unbalanced parens in runs table DDL")
    body = sql_text[start + 1 : end]

    # Split on top-level commas (ignore commas inside nested parens).
    parts: list[str] = []
    depth = 0
    buf: list[str] = []
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))

    _table_constraint = re.compile(
        r"^(CONSTRAINT|PRIMARY|FOREIGN|UNIQUE|CHECK)\b", re.IGNORECASE
    )
    columns: dict[str, dict[str, bool]] = {}
    for raw in parts:
        line = raw.strip()
        if not line or line.startswith("--"):
            continue
        # Drop trailing inline comments so keyword scans stay clean.
        line = re.split(r"--", line, maxsplit=1)[0].strip()
        if not line or _table_constraint.match(line):
            continue
        col = line.split()[0]
        upper = line.upper()
        columns[col] = {
            "not_null": "NOT NULL" in upper or "PRIMARY KEY" in upper,
            "has_default": "DEFAULT" in upper,
            "is_pk": "PRIMARY KEY" in upper,
        }
    if not columns:
        raise CheckInfraError("parsed zero columns from runs DDL")
    return columns


def parse_runs_cols(source: str) -> tuple[str, ...]:
    """Extract the ``_RUNS_COLS`` tuple literal from runs_writer.py via ``ast``."""
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_RUNS_COLS":
                    value = node.value
                    if isinstance(value, (ast.Tuple, ast.List)):
                        cols = [
                            elt.value
                            for elt in value.elts
                            if isinstance(elt, ast.Constant)
                            and isinstance(elt.value, str)
                        ]
                        return tuple(cols)
    raise CheckInfraError("could not find `_RUNS_COLS` tuple in runs_writer.py")


def check_ddl_column_alignment() -> None:
    """Assert runs DDL columns and db_writer `_RUNS_COLS` agree; raise on drift."""
    if not INIT_SQL.exists():
        raise CheckInfraError(f"init.sql not found: {INIT_SQL}")
    if not RUNS_WRITER.exists():
        raise CheckInfraError(f"runs_writer.py not found: {RUNS_WRITER}")

    ddl_columns = parse_runs_ddl_columns(INIT_SQL.read_text())
    runs_cols = parse_runs_cols(RUNS_WRITER.read_text())
    ddl_names = set(ddl_columns)
    writer_names = set(runs_cols)

    problems: list[str] = []
    # (1) Every writer column must exist as a real DDL column.
    for col in runs_cols:
        if col not in ddl_names:
            problems.append(
                f"  db_writer inserts `{col}` but the runs DDL has no such column"
            )
    # (2) Every required (NOT NULL, no DEFAULT) DDL column must be supplied.
    for col, meta in ddl_columns.items():
        required = (meta["not_null"] or meta["is_pk"]) and not meta["has_default"]
        if required and col not in writer_names:
            problems.append(
                f"  runs DDL column `{col}` is NOT NULL without DEFAULT but "
                "db_writer._RUNS_COLS never supplies it"
            )

    if problems:
        raise DriftError(
            "runs DDL / db_writer._RUNS_COLS drift:\n"
            + "\n".join(problems)
            + f"\n  DDL columns:      {sorted(ddl_names)}"
            + f"\n  db_writer columns: {list(runs_cols)}"
            + "\n  fix: align the init.sql `runs` table and db_writer._RUNS_COLS"
        )
    print("[OK] DDL: runs table columns align with db_writer._RUNS_COLS")


# ===========================================================================
# Check C — data_source literals vs the DataSource enum
# ===========================================================================
def datasource_members(envelope_src: str) -> dict[str, str]:
    """Extract the ``DataSource`` enum's ``{MEMBER_NAME: "value"}`` map via ``ast``."""
    tree = ast.parse(envelope_src)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "DataSource":
            members: dict[str, str] = {}
            for stmt in node.body:
                if (
                    isinstance(stmt, ast.Assign)
                    and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and isinstance(stmt.value, ast.Constant)
                    and isinstance(stmt.value.value, str)
                ):
                    members[stmt.targets[0].id] = stmt.value.value
            if not members:
                raise CheckInfraError("DataSource enum has no string members")
            return members
    raise CheckInfraError("could not find the `DataSource` enum in envelope.py")


def scan_data_source_literals(py_src: str, members: dict[str, str]) -> list[str]:
    """Return problems for every ``{"data_source": <value>}`` in one module.

    Legal values: a ``DataSource.<MEMBER>`` reference, or a string equal to a member
    value. Anything else (a bare unknown string, a re-introduced private constant
    Name) is drift.
    """
    tree = ast.parse(py_src)
    names = set(members)
    values = set(members.values())
    problems: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values):
            if not (isinstance(key, ast.Constant) and key.value == "data_source"):
                continue
            if (
                isinstance(value, ast.Attribute)
                and isinstance(value.value, ast.Name)
                and value.value.id == "DataSource"
            ):
                if value.attr not in names:
                    problems.append(f"line {value.lineno}: DataSource.{value.attr} is not a member")
            elif isinstance(value, ast.Constant) and isinstance(value.value, str):
                if value.value not in values:
                    problems.append(
                        f'line {value.lineno}: "{value.value}" is not a DataSource value '
                        f"(use one of {sorted(values)})"
                    )
            else:
                problems.append(
                    f"line {getattr(value, 'lineno', '?')}: non-canonical data_source value — "
                    "must be a DataSource member (kills the uncoordinated-literal sprawl, A1)"
                )
    return problems


def check_data_source_literals() -> None:
    """Assert every ``data_source`` assignment is a DataSource member; raise on drift."""
    if not ENVELOPE_PY.exists():
        raise CheckInfraError(f"envelope.py not found: {ENVELOPE_PY}")
    if not ROUTERS_DIR.exists():
        raise CheckInfraError(f"routers dir not found: {ROUTERS_DIR}")
    members = datasource_members(ENVELOPE_PY.read_text(encoding="utf-8"))
    files = [ENVELOPE_PY, *sorted(ROUTERS_DIR.glob("*.py"))]
    problems: list[str] = []
    for path in files:
        for msg in scan_data_source_literals(path.read_text(encoding="utf-8"), members):
            problems.append(f"  {path.relative_to(BACKEND_DIR)}: {msg}")
    if problems:
        raise DriftError(
            "data_source literal drift: a value is not a DataSource enum member\n"
            + "\n".join(problems)
            + "\n  fix: add the token to `api/envelope.py::DataSource` or use an existing member"
        )
    print(f"[OK] data_source: every literal is a DataSource member ({len(members)} tokens)")


# ===========================================================================
# Driver
# ===========================================================================
def main() -> int:
    checks = (
        ("OpenAPI drift", check_openapi_drift),
        ("runs DDL alignment", check_ddl_column_alignment),
        ("data_source literals", check_data_source_literals),
    )
    drift_found = False
    infra_error = False
    for name, fn in checks:
        try:
            fn()
        except DriftError as exc:
            drift_found = True
            print(f"[DRIFT] {name}:\n{exc}", file=sys.stderr)
        except CheckInfraError as exc:
            infra_error = True
            print(f"[ERROR] {name} could not run: {exc}", file=sys.stderr)

    if drift_found:
        print("\nContract drift detected — see [DRIFT] blocks above.", file=sys.stderr)
        return 1
    if infra_error:
        print("\nA check could not run — see [ERROR] blocks above.", file=sys.stderr)
        return 2
    print("\nAll contract checks passed — no drift.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
