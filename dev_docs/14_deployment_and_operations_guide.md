# 部署與運維指南 — backtest_platform

> **版本：** v2.0 | **更新：** 2026-07-02
> **部署假設：** 單機自託管、內網 localhost、單人（[02 PRD v4.0 §2.3](./02_project_brief_and_prd.md)、[ADR-031](./adrs/ADR-031-standalone-auth-decision.md)）。
> **關聯：** [23_deployment_topology.md](./23_deployment_topology.md)（拓撲）、[13_security_and_readiness_checklists.md](./13_security_and_readiness_checklists.md)（安全 / 備份）、[24_risk_management_spec.md](./24_risk_management_spec.md)（風控 SOP）。

本文是**現行單機部署與運維 SOP**：如何把整套跑起來、如何備份、出事怎麼查。企業級 scheduler / VPS / 藍綠部署不在範圍（standalone lite 原則，PRD v4.0 §5「不做什麼」）。

---

## 1. 部署架構（單機）

```
單台 PC（Linux / WSL2）
├── uv 管理的 Python 環境（backtest_platform 套件）
│   ├── FastAPI（uvicorn，綁 127.0.0.1:8000）
│   ├── research CLI（doe / truth-gate / build-universe / paper-replay …）
│   └── monitoring（Discord notifier + alert rules）
├── Node / Vite（前端：dev 走 5173、prod 出 static build）
└── Docker Compose
    ├── TimescaleDB          :5432   ← 必要（telemetry + runs + bundle cache）
    ├── InfluxDB 2.7         :8086   ← M4 選配（系統 metrics）
    └── Grafana 10.4         :3000   ← M4 選配（系統面板）
```

| 元件 | 用途 | 技術 |
| :--- | :--- | :--- |
| 後端 API | REST 契約（端點 registry 見 25 §6）| FastAPI + uvicorn |
| 前端 | React 三 zone GUI | Vite + React 19（build → static）|
| 資料庫 | telemetry / runs / bundle cache | TimescaleDB 2.14.2-pg16 |
| 系統 metrics（選配）| ETL / quota / 排程健康面板 | InfluxDB 2.7 + Grafana 10.4 |
| 告警 | 退化 / 風控推播 | Discord（`monitoring/`，httpx REST，ADR-010）|
| 排程 | after-close 收 live OOS | cron / systemd timer（**下一步**，見 §3）|

> **排程器方向（PRD v4.0）**：個人 standalone 不需企業 scheduler；一條 cron / systemd timer + Discord 成敗通知即足。`docker-compose.yml` 已移除先前未使用的 `prefect-server` 殘留服務，排程方向確定為 cron/systemd。

---

## 2. 環境建置 SOP

### 2.1 後端 + 資料庫

```bash
cd backtest_platform

# 1. Python 環境（uv，ADR-012）
uv sync --all-extras            # 全 extras：api / dev / sprint1 / validation …

# 2. 秘密：複製並填入 .env（gitignored，絕不入版控）
cp .env.example .env
#   至少填 FINLAB_API_TOKEN（主資料源）、POSTGRES_PASSWORD（改掉預設值）、DISCORD_*（告警）

# 3. TimescaleDB（init.sql 於首次啟動自動建 13 張表）
docker compose up -d timescaledb
docker compose ps              # 確認 quant-timescaledb healthy

# 4. 啟動 API（standalone MUST 綁 loopback，ADR-031）
uv run uvicorn backtest_platform.api.app:app --host 127.0.0.1 --port 8000
#   OpenAPI 文件：http://127.0.0.1:8000/docs
```

### 2.2 前端

```bash
cd frontend
npm ci

# dev：vite proxy 把 /runs /research /monitor /system /home 等前綴代理到 127.0.0.1:8000
npm run dev                    # http://localhost:5173

# prod：靜態 build（以任意 static server / uvicorn 掛載 dist/ 提供）
npm run build                  # tsc --noEmit && vite build → dist/
```

> 契約型別由 OpenAPI 生成：後端 `app.openapi()` → `frontend/openapi.json` → `npm run gen:api`。CI `contract-drift` job 硬 gate 兩者一致（見 §5）。

### 2.3 系統面板（M4 選配）

```bash
docker compose up -d influxdb grafana
#   Grafana http://localhost:3000（provisioning 自動載入 4 個系統面板：ETL / quota / 排程 / 資源）
#   資料來源對齊 monitoring/influx_writer.py emit 的 measurements（見 20 §Grafana）
```

---

## 3. 排程（after-close，收 live OOS）

