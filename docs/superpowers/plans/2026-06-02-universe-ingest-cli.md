# Universe Ingest CLI Implementation Plan

> **For agentic workers:** Use the Execute Plan phase of sunnydata-design to implement task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add an `ingest` CLI subcommand that batch-ingests `DEFAULT_UNIVERSE` into the parquet cache, then run it live to close R14.

**Architecture:** Thin Click command on the existing `cli()` group delegating to the already-merged `ingest_universe` helper; per-symbol isolation lives in the helper, the CLI only maps results → console output + exit code. Live run + runbook + doc sync follow.

**Tech Stack:** Click, pytest + `CliRunner`, FinMind ETL (existing), zipline-reloaded parquet cache.

---

## Task 1: `ingest` CLI subcommand (TDD)

**Files:**
- Modify: `backtest_platform/src/backtest_platform/engines/zipline_adapter/cli.py` (add command after `list_bundles`, ~line 266)
- Test: `backtest_platform/tests/engines/zipline_adapter/test_cli.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `test_cli.py`:

```python
# --------------------------------------------------------------------------- #
# ingest command
# --------------------------------------------------------------------------- #
_FB = "backtest_platform.engines.zipline_adapter.bundles.finmind_bundle"


def test_ingest_dry_run_lists_universe_without_calling_helper():
    runner = CliRunner()
    with patch(f"{_FB}.ingest_universe") as m:
        res = runner.invoke(
            cli_mod.cli,
            ["ingest", "--start", "2020-01-01", "--end", "2024-12-31", "--dry-run"],
        )
    assert res.exit_code == 0
    m.assert_not_called()
    assert "2330" in res.output and "2891" in res.output  # first + last default


def test_ingest_default_universe_invokes_helper():
    from backtest_platform.engines.zipline_adapter.bundles.finmind_bundle import (
        DEFAULT_UNIVERSE,
        UniverseIngestResult,
    )

    runner = CliRunner()
    with patch(f"{_FB}.ingest_universe") as m:
        m.return_value = UniverseIngestResult(
            bundles={s: MagicMock() for s in DEFAULT_UNIVERSE}, failed_symbols=[]
        )
        res = runner.invoke(
            cli_mod.cli, ["ingest", "--start", "2020-01-01", "--end", "2024-12-31"]
        )
    assert res.exit_code == 0
    universe_arg = m.call_args.args[0]
    assert universe_arg == list(DEFAULT_UNIVERSE)


def test_ingest_stocks_override():
    from backtest_platform.engines.zipline_adapter.bundles.finmind_bundle import (
        UniverseIngestResult,
    )

    runner = CliRunner()
    with patch(f"{_FB}.ingest_universe") as m:
        m.return_value = UniverseIngestResult(
            bundles={"2330": MagicMock(), "2454": MagicMock()}, failed_symbols=[]
        )
        res = runner.invoke(
            cli_mod.cli,
            ["ingest", "--start", "2020-01-01", "--end", "2024-12-31",
             "--stocks", "2330,2454"],
        )
    assert res.exit_code == 0
    assert m.call_args.args[0] == ["2330", "2454"]


def test_ingest_all_fail_exits_nonzero():
    runner = CliRunner()
    with patch(f"{_FB}.ingest_universe", side_effect=RuntimeError("all failed")):
        res = runner.invoke(
            cli_mod.cli, ["ingest", "--start", "2020-01-01", "--end", "2024-12-31"]
        )
    assert res.exit_code == 1
    assert "failed" in res.output.lower()


