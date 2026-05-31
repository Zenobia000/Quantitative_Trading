# 部署與運維指南 — backtest_platform

> **版本：** v1.0 | **更新：** 2026-05-26

---

## 1. 部署架構

> **2026-05-31 補註**：本節為高層概述。**完整三環境拓撲（Dev/Staging/Production）含 docker-compose 詳細草案、port mapping、secrets 管理、災難復原拓撲 → 詳見 [23_deployment_topology.md](./23_deployment_topology.md)**。
> 本文聚焦運維 SOP 與 Runbook；23 號文件聚焦拓撲與基礎設施設計。

### 當前（M1–M3：開發/回測階段）

```
本機 PC（Windows / WSL2）
    ├── Python venv（backtest_platform 套件）
    └── Docker Compose
            ├── TimescaleDB（資料）
            ├── Prefect（排程，M2 啟用）
            └── Grafana（監控，M4 啟用）
```

### M4 階段（Paper Trading）

```
本機 PC（持續開機 / 同上）
    ├── Prefect schedule（每日 17:00 ETL + 18:00 訊號生成）
    └── Grafana + Telegram bot
```

### M5 階段（小倉位實盤）

```
雲端 VPS（推薦 GCP Compute Engine e2-small）
    ├── Docker Compose（同上 + Shioaji 容器）
    ├── Prefect schedule
    ├── Grafana + Telegram bot
    └── 自動備份 → GCS / S3
```

### 基礎設施元件

| 元件 | 用途 | 技術選型 |
| :--- | :--- | :--- |
| 應用容器（M5） | backtest_platform 套件 | Docker (Python 3.11-slim) |
| 資料庫 | TimescaleDB | timescale/timescaledb:2.14.2-pg16 |
| 排程 | Prefect Server 2.x | prefecthq/prefect:2.19 |
| 監控 | Grafana | grafana/grafana:10.4.2 |
| 告警 | Telegram Bot | python-telegram-bot |
| 雲端（M5） | GCP Compute Engine | e2-small / e2-medium |
| 備份（M5） | GCS / S3 | gsutil / aws s3 |

---

## 2. CI/CD 流水線

### 當前（M1）— 手動

```bash
# Lint
ruff check src/ tests/

# Test
PYTHONPATH=src python3 -m pytest -p no:asyncio

# 端到端
PYTHONPATH=src python3 -m backtest_platform.pipeline run \
    --stock-id 2330 --start 2023-01-01 --end 2024-12-31
```

### M3 起：GitHub Actions

```yaml
# .github/workflows/ci.yml（規劃）
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      timescaledb:
        image: timescale/timescaledb:2.14.2-pg16
        env:
          POSTGRES_PASSWORD: test_pw
        options: >-
          --health-cmd "pg_isready -U postgres"
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.10' }
      - run: pip install -e ".[dev]"
      - run: ruff check src/ tests/
      - run: mypy --strict src/
      - run: pytest -v --cov=src --cov-fail-under=80
      - run: pytest -m integration  # 需 DB
```

### M5：部署流程

| 階段 | 步驟 |
| :--- | :--- |
| 1. 建置 | `docker build` 產出 image，push 到 registry |
| 2. 部署到 staging | `docker-compose -f docker-compose.staging.yml up -d` |
| 3. 測試 | smoke test：訊號重現驗證、Shioaji 模擬下單 |
| 4. 部署到 production | `docker-compose up -d`，藍綠部署 |
| 5. 驗證 | 健康檢查、首日訊號比對 paper trading |

---

## 3. 部署檢查清單

### M5 上線前（一次性）

- [ ] 13_security_and_readiness P0 行動項全部完成
- [ ] Paper trading 已跑 3 個月，Sharpe > 回測 × 0.7
- [ ] 滑點實測 < 預估值 1.5x
- [ ] Shioaji TLS、auth 測試通過
- [ ] backup 演練：刪 1 day 資料 → restore 成功
- [ ] 緊急停機腳本準備好（`kill_switch.sh`）
- [ ] Telegram bot 告警測試通過
- [ ] Runbook 完成（H 章）
- [ ] 設定停損上限：DD 25% 自動全平
- [ ] 設定資金上限：1/4 倉位

### 每次新版本部署前（M5 後）

- [ ] code review 通過
- [ ] 所有測試通過
- [ ] paper trading 跑同版本 1 週驗證
- [ ] DB migration（如有）已測試
- [ ] 回滾計畫文字化
- [ ] 監控告警閾值已配置
- [ ] 上線時間避開盤中（建議週末晚上）

### 部署中

- [ ] 監控部署進度（docker logs）
- [ ] 驗證健康檢查（`/health`）
- [ ] 檢查應用日誌（Loguru）
- [ ] 驗證 ETL 排程正常觸發
- [ ] 監控 TimescaleDB connection

### 部署後

- [ ] 隔日盤後 smoke test 通過
- [ ] 訊號頻率符合預期
- [ ] 滑點實測未顯著變化
- [ ] 文檔已更新

---

## 4. 部署策略

| 策略 | 適用場景 | 回滾時間 |
| :--- | :--- | :--- |
| **Blue-Green** | M5 重大版本 | < 30 秒 |
| **Rolling** | 不適用（單機） | — |
| **Canary** | M5 後策略參數調整 | 透過 paper trading 先試 |