收 live OOS 的最後一塊——after-close 排程器（審查缺陷 #17）——已落地為 **cron / systemd timer 級**（不用企業 scheduler，對齊 PRD v4.0）。CLI 入口 `orchestration.cli after-close` 自帶三道守門，週末 / 假日 / 未到收盤 / 重複觸發都是乾淨 no-op（exit 0）；唯有 daily flow 失敗才 exit 1 並推 Discord 告警。

### 3.1 CLI 入口

```bash
# 今日盤後跑一次（預設 --date = 今日 Asia/Taipei）
uv run python -m backtest_platform.orchestration.cli \
    after-close --strategy inst_flow --universe 2330,2317,2454

# 補跑某個交易日（back-fill；過去日期自動視為已收盤）
uv run python -m backtest_platform.orchestration.cli \
    after-close --strategy inst_flow --date 2026-07-01 --universe 2330,2317

# 煙霧測試：過守門但不觸發 daily flow（不碰 finlab / DB）
uv run python -m backtest_platform.orchestration.cli \
    after-close --strategy inst_flow --dry-run --force
```

守門順序與行為：

| 守門 | 判準 | 未過 → | exit |
| :--- | :--- | :--- | :--- |
| 交易日 | XTAI 日曆（裝 `--extra mainframe`）；否則週一至五近似 | `NON_TRADING_DAY` no-op | 0 |
| 收盤後 | 台北時區 ≥ 14:30（過去日期自動過；`--force` 跳過）| `TOO_EARLY` 拒跑 | 0 |
| 冪等 | 同 (strategy, date) 已成功 → done-marker JSONL | `ALREADY_DONE` skip | 0 |
| daily flow | 走既有 live-panel forward 鏈（`market_reader.live_config_for_date` → `run_forward_session`）| `FAILED` 推 Discord 告警 | **1** |

> **日曆限制**：未裝 `mainframe` extra 時退化為週一至五近似——落在平日的國定 / 農曆假日會被誤判為交易日（年約 10–15 天）。裝 `uv sync --extra mainframe` 取得精確 XTAI sessions；冪等 + 風控仍限縮誤觸發的爆炸半徑。
>
> **收盤時間校準**：14:30 是台股 13:30 收盤後的 EOD 資料緩衝；若你的資料源較晚才發布三大法人 net-buy，把 timer 與 gate 一併後移（如 17:35）。
>
> **portfolio 狀態限制**：每次 CLI process 起一個全新 `PaperBroker`；每日 signals / fills / equity 皆經 sink 落庫，但跨日的 in-process 倉位尚未從 DB 回填（屬 db hardening 工作包）。足以觀察每日 live 訊號。

### 3.2 安裝（systemd user timer，建議）

`deploy/` 附完整範例（`after-close.service` / `after-close.timer` / `after-close.cron.example` / `README.md`）。

```bash
mkdir -p ~/.config/systemd/user
cp backtest_platform/deploy/after-close.{service,timer} ~/.config/systemd/user/
# 編輯 .service 的 WorkingDirectory / EnvironmentFile / --universe 成你的路徑
systemctl --user daemon-reload
systemctl --user enable --now after-close.timer
loginctl enable-linger "$USER"                    # 登出後 timer 續跑
systemctl --user list-timers after-close.timer    # 確認下次觸發
journalctl --user -u after-close.service -n 50     # 看最近一次結果
```

Timer：`OnCalendar=Mon..Fri 14:35 Asia/Taipei` + `Persistent=true`（補跑睡眠中錯過的觸發，冪等擋雙跑）。cron 替代方案見 `deploy/after-close.cron.example`（cron 無時區，假設 host 為 Asia/Taipei）。service 讀 `.env`（`FINLAB_API_TOKEN` / `POSTGRES_*` / `DISCORD_*`）。成功推 `INFO` digest、失敗推 `ERROR` 告警。

---

## 4. 備份與災難恢復

### 4.1 備份（單人不可再生資產，審查缺陷 #10）

三類不可再生資產：FinLab 付費 parquet cache、研究血統 `reports/*.jsonl`、TimescaleDB telemetry。

```bash
# 每日 TimescaleDB dump（cron 建議 02:00）
docker exec quant-timescaledb pg_dump -U quant -Fc quant_trading \
    > backups/quant_trading_$(date +%F).dump

# 付費資料 + 研究血統（rsync 到備份目錄 / 外接碟）
rsync -a data/parquet/ data/parquet_finlab_universe/ backups/parquet/
rsync -a reports/ backups/reports/
```