def test_ingest_partial_failure_warns_exit_zero():
    from backtest_platform.engines.zipline_adapter.bundles.finmind_bundle import (
        UniverseIngestResult,
    )

    runner = CliRunner()
    with patch(f"{_FB}.ingest_universe") as m:
        m.return_value = UniverseIngestResult(
            bundles={"2330": MagicMock()}, failed_symbols=["9999"]
        )
        res = runner.invoke(
            cli_mod.cli,
            ["ingest", "--start", "2020-01-01", "--end", "2024-12-31",
             "--stocks", "2330,9999"],
        )
    assert res.exit_code == 0
    assert "9999" in res.output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backtest_platform && uv run pytest tests/engines/zipline_adapter/test_cli.py -k ingest -v`
Expected: FAIL — `No such command 'ingest'`

- [ ] **Step 3: Implement the command**

Insert in `cli.py` between `list_bundles` and the `if __name__` guard:

```python
@cli.command("ingest")
@click.option("--start", required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option("--end", required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option(
    "--stocks",
    default=None,
    help="Comma-separated override; default = DEFAULT_UNIVERSE (10 檔)",
)
@click.option(
    "--cache-dir",
    default=None,
    type=click.Path(path_type=Path),
    help="parquet cache dir (default: data/parquet)",
)
@click.option("--dry-run/--no-dry-run", default=False, show_default=True)
def ingest(
    start: datetime,
    end: datetime,
    stocks: str | None,
    cache_dir: Path | None,
    dry_run: bool,
) -> None:
    """Batch-ingest a universe into the parquet cache (FinMind → parquet).

    Example:
        ingest --start 2020-01-01 --end 2024-12-31
    """
    from backtest_platform.engines.zipline_adapter.bundles import finmind_bundle

    universe = (
        [s.strip() for s in stocks.split(",") if s.strip()]
        if stocks
        else list(finmind_bundle.DEFAULT_UNIVERSE)
    )

    if dry_run:
        click.echo(
            f"[dry-run] would ingest {len(universe)} symbols "
            f"{start.date()}..{end.date()}"
        )
        for sym in universe:
            click.echo(f"  - {sym}")
        click.echo(f"cache_dir = {cache_dir or 'data/parquet (default)'}")
        return

    try:
        result = finmind_bundle.ingest_universe(
            universe, start=start.date(), end=end.date(), cache_dir=cache_dir
        )
    except RuntimeError as exc:
        click.echo(f"ingest failed — every symbol failed: {exc}", err=True)
        sys.exit(1)

    click.echo("\n=== Ingest Summary ===")
    click.echo(f"ok     : {len(result.bundles)} / {len(universe)}")
    if result.failed_symbols:
        click.echo(f"failed : {result.failed_symbols}")
    click.echo(f"cache  : {cache_dir or 'data/parquet'}")
```

Note: import via module (`finmind_bundle.ingest_universe`) so tests patching
`...finmind_bundle.ingest_universe` intercept the call.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backtest_platform && uv run pytest tests/engines/zipline_adapter/test_cli.py -k ingest -v`
Expected: 5 passed

- [ ] **Step 5: Run full suite + coverage gate**

Run: `cd backtest_platform && uv run pytest -q`
Expected: all pass, `--cov-fail-under=80` holds

- [ ] **Step 6: Commit**

```bash
git add backtest_platform/src/backtest_platform/engines/zipline_adapter/cli.py \
        backtest_platform/tests/engines/zipline_adapter/test_cli.py
git commit -F - <<'MSG'
feat(cli): add `ingest` subcommand for universe parquet pre-population

WHY: R14 — no reproducible way to populate the parquet cache for the
DEFAULT_UNIVERSE without running a full backtest. The ingest_universe
helper (PR #15) had no CLI entry point.

WHAT: thin Click command delegating to ingest_universe; per-symbol
isolation stays in the helper. All-fail → exit 1; partial → exit 0 +
warning. --dry-run lists the universe without hitting FinMind.

IMPACT: engines/zipline_adapter/cli.py + tests. Unblocks the live ingest
that closes R14.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
MSG
```

---

## Task 2: Runbook doc

**Files:**
- Create: `dev_docs/runbooks/m2_universe_ingest_runbook.md`

- [ ] **Step 1: Write the runbook**

```markdown
# Runbook — M2 Universe Ingest（5.A.7.b）

> 目的：把 `DEFAULT_UNIVERSE` 10 檔（含 2330）2020-2024 日線抓進本地 parquet cache。
> cache **不入版控**（`.gitignore` 已排除 `data/parquet/` + `*.parquet`）。

## 1. 前置：FinMind token

1. 到 https://finmindtrade.com 註冊取得 API token
2. 寫入 **gitignored** `backtest_platform/.env`（絕不入版控）：
   ```
   FINMIND_TOKEN=<你的 token>
   ```
3. 確認 `.env` 被忽略：`git check-ignore backtest_platform/.env` 應回傳該路徑

## 2. 執行

```bash
cd backtest_platform
# 先 dry-run 驗證 universe / 範圍
uv run python -m backtest_platform.engines.zipline_adapter.cli ingest \
    --start 2020-01-01 --end 2024-12-31 --dry-run
# 正式跑
uv run python -m backtest_platform.engines.zipline_adapter.cli ingest \
    --start 2020-01-01 --end 2024-12-31
```

## 3. 驗證

```bash
ls -1 data/parquet/*.parquet | wc -l   # 預期 10
uv run python -m backtest_platform.engines.zipline_adapter.cli list-bundles
```

## 4. Troubleshoot

| 症狀 | 處理 |
|:--|:--|
| 部分 symbol failed | 重跑同指令；cache 命中已成功的，只補失敗的（FinMind 5xx 多為暫時性） |
| 全失敗 exit 1 | 檢查 `FINMIND_TOKEN` 是否設、是否超過免費版流量 |
| cache 沒更新 | range 已被既有 cache 涵蓋即命中不重抓；刪對應 `data/parquet/<id>.parquet` 強制重抓 |

## 5. 安全

- token 只進 `backtest_platform/.env`（gitignored）
- 疑似外洩（貼到聊天 / log / PR）即到 FinMind 後台輪換
```

- [ ] **Step 2: Commit**

```bash
git add dev_docs/runbooks/m2_universe_ingest_runbook.md
git commit -m "docs(runbook): add M2 universe ingest runbook (5.A.7.b)"
```

---

## Task 3: Doc sync (06 / README / 16 WBS)

**Files:**
- Modify: `dev_docs/06_api_design.md` (add `ingest` to CLI section)
- Modify: `backtest_platform/README.md` (add usage)
- Modify: `dev_docs/16_wbs_development_plan.md` (5.A.7.b status + R14)

- [ ] **Step 1: Update 06_api_design.md** — locate the zipline_adapter CLI command list, add an `ingest` row mirroring `backtest-run` style (options + one-line purpose). Cross-ref the runbook.

- [ ] **Step 2: Update README.md** — under CLI usage, add the `ingest` one-liner + link to runbook.

- [ ] **Step 3: Update 16 WBS** (after live run in Task 4; do final status flip there). Here just stage the structural edits: `5.A.7.b` row, R14 row.

- [ ] **Step 4: Commit** (fold into Task 4's commit if status depends on live run; otherwise commit docs now).

---

## Task 4: Live ingest run + close R14

**Files:**
- Create (gitignored, NOT committed): `backtest_platform/.env`
- Produces (gitignored): `backtest_platform/data/parquet/*.parquet`
- Modify: `backtest_platform/tests/engines/zipline_adapter/validation/test_cross_check_vectorbt.py` (un-skip if cache now present)
- Modify: `dev_docs/16_wbs_development_plan.md` (flip 5.A.7.b ✅, R14 closed)

- [ ] **Step 1: Write token to gitignored .env**

```bash
cd backtest_platform
printf 'FINMIND_TOKEN=%s\n' "$FINMIND_TOKEN_VALUE" >> .env   # value passed inline, never echoed to log
git check-ignore .env   # MUST print .env
```

- [ ] **Step 2: Dry-run then live ingest**

```bash
cd backtest_platform
uv run python -m backtest_platform.engines.zipline_adapter.cli ingest \
    --start 2020-01-01 --end 2024-12-31 --dry-run
uv run python -m backtest_platform.engines.zipline_adapter.cli ingest \
    --start 2020-01-01 --end 2024-12-31
```
Expected: `ok : 10 / 10` (or note any failed symbol for retry)

- [ ] **Step 3: Verify cache**

```bash
ls -1 backtest_platform/data/parquet/*.parquet | wc -l   # expect 10
```

- [ ] **Step 4: Un-skip cross-check test (if cache present)**

`test_cross_check_vectorbt.py:32` currently `pytest.skip("2330 parquet cache missing")`.
With the cache now present, run it: `uv run pytest tests/engines/zipline_adapter/validation/test_cross_check_vectorbt.py -v`.
If it passes against live cache, keep the skip guard (CI has no cache) but confirm it runs locally. Do NOT hard-remove the guard — CI still lacks the cache. Record the local PASS in the WBS.

- [ ] **Step 5: Update 16 WBS** — flip `5.A.7.b` → ✅ with date, mark R14 closed/mitigated, bump module 5.0 progress, update Sprint 3 row + overall %.

- [ ] **Step 6: Verify diff carries no secret**

```bash
git diff --cached | grep -i "FINMIND_TOKEN\|eyJ" && echo "SECRET LEAK — abort" || echo "clean"
git status   # .env must NOT appear
```

- [ ] **Step 7: Commit** (WBS + test changes only; never .env/parquet)

```bash
git add dev_docs/16_wbs_development_plan.md \
        backtest_platform/tests/engines/zipline_adapter/validation/test_cross_check_vectorbt.py
git commit -m "docs(wbs): close R14 — live universe ingest done, 10/10 parquet cached"
```

---

## Plan Self-Review

- **Spec coverage:** §3.1 CLI → Task 1; §3.2 runbook → Task 2; §3.3 live run → Task 4; §5 tests → Task 1; §6 doc sync → Task 3 + 4. ✓
- **Placeholder scan:** every code step has real code; no TBD. ✓
- **Type consistency:** `UniverseIngestResult{bundles, failed_symbols}`, `ingest_universe(universe, *, start, end, cache_dir)` (start/end = `date`), `start.date()` from Click `DateTime`. Matches `finmind_bundle.py`. ✓
- **Secret handling:** token only in gitignored `.env`; Step 6 leak-check before commit. ✓
