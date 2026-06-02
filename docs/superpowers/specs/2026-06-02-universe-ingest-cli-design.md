# 5.A.7.b — Universe Ingest CLI + Runbook 設計

> **狀態：** Draft（待使用者核准）
> **日期：** 2026-06-02
> **WBS：** 5.A.7.b（解 R14）| **分支：** `feat/universe-ingest-cli`
> **相關：** [[16_wbs_development_plan]] §5.A.7 / §5 R14、PR #15（`ingest_universe` helper）

---

## 1. 目標（Goal）

讓 `DEFAULT_UNIVERSE` 9 檔（2317/2454/1101/3008/2882/1303/2412/2308/2891 + 既有 2330）的
**5 年（2020-01-01 → 2024-12-31）日線** 能以**單一可重現指令**抓進 parquet cache，並**實際執行**
產出 cache → 解開 `cross_check_vectorbt` / portfolio 的 skip，正式關閉致命風險 **R14**。

非目標（YAGNI，明確排除）：
- ❌ 不寫 zipline native bundle ingest 流程（`zipline ingest -b finmind` 由 bundle callback 已涵蓋）
- ❌ 不把 parquet 入版控（`.gitignore` 已排除 `data/parquet/` + `*.parquet`）
- ❌ 不加 Makefile（專案目前無 Makefile，單一 target 屬 over-engineering）
- ❌ 不做 FinLab bundle（M3 規劃，3.B.x）

## 2. 背景與現況（既有可重用資產）

| 資產 | 位置 | 重用方式 |
|:--|:--|:--|
| `ingest_universe(universe, *, start, end, cache_dir)` | `bundles/finmind_bundle.py` | CLI 直接呼叫；per-symbol 隔離 + all-fail raise 已實作 |
| `DEFAULT_UNIVERSE` (10 檔 tuple) | 同上 | 預設 universe |
| `cached_or_fetch` → `fetch_bundle` → `write_parquet` | `bundles/parquet_cache.py` + `data/finmind_etl.py` | 抓取 + 寫 parquet 既有路徑 |
| `cli()` Click group（`backtest-run` / `list-bundles`） | `engines/zipline_adapter/cli.py` | 新 `ingest` 子命令掛同一 group |
| CLI 測試（`CliRunner` + `patch`） | `tests/engines/zipline_adapter/test_cli.py` | 延用 pattern |

**關鍵事實：** FinMind token 已驗證可用（2330 真實資料回傳 200）、本機可連 FinMind API。
因此本任務的執行階段（Phase 3）**包含實跑 live ingest**，非僅交付工具。

## 3. 架構與元件

### 3.1 新增 `ingest` CLI 子命令（`cli.py`）

```
uv run python -m backtest_platform.engines.zipline_adapter.cli ingest \
    --start 2020-01-01 --end 2024-12-31
```

| Option | 預設 | 說明 |
|:--|:--|:--|
| `--start` / `--end` | required | ISO date；回測資料窗口 |
| `--stocks` | None → `DEFAULT_UNIVERSE` | 逗號分隔覆蓋（如 `2330,2454`） |
| `--cache-dir` | None → `data/parquet` | parquet 落地目錄 |
| `--dry-run/--no-dry-run` | False | 只印「將抓哪些 symbol / 範圍」，不呼叫 FinMind，exit 0 |

**控制流：**
1. resolve universe：`--stocks` 拆逗號，否則 `list(DEFAULT_UNIVERSE)`
2. `--dry-run`：印 universe + 範圍 + cache dir，`return`（exit 0）
3. 呼叫 `ingest_universe(universe, start=..., end=..., cache_dir=...)`
4. `except RuntimeError`（全失敗）：`click.echo(err, err=True)` + `sys.exit(1)`
5. 成功：印 summary — `ok=N failed=[...] cache_dir=...`；若 `failed_symbols` 非空，
   印警告但 exit 0（部分成功仍可做 partial-universe 回測，符合 helper 契約）

**錯誤處理：** per-symbol 隔離邏輯在 helper（單一來源），CLI 只負責呈現與 exit code 對映。

### 3.2 Runbook 文件

`dev_docs/runbooks/m2_universe_ingest_runbook.md` — 內容：
1. 前置：FinMind token 取得 + 寫入**gitignored** `backtest_platform/.env`（`FINMIND_TOKEN=...`）
2. 執行指令（dry-run 先驗證 → 正式跑）
3. 驗證：`ls data/parquet/*.parquet` 應有 10 檔 + `list-bundles` 確認
4. Troubleshoot：rate limit（FinMind 免費版）、部分 symbol 失敗重跑、cache 命中規則
5. 安全提醒：token 只進 `.env`，不入版控；疑似外洩即輪換

### 3.3 執行階段（Phase 3 實跑）

寫 `FINMIND_TOKEN` 進 `backtest_platform/.env`（gitignored）→ 跑 ingest →
驗證 10 檔 parquet → 解 `test_cross_check_vectorbt` 的 `pytest.skip`（2330 cache 現已存在）。

## 4. 資料流

```
CLI ingest
  └─ ingest_universe(DEFAULT_UNIVERSE, start, end, cache_dir)
       └─ for symbol: cached_or_fetch(symbol, start, end, cache)
            ├─ cache hit (range 涵蓋) → 回傳，不打 API
            └─ miss → fetch_bundle(symbol) [FinMind API] → write_parquet → data/parquet/<symbol>.parquet
  └─ UniverseIngestResult{bundles, failed_symbols} → summary 印出
```

## 5. 測試策略（TDD，mock 不打網路）

| 測試 | 驗證 | 手法 |
|:--|:--|:--|
| `test_ingest_dry_run_lists_universe` | dry-run 印出 10 檔（DEFAULT_UNIVERSE 含 2330）、不呼叫 `ingest_universe` | `patch` 確認 helper 未被呼叫 |
| `test_ingest_default_universe_invokes_helper` | 無 `--stocks` → 用 `DEFAULT_UNIVERSE` | `patch ingest_universe` 斷言 args |
| `test_ingest_stocks_override` | `--stocks 2330,2454` → universe 覆蓋 | 斷言傳入 list |
| `test_ingest_all_fail_exits_nonzero` | helper raise `RuntimeError` → exit code 1 | `patch` side_effect=RuntimeError |
| `test_ingest_partial_failure_warns_exit_zero` | `failed_symbols` 非空 → exit 0 + 警告 | `patch` 回傳含 failed |

CI 維持全 mock（不打 FinMind）。live ingest 屬 Phase 3 一次性 acceptance，不入 CI。

## 6. 文件同步（code-doc-sync 觸發表）

| 觸發 | 文件 | 動作 |
|:--|:--|:--|
| 新 CLI 子命令 | `06_api_design.md` | 加 `ingest` 子命令條目 |
| 新 CLI 子命令 | `backtest_platform/README.md` | 加用法 |
| 新 runbook | `dev_docs/runbooks/m2_universe_ingest_runbook.md` | 新建 |
| 任務狀態 | `16_wbs_development_plan.md` | 5.A.7.b ✅ + R14 關閉 + 模組 5.0 進度 + Sprint 3 |

## 7. 驗收條件

- [ ] 5 個 mock 測試全綠，coverage 不低於 gate 80
- [ ] `ingest --dry-run` 正確列出 universe
- [ ] live 跑完 `data/parquet/` 有 10 檔（2330 + 9 新）
- [ ] `test_cross_check_vectorbt` 解 skip 後通過（或標記 portfolio 待 5.A.6）
- [ ] 06 / README / runbook / 16 WBS 同步
- [ ] token 僅存在 gitignored `.env`，diff 無秘密