- **RPO**：24 小時（每日一次 dump）。**RTO**：< 1 小時（單機 restore）。
- parquet cache 已具原子寫回 + 缺口 merge（`parquet_cache.py`），舊歷史不被新 ingest 覆蓋。

### 4.2 恢復

```bash
# 資料庫恢復
docker exec -i quant-timescaledb pg_restore -U quant -d quant_trading --clean \
    < backups/quant_trading_YYYY-MM-DD.dump

# parquet / reports 恢復：反向 rsync
rsync -a backups/parquet/ data/parquet/
```

恢復演練（建議每季）：刪 1 日資料 → restore → 跑一次 `research truth-gate --strategy <s> --dry-run` smoke。

### 4.3 資料源中斷降級

| 失效 | Fallback | 通知 |
| :--- | :--- | :--- |
| FinLab API | 切 FinMind bundle ingest（`zipline_adapter cli ingest`）| Discord HIGH |
| TimescaleDB | 無 fallback，停 paper 鏈 | Discord CRITICAL |
| Discord | 寫本機 log（告警不阻塞主流程）| system log |

---

## 5. CI（品質守門，已上線）

`.github/workflows/ci.yml` 三 job，每次 push main / PR 觸發（詳見 [22 §CI](./22_test_strategy.md)）：

| Job | 內容 |
| :--- | :--- |
| **backend** | `uv sync --all-extras` → `uv run pytest`（coverage gate 80%）|
| **frontend** | `npm ci` → `tsc --noEmit` → `vitest run --coverage` |
| **contract-drift** | `scripts/check_openapi_drift.py`：OpenAPI live↔snapshot + runs DDL↔`_RUNS_COLS`（hard gate）|

---

## 6. 告警 Runbook（Discord）

告警經 `monitoring/`：`alert_rules.py`（決策層：三級規則 + 去重 + 靜默時段）+ `discord_notifier.py`（發送層：httpx REST embed）。等級與觸發規則見 [20 §Discord 告警規格](./20_dashboard_specification.md)。

```bash
# 測試 Discord 送達（後端須設 DISCORD_BOT_TOKEN 等）
curl -X POST http://127.0.0.1:8000/system/alerts/test
#   或看告警規則 catalog：GET /system/alerts/rules
```

| 等級 | 觸發類別 | 通知節奏 |
| :--- | :--- | :--- |
| **Critical** 🚨 | 熔斷觸發、下單失敗連 3、資料源全斷 | 即時（5 秒內）|
| **High** ⚠️ | ETL 失敗、訊號缺漏、部位偏離 > 5%、quota < 500MB | 5 分鐘內 |
| **Info** ℹ️ | 每日盤後績效 + 訊號 digest | 每日一次 |

去重：同 `rule_id` 30 分鐘內只發一次；靜默時段 22:00–08:00 只推 Critical（`alert_rules.py` `DEDUPE_WINDOW` / `SILENT_*`）。

---

## 7. 常見狀況 Runbook

### 7.1 FinLab / FinMind ingest 失敗

```bash
# FinLab（主）：確認 token 有效、quota 未爆
uv run python -c "from backtest_platform.data.finlab_source import login; login()"

# FinMind（fallback）：重跑同指令，cache 命中已成功的只補失敗的
uv run python -m backtest_platform.engines.zipline_adapter.cli ingest \
    --start <start> --end <end>
```
常見原因：token 過期 / quota 上限（等冷卻）、部分 symbol 5xx（重跑補抓）。詳見 [runbooks/m2_universe_ingest_runbook.md](./runbooks/m2_universe_ingest_runbook.md)。

### 7.2 TimescaleDB connection refused

```bash
docker compose ps                      # 確認 quant-timescaledb healthy
docker compose logs timescaledb | tail -50
docker compose restart timescaledb     # 重啟（資料在 named volume，不遺失）
```

### 7.3 API 起不來 / 前端打不到後端

- 確認 uvicorn 綁的是 `127.0.0.1:8000`，且 vite proxy target（`vite.config.ts` `API_TARGET`）指向同一位址。
- `contract-drift` 紅燈 → 後端 schema 變了但 `openapi.json` / `api.gen.ts` 未重生：`npm run gen:api` 後重跑。

### 7.4 判決異常（GUI 與 CLI truth-gate 不一致）

1. 確認 run 的 `strategy` 欄正確（gate 依策略 dispatch，非四層預設）。
2. 以 CLI 重跑 `research truth-gate --strategy <s>` 對照（審判庭真相源）。
3. 差異持續 → 走 [24 風控 SOP](./24_risk_management_spec.md) 排查。
