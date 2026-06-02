# Runbook — M2 Universe Ingest（5.A.7.b）

> 目的：把 `DEFAULT_UNIVERSE` 10 檔（含 2330）2020-2024 日線抓進本地 parquet cache。
> cache **不入版控**（`.gitignore` 已排除 `data/parquet/` + `*.parquet`）。
> 狀態真相源：[16 WBS](../16_wbs_development_plan.md) §5.A.7。

## 1. 前置：FinMind token

1. 到 https://finmindtrade.com 註冊取得 API token
2. 寫入 **gitignored** `backtest_platform/.env`（絕不入版控）：
   ```
   FINMIND_TOKEN=<你的 token>
   ```
3. 確認 `.env` 被忽略：
   ```bash
   git check-ignore backtest_platform/.env   # 應回傳該路徑
   ```

## 2. 執行

```bash
cd backtest_platform
# 先 dry-run 驗證 universe / 範圍（不打 FinMind）
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

## 3. 驗證

```bash
ls -1 backtest_platform/data/parquet/*.parquet | wc -l   # 預期 10
uv run --extra sprint1 --extra dev python -m \
    backtest_platform.engines.zipline_adapter.cli list-bundles
```

cache 就緒後，下列原本 auto-skip 的驗證測試會自動執行：
```bash
uv run --extra sprint1 --extra dev pytest \
    tests/engines/zipline_adapter/validation/ -q
```

## 4. Troubleshoot

| 症狀 | 處理 |
|:--|:--|
| 部分 symbol failed | 重跑同指令；cache 命中已成功的，只補失敗的（FinMind 5xx 多為暫時性） |
| 全失敗 exit 1 | 檢查 `FINMIND_TOKEN` 是否設、是否超過免費版流量上限 |
| cache 沒更新 | range 已被既有 cache 涵蓋即命中不重抓；刪對應 `data/parquet/<id>.parquet` 強制重抓 |
| `ModuleNotFoundError: zipline` | 缺 extra；指令需帶 `--extra sprint1 --extra dev` |

## 5. 安全

- token 只進 `backtest_platform/.env`（gitignored），**絕不**進原始碼或 commit
- 疑似外洩（貼到聊天 / log / PR）即到 FinMind 後台輪換
- 參見 [security 規範](../../.claude/rules/security.md) §秘密管理