當前單機部署，使用 Blue-Green 概念：
- 用 docker tag 區分 `blue` / `green` 版本
- nginx / traefik 切換流量（M5 才有 HTTP layer）
- 切換後保留舊容器 24 小時，方便 rollback

---

## 5. 監控與告警

### 關鍵指標

| 類別 | 指標 | 閾值 |
| :--- | :--- | :--- |
| **資料健康** | FinMind ETL 完成時間 | < 18:00 |
| 資料健康 | 三表 join 後行數 | == 訊號日數 |
| 資料健康 | 異常值（單日 ±10%） | 標記人工確認 |
| **策略健康** | 30D 滾動 Sharpe | > 回測平均 -2σ |
| 策略健康 | 30D 滾動 PF | > 1.0 |
| 策略健康 | 30D 訊號頻率 | 偏離歷史 ±50% 告警 |
| **執行品質** | 平均滑點 | < 預估值 1.5x |
| 執行品質 | 訊號 → 成交比例 | > 80% |
| **Portfolio** | Current DD | > 10% 警告 |
| Portfolio | Heat | > 6% 告警 |
| **基礎設施** | TimescaleDB connection | timeout 5s |
| 基礎設施 | Container restart count | > 0 / day 告警 |

### 告警分級

| 名稱 | 條件 | 嚴重程度 | 通知 |
| :--- | :--- | :--- | :--- |
| 連虧 5 筆 | streak_loss >= 5 | Critical | Telegram + Email |
| 單日 DD > 5% | daily_pnl < -0.05 × equity | Warning | Telegram |
| 單日 DD > 10% | daily_pnl < -0.10 × equity | Critical | Telegram + Email |
| Heat 超標 | heat > 0.06 | Warning | Telegram |
| 資料延遲 | etl_done_time > 18:00 | Warning | Telegram |
| 資料缺失 | row_count != expected | Critical | Telegram |
| Container down | docker container status != running | Critical | Telegram + Email |
| Shioaji 異常 | shioaji response error | Critical | Telegram + 自動停止下單 |

---

## 6. 回滾流程

### 自動回滾觸發（M5）

- DD > 25% → 全平 + 停機
- 連虧 8 筆 → 停機檢討
- Shioaji 連續錯誤 5 次 → 自動停止下單

### 手動回滾步驟

1. 緊急停機：`scripts/kill_switch.sh`（M5 要寫）
2. 確認最後一個穩定 git tag：`git tag --sort=-creatordate | head -5`
3. 執行回滾：
   ```bash
   git checkout <stable_tag>
   docker compose down
   docker compose up -d --build
   ```
4. 驗證：
   - `docker compose ps` 全部 healthy
   - `pipeline run` smoke test 通過
   - Telegram 收到 "rollback complete" 訊息
5. 監控應用健康 24 小時

### 部位處理

回滾時若有持倉：
- 預設規則：**繼續持有，按原規則執行至完成**
- 例外：若回滾原因是策略本身錯誤 → 人工決定是否全平

---

## 7. Runbook：常見狀況

### 7.1 FinMind ETL 失敗

```bash
# 查看 log
docker logs quant-prefect | grep ERROR

# 手動重跑
PYTHONPATH=src python3 -m backtest_platform.data.finmind_etl \
    --stock-id 2330 --start <yesterday> --end <yesterday> --db
```

常見原因：
- API rate limit → 等 1 小時
- token 過期 → 重新註冊 / sponsor 續費
- FinMind 服務中斷 → 切備用源（手動從 TWSE 抓）

### 7.2 TimescaleDB connection refused

```bash
docker compose ps  # 確認 timescaledb 是 healthy
docker compose logs timescaledb | tail -50

# 重啟
docker compose restart timescaledb

# 大絕招（保留資料）
docker compose down
docker compose up -d
```

### 7.3 訊號異常（與 paper trading 不一致）

1. 比對 `compute_signals` 線上 vs 線下重算
2. 檢查 ETL 資料延遲 / 缺漏
3. 檢查 `StrategyConfig` 是否被修改
4. 如差異 > 5% → 立即停止新訊號，人工排查

### 7.4 績效退化

按 v2.md 5.4 退化處理流程：
1. 30D 績效 < 歷史 -1σ → 加強監控
2. -2σ → 倉位降 50%
3. 60D < -2σ → 暫停新進場
4. 90D < -2σ → 全平檢討

---

## 8. 災難恢復

### 資料遺失
- **預防**：每日 backup pg_dump → GCS
- **恢復**：
  ```bash
  gsutil cp gs://backup/quant_trading_YYYYMMDD.dump .
  pg_restore -h localhost -U quant -d quant_trading quant_trading_YYYYMMDD.dump
  ```
- **RPO**：24 小時（每日一次 backup）
- **RTO**：1 小時（單機 restore）

### 機器壞掉
- **預防**：策略狀態（持倉、entry_price）也存 DB
- **恢復**：開新 VPS → pull docker image → restore DB → 切流量
- **RTO**：2 小時

### 策略邏輯出錯（虧大錢）
- **預防**：DD 熔斷規則
- **恢復**：人工檢討 → 修復 → paper trading 1 個月 → 重新評估
