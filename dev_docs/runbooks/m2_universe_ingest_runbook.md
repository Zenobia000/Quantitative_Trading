# Runbook — Universe Ingest（雙路徑）

> 目的：把台股 universe 的日線 / 法人籌碼抓進本地 parquet cache，供回測 / truth-gate / paper-replay 消費。
> 兩條路徑共用同一 parquet schema（`daily_bars__ / institutional__ / broker_chips__` + `manifest.json`），下游（`load_merged_parquet` / 驗證 / replay）零差異。
> cache **不入版控**（`.gitignore` 已排除 `data/parquet*` + `*.parquet`）。
> 狀態真相源：[16 WBS](../16_wbs_development_plan.md)。

| 路徑 | 何時用 | 資料源 | 入口 |
| :--- | :--- | :--- | :--- |
| **A. FinLab 主（survivorship-clean）** | 建策略專屬乾淨 universe（含下市股，反 survivorship）| 付費 FinLab（ADR-006）| `research build-universe --strategy <name>`（ADR-032）|
| **B. FinMind fallback** | 快速抓固定 universe 日線（無 FinLab token 時）| 免費 FinMind | `zipline_adapter cli ingest`（ADR-013）|

---

## 路徑 A — FinLab survivorship-clean universe（主，ADR-032）

策略以 `strategies/<name>/research_config.py` 的 `UNIVERSE`（frozen `UniverseConfig`：span / top_n / min_turnover / cache_dir，季度 rebalance）宣告建構參數；工作流執行它。

### A.1 前置：FinLab token

```bash
# 取得：https://ai.finlab.tw 登入 → 個人資料 → API Token
# 寫入 gitignored backtest_platform/.env（絕不入版控）
#   FINLAB_API_TOKEN=<你的 token>
git check-ignore backtest_platform/.env    # 應回傳該路徑
```

### A.2 執行

```bash
cd backtest_platform

# 先 dry-run 驗證 span / top_n / cache_dir（不打 FinLab）
uv run python -m backtest_platform.research.cli build-universe \
    --strategy inst_flow --dry-run

# 正式跑：fetch FinLab 寬表 → 季度 PIT survivorship-clean 選股（含下市）
#         → ingest 專屬 parquet cache → 寫 universe_manifest.json
uv run python -m backtest_platform.research.cli build-universe --strategy inst_flow
```

預期輸出尾段：
```
  universe=<N> names  alive=<a> delisted=<d>
  ingest ok=<ok> failed=<f>
  → manifest data/parquet_finlab_universe/universe_manifest.json
```

- `cache_dir` 由 `UniverseConfig` 宣告（inst_flow 為 `data/parquet_finlab_universe`，survivorship-clean 快取）。
- `delisted > 0` 是**正確的**：下市股在其存活的季度被保留（反 survivorship）；全 alive 反而可疑。

### A.3 驗證 + 消費

```bash
# manifest = 可重現血統（params / symbols / n_alive / n_delisted / ingest ok·failed / generated_at）
cat data/parquet_finlab_universe/universe_manifest.json | head -40

# cache 就緒後，inst_flow 的 TRUTH_GATE 條件宣告 survivorship_clean=True 並讀該 cache
uv run python -m backtest_platform.research.cli truth-gate --strategy inst_flow
```

> **反自欺（ADR-030/032）**：`survivorship_clean` 跟著 cache 走——掃到乾淨料才宣告 True 並把 `parquet_dir` 指向該 cache；cache 缺席時退回 survivor-only fallback（`survivorship_clean=False`）。宣告、資料、判決三者對齊。

### A.4 HTTP 觸發（非同步）

```bash
# POST /research/workflows/build_universe → 202 {job_id, status}（經 jobs/ 非同步，25 §5.2）
curl -X POST http://127.0.0.1:8000/research/workflows/build_universe \
    -H 'Content-Type: application/json' -d '{"strategy":"inst_flow"}'
```

---

## 路徑 B — FinMind fallback（固定 universe 日線）

無 FinLab token 時的快速路徑；抓 `DEFAULT_UNIVERSE`（或 `--stocks` 覆蓋）到 `data/parquet`。

### B.1 前置：FinMind token

```bash
# 取得：https://finmindtrade.com 註冊
# 寫入 gitignored backtest_platform/.env
#   FINMIND_TOKEN=<你的 token>
```

### B.2 執行

```bash
cd backtest_platform

# dry-run（不打 FinMind）
uv run --extra sprint1 --extra dev python -m \
    backtest_platform.engines.zipline_adapter.cli ingest \
    --start 2020-01-01 --end 2024-12-31 --dry-run

# 正式跑
uv run --extra sprint1 --extra dev python -m \
    backtest_platform.engines.zipline_adapter.cli ingest \
    --start 2020-01-01 --end 2024-12-31
```

預期輸出尾段：
```
=== Ingest Summary ===
ok     : 10 / 10
cache  : data/parquet
```

可選 flag：`--stocks 2330,2454`（覆蓋 universe）、`--cache-dir <path>`（自訂落地目錄）。

### B.3 驗證

```bash
ls -1 backtest_platform/data/parquet/daily_bars__*.parquet | wc -l   # 預期 = universe 檔數
uv run --extra sprint1 --extra dev python -m \
    backtest_platform.engines.zipline_adapter.cli list-bundles
```

---

## Troubleshoot（共用）

| 症狀 | 處理 |
|:--|:--|
| 部分 symbol failed | 重跑同指令；cache 命中已成功的，只補失敗的（5xx 多為暫時性）|
| 全失敗 exit 1 | 檢查對應 token（`FINLAB_API_TOKEN` / `FINMIND_TOKEN`）是否設、是否超流量上限 |
| cache 沒更新 | range 已被既有 cache 涵蓋即命中不重抓；缺口 fetch+merge 為 day-incremental（不覆蓋歷史）|
| `ModuleNotFoundError: zipline` | 路徑 B 缺 extra；指令需帶 `--extra sprint1 --extra dev` |
| build-universe 報缺 `UNIVERSE` | 該策略 `research_config.py` 未宣告 `UniverseConfig`（僅資金流類需要）|

## 安全

- token 只進 `backtest_platform/.env`（gitignored），**絕不**進原始碼或 commit。
- 疑似外洩（貼到 chat / log / PR）即到對應後台輪換。
- 參見 [security 規範](../../.claude/rules/security.md) §秘密管理、[13 §B](../13_security_and_readiness_checklists.md)。
