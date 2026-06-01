# 部署拓撲 — backtest_platform

> **版本：** v1.0 | **更新：** 2026-05-31
> **適用 M**：Dev (M2+) / Staging Paper (M4) / Production Live (M5)
> **進度**：見 [`16_wbs_development_plan.md §7.D + §8.B`](./16_wbs_development_plan.md)（單一狀態真相源）
> **適用範圍：** M2-M5 三環境部署
> **關聯文件：** `14_deployment_and_operations_guide.md`（運維 SOP）、`05_architecture_and_design_document.md` §5（C4 Deployment）、`20_dashboard_specification.md`（監控元件）

> 本文 **擴充** 既有 `14_deployment_and_operations_guide.md`，不取代。
> 14 號文件涵蓋 SOP 與 Runbook；本文聚焦 **拓撲與 docker-compose 設計**。

---

## 1. 環境策略

### 1.1 三環境定義

| 環境 | 用途 | 主機 | 資料源 | Broker | 啟用時機 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Dev** | 開發、unit/integration test、本機 backtest 研究 | 本機 PC（WSL2） | Fixture / FinLab dev token | SimulationBlotter | M2 持續 |
| **Staging** | Paper trading 3 個月驗證、E2E test、新版本預演 | 同 Dev 機 or 雲端小 VM | FinLab live token（讀取） | PaperBroker | M4 |
| **Production** | 小倉位實盤 → 全倉 | GCP Compute Engine e2-small/medium | FinLab live + Shioaji quote 雙源 | ShioajiBroker | M5 |

### 1.2 環境差異矩陣

| 配置 | Dev | Staging | Production |
| :--- | :--- | :--- | :--- |
| TimescaleDB | local docker | local docker | dedicated container + WAL backup |
| Discord bot | optional | enabled (test chat) | enabled (prod chat) |
| Grafana auth | none | basic auth | OAuth + IP allowlist |
| Streamlit port | 8501 open | 8501 + basic auth | reverse proxy + TLS |
| Secrets | `.env` | `.env` + git-crypt | GCP Secret Manager |
| 24x7 運行 | no | yes | yes |
| Backup | none | weekly local | daily → GCS |
| 監控告警 | manual | Discord critical only | full 3-level |

---

## 2. Dev 拓撲（本機）

### 2.1 物理視圖

```mermaid
flowchart TB
    subgraph host["Host: Windows 11 + WSL2 Ubuntu 22.04<br/>Intel i7 / 32GB RAM"]
        subgraph venv["Python 3.10 venv (uv-managed)"]
            app["Application<br/>backtest_platform"]
            zipline_cli["zipline CLI"]
            streamlit["streamlit run"]
            alerter["monitoring.alerter (optional)"]
        end

        subgraph docker["Docker Engine 24.x"]
            tsdb["TimescaleDB<br/>:5432"]
            influx["InfluxDB 2.7<br/>:8086 (optional dev)"]
            grafana["Grafana 10.4<br/>:3000 (optional dev)"]
            prefect["Prefect 2.19<br/>:4200 (optional dev)"]
        end

        zipline_data["~/.zipline/data/<br/>(bundles)"]
        parquet["./data/parquet/"]
        envfile[".env"]
    end

    finlab[("FinLab API")]
    shioaji_sandbox[("Shioaji Sandbox")]
    discord_test[("Discord test bot")]

    app -->|"libpq"| tsdb
    app -->|"file I/O"| parquet
    app -->|"file I/O"| zipline_data
    app -->|"HTTPS"| finlab
    app -.->|"WS"| shioaji_sandbox
    alerter -.->|"poll"| tsdb
    alerter -.->|"HTTPS"| discord_test
    streamlit -->|"libpq"| tsdb
    grafana -.->|"InfluxQL"| influx
    grafana -.->|"SQL"| tsdb
    prefect -.->|"trigger"| app
    app -.->|"UDP"| influx
```

### 2.2 必要 vs 選用

| Container | Dev 必要 | 啟用時機 |
| :--- | :---: | :--- |
| TimescaleDB | ✅ | M1 起 |
| InfluxDB | optional | M3 開發 dashboard 時 |
| Grafana | optional | 同上 |
| Prefect | optional | M4 開發排程時 |

### 2.3 啟動指令

```bash
# WSL terminal
cd ~/python_workspace/Quantitative_Trading

# 1. 必要服務
docker compose -f docker-compose.dev.yml up -d timescaledb

# 2. venv
uv sync
source .venv/bin/activate

# 3. 初始化 DB
psql -h localhost -U quant -d quant_trading -f dashboard/db_schema.sql

# 4. bundle ingest
zipline ingest -b finlab --start 2020-01-01 --end 2024-12-31

# 5. dashboard
streamlit run dashboard/streamlit_app.py
```

---

## 3. Staging Paper Trading 拓撲（M4）

### 3.1 物理視圖

```mermaid
flowchart TB
    subgraph host_staging["Host: Dev 同機 or 雲端 e2-micro"]
        subgraph dockerd_st["Docker Compose"]
            app_st["app:<br/>backtest_platform"]
            paper_br["PaperBroker daemon"]
            scheduler["Prefect Server + Worker"]
            tsdb_st["TimescaleDB"]
            influx_st["InfluxDB"]
            grafana_st["Grafana :3000"]
            streamlit_st["Streamlit :8501"]
            alerter_st["Alerter daemon"]
            live_feed["finlab_live polling"]
        end
    end

    finlab[("FinLab live API")]
    discord_staging[("Discord staging channel")]

    live_feed -->|"poll 5s"| finlab
    live_feed -->|"INSERT"| tsdb_st
    scheduler -->|"cron 14:30"| app_st
    app_st -->|"in-proc"| paper_br
    paper_br -->|"INSERT fills"| tsdb_st
    app_st -->|"UDP"| influx_st
    alerter_st -->|"poll/threshold"| tsdb_st
    alerter_st -->|"poll/threshold"| influx_st
    alerter_st -->|"HTTPS"| discord_staging
    grafana_st --> influx_st
    grafana_st --> tsdb_st
    streamlit_st --> tsdb_st
```

### 3.2 與 Dev 差異

| 項目 | Dev | Staging |
| :--- | :--- | :--- |
| 容器數 | 1-4 | 8-10 |
| Prefect | optional | required |
| Alerter | manual | daemon |
| Live feed | off | running 09:00-13:30 TWT |
| Backup | no | weekly snapshot |
| Restart policy | no | `unless-stopped` |

### 3.3 Paper trading 流程

```mermaid
sequenceDiagram
    participant Cron as Prefect
    participant App as Application
    participant Feed as live_feed
    participant TSDB as TimescaleDB
    participant Paper as PaperBroker
    participant Alert as Alerter
    participant DC as Discord

    Note over Cron: 08:30 盤前
    Cron->>App: daily_pre_open_flow
    App->>Feed: warmup historical bars
    Feed->>TSDB: backfill last 60 days

    Note over Cron: 09:00 開盤
    Cron->>Feed: start live polling

    loop 09:00-13:30 every 5min
        Feed->>TSDB: INSERT live quotes
    end

    Note over Cron: 13:31 收盤後
    Cron->>App: daily_algo_flow
    App->>TSDB: load quotes + scores
    App->>App: compute_signals
    App->>Paper: submit orders
    Paper->>TSDB: INSERT fills (simulated)
    App->>TSDB: emit equity_snapshot

    Note over Cron: 14:35 報告
    Cron->>Alert: trigger digest
    Alert->>TSDB: aggregate today
    Alert->>TG: INFO-001 digest
```

---

## 4. Production Live 拓撲（M5）

### 4.1 物理視圖（從 `05_architecture_and_design_document.md` §5.1.2 擴充）

```mermaid
flowchart TB
    subgraph gcp["GCP Compute Engine e2-small (2vCPU/4GB) · asia-east1 · COS"]
        subgraph dockerd5["Docker Compose v2"]
            app5["app<br/>Zipline + Strategy"]
            paper5["paper_broker<br/>(M5 仍跑作 sanity)"]
            shio5["shioaji_broker"]
            live_feed5["finlab_live"]
            shio_quote5["shioaji_quote<br/>備援"]
            scheduler5["prefect_server + worker"]
            tsdb5["timescaledb"]
            influx5["influxdb"]
            grafana5["grafana"]
            streamlit5["streamlit"]
            alerter5["alerter"]
            caddy["caddy<br/>reverse proxy + TLS"]
        end
        cron5["systemd timer:<br/>pg_dump nightly"]
    end

    subgraph user_pc["使用者 PC"]
        browser["瀏覽器"]
    end

    finlab[("FinLab live API")]
    twse[("TWSE")]
    shioaji[("Shioaji API")]
    discord[("Discord Bot API")]
    gcs[("GCS Bucket<br/>quant-backup-prod")]
    gcp_sm[("GCP Secret Manager")]

    browser -->|"HTTPS :443"| caddy
    caddy -->|"localhost:8501"| streamlit5
    caddy -->|"localhost:3000"| grafana5
    streamlit5 --> tsdb5
    grafana5 --> influx5
    grafana5 --> tsdb5

    scheduler5 -->|"cron"| app5
    app5 --> live_feed5
    live_feed5 --> finlab
    app5 -.->|"backup"| shio_quote5
    shio_quote5 --> shioaji
    app5 -->|"orders"| shio5
    shio5 -->|"WS TLS"| shioaji
    app5 -->|"fills"| tsdb5
    app5 -->|"metrics UDP"| influx5

    alerter5 --> tsdb5
    alerter5 --> influx5
    alerter5 -->|"HTTPS"| discord

    cron5 -->|"gsutil cp"| gcs
    app5 -.->|"read secrets"| gcp_sm
```

### 4.2 規格

| 項目 | 規格 |
| :--- | :--- |
| GCP zone | asia-east1-b（彰化）|
| Machine | e2-small (2 vCPU, 4GB)；M5 後期視負載升 e2-medium |
| OS | Container-Optimized OS (COS) |
| Disk | 50GB SSD persistent |
| Network | premium tier + reserved external IP |
| Firewall | 只開 443 (HTTPS via caddy)；5432/8086/8501/3000 internal only |
| 預估月成本 | NT$ 800-1500（VM）+ NT$ 50（GCS）|

---

## 5. Docker Compose 設計

### 5.1 三 Compose 檔分工

```
backtest_platform/
├── docker-compose.dev.yml          # Dev minimal (timescaledb only)
├── docker-compose.staging.yml      # Staging full stack (no shioaji)
└── docker-compose.prod.yml         # Production (extends staging + shioaji + caddy)
```

### 5.2 `docker-compose.prod.yml` 完整草案

```yaml
version: "3.9"

x-common-env: &common-env
  TZ: Asia/Taipei
  PYTHONUNBUFFERED: "1"
  DATABASE_URL: postgresql://quant:${DB_PASSWORD}@timescaledb:5432/quant_trading
  INFLUX_URL: http://influxdb:8086
  INFLUX_TOKEN: ${INFLUX_TOKEN}
  DISCORD_BOT_TOKEN: ${DISCORD_BOT_TOKEN}
  DISCORD_CHANNEL_ID: ${DISCORD_CHANNEL_ID}
  FINLAB_TOKEN: ${FINLAB_TOKEN}
  SHIOAJI_API_KEY: ${SHIOAJI_API_KEY}
  SHIOAJI_API_SECRET: ${SHIOAJI_API_SECRET}

services:
  timescaledb:
    image: timescale/timescaledb:2.14.2-pg16
    container_name: tsdb
    restart: unless-stopped
    environment:
      POSTGRES_DB: quant_trading
      POSTGRES_USER: quant
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - tsdb_data:/var/lib/postgresql/data
      - ./dashboard/db_schema.sql:/docker-entrypoint-initdb.d/01-schema.sql:ro
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "quant"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks: [internal]

  influxdb:
    image: influxdb:2.7
    container_name: influx
    restart: unless-stopped
    environment:
      DOCKER_INFLUXDB_INIT_MODE: setup
      DOCKER_INFLUXDB_INIT_USERNAME: admin
      DOCKER_INFLUXDB_INIT_PASSWORD: ${INFLUX_PASSWORD}
      DOCKER_INFLUXDB_INIT_ORG: quant
      DOCKER_INFLUXDB_INIT_BUCKET: metrics
      DOCKER_INFLUXDB_INIT_ADMIN_TOKEN: ${INFLUX_TOKEN}
    volumes:
      - influx_data:/var/lib/influxdb2
    networks: [internal]

  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: app
    restart: unless-stopped
    environment: *common-env
    volumes:
      - zipline_data:/root/.zipline
      - ./data/parquet:/app/data/parquet
    depends_on:
      timescaledb: { condition: service_healthy }
      influxdb: { condition: service_started }
    networks: [internal]

  paper_broker:
    image: ${APP_IMAGE}
    command: python -m backtest_platform.adapters.brokers.paper_broker
    environment: *common-env
    depends_on: [timescaledb]
    networks: [internal]

  shioaji_broker:
    image: ${APP_IMAGE}
    command: python -m backtest_platform.adapters.brokers.shioaji_broker
    environment: *common-env
    depends_on: [timescaledb]
    networks: [internal]

  live_feed:
    image: ${APP_IMAGE}
    command: python -m backtest_platform.adapters.data_feed.finlab_live
    environment: *common-env
    depends_on: [timescaledb]
    networks: [internal]

  scheduler:
    image: prefecthq/prefect:2.19-python3.10
    container_name: prefect
    command: prefect server start --host 0.0.0.0
    environment:
      PREFECT_API_DATABASE_CONNECTION_URL: postgresql+asyncpg://quant:${DB_PASSWORD}@timescaledb:5432/prefect
    depends_on: [timescaledb]
    networks: [internal]

  streamlit:
    image: ${APP_IMAGE}
    command: streamlit run dashboard/streamlit_app.py --server.port 8501 --server.address 0.0.0.0
    environment: *common-env
    depends_on: [timescaledb]
    networks: [internal]

  grafana:
    image: grafana/grafana:10.4.2
    container_name: grafana
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
      GF_USERS_ALLOW_SIGN_UP: "false"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./dashboard/grafana_dashboards:/etc/grafana/provisioning/dashboards:ro
    depends_on: [influxdb, timescaledb]
    networks: [internal]

  alerter:
    image: ${APP_IMAGE}
    command: python -m backtest_platform.monitoring.alerter
    environment: *common-env
    depends_on: [timescaledb, influxdb]
    networks: [internal]

  caddy:
    image: caddy:2-alpine
    container_name: caddy
    restart: unless-stopped
    ports: ["80:80", "443:443"]
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on: [streamlit, grafana]
    networks: [internal, public]

volumes:
  tsdb_data:
  influx_data:
  zipline_data:
  grafana_data:
  caddy_data:
  caddy_config:

networks:
  internal:
    driver: bridge
  public:
    driver: bridge
```

### 5.3 Caddyfile（反向代理）

```caddy
quant.example.com {
    handle_path /grafana/* {
        reverse_proxy grafana:3000
    }
    handle {
        reverse_proxy streamlit:8501
    }
    log {
        output file /data/access.log
    }
}
```

---

## 6. 排程設計

### 6.1 每日 `daily_flow`

```mermaid
gantt
    title 每日 daily_flow（台股交易日）
    dateFormat HH:mm
    axisFormat %H:%M

    section 盤前
    ETL pre-warmup           :08:30, 30m
    FinLab daily snapshot    :08:45, 15m
    universe rebuild         :09:00, 5m

    section 盤中
    Live feed polling        :09:00, 270m
    Heartbeat check          :09:00, 270m

    section 盤後
    Final daily bars ingest  :14:00, 10m
    Algo compute_signals     :14:15, 5m
    Submit orders            :14:20, 5m
    Reconciliation           :14:25, 5m
    Equity snapshot          :14:30, 2m
    Discord digest          :14:35, 3m
    Backup                   :02:00, 30m
```

### 6.2 Prefect flow 結構

```python
# orchestration/daily_flow.py
from prefect import flow, task
from prefect.client.schedules import CronSchedule

@task(retries=3, retry_delay_seconds=60)
def pre_open_etl(): ...

@task(retries=2)
def algo_signals(): ...

@task
def submit_orders(): ...

@task
def reconcile_positions(): ...

@flow(name="daily_pre_open", retries=1)
def pre_open_flow():
    pre_open_etl()

@flow(name="daily_post_close", retries=1)
def post_close_flow():
    algo_signals()
    submit_orders()
    reconcile_positions()

@flow(name="daily_digest")
def digest_flow():
    send_discord_digest()

# deployment
pre_open_flow.serve(name="prod", schedule=CronSchedule(cron="30 8 * * 1-5", timezone="Asia/Taipei"))
post_close_flow.serve(name="prod", schedule=CronSchedule(cron="15 14 * * 1-5", timezone="Asia/Taipei"))
digest_flow.serve(name="prod", schedule=CronSchedule(cron="35 14 * * 1-5", timezone="Asia/Taipei"))
```

---

## 7. Secrets 管理

### 7.1 三環境策略

| 環境 | 機制 | 範例 |
| :--- | :--- | :--- |
| Dev | `.env` (gitignored) | `cp .env.example .env && vim .env` |
| Staging | `.env` + git-crypt | `git-crypt unlock` 後 `.env` 解密可讀 |
| Production | GCP Secret Manager | `gcloud secrets versions access latest --secret=finlab-token` |

### 7.2 必管理 secret 清單

| Secret | 用途 | rotation 週期 |
| :--- | :--- | :--- |
| `DB_PASSWORD` | TimescaleDB | 季度 |
| `INFLUX_TOKEN` | InfluxDB | 季度 |
| `GRAFANA_PASSWORD` | Grafana admin | 季度 |
| `FINLAB_TOKEN` | FinLab API | 年度（伴隨 sponsor 續費） |
| `SHIOAJI_API_KEY` / `SHIOAJI_API_SECRET` | 實盤下單 | 半年 |
| `DISCORD_BOT_TOKEN` | Bot API | 變更時 |
| `DISCORD_CHANNEL_ID` | 接收 chat | 固定 |

### 7.3 production 啟動 secret 注入

```bash
# entrypoint.sh (production VM)
#!/bin/bash
set -euo pipefail

export DB_PASSWORD=$(gcloud secrets versions access latest --secret=db-password)
export FINLAB_TOKEN=$(gcloud secrets versions access latest --secret=finlab-token)
export SHIOAJI_API_KEY=$(gcloud secrets versions access latest --secret=shioaji-key)
export SHIOAJI_API_SECRET=$(gcloud secrets versions access latest --secret=shioaji-secret)
export DISCORD_BOT_TOKEN=$(gcloud secrets versions access latest --secret=discord-token)
export DISCORD_CHANNEL_ID=$(gcloud secrets versions access latest --secret=discord-channel-id)

docker compose -f docker-compose.prod.yml up -d
```

### 7.4 防外洩規範

- 禁止 secret 進 git（pre-commit hook 用 `detect-secrets`）
- 禁止 secret 進 log（Loguru filter）
- 禁止 secret 在 Discord 訊息出現
- 容器以非 root 執行（M5 P2 行動項）

---

## 8. 災難復原

### 8.1 服務降級策略

| 失效服務 | Fallback | 觸發 | 通知 |
| :--- | :--- | :--- | :--- |
| FinLab API | 切 FinMind bundle | HTTP 429/500 連 3 次 | HIGH-001 |
| FinLab live feed | 切 Shioaji quote | 連續 60s 無 tick | CRIT-002 |
| Shioaji broker | 暫停下單（不切回 paper） | submit error 連 3 次 | CRIT 自動暫停 |
| TimescaleDB | 無 fallback，停 algo | health check fail | CRIT + 全停 |
| InfluxDB | 降級（metrics 不寫，algo 照跑） | health check fail | HIGH |
| Discord | 寫 local log + email backup | send_message exception | system log |

### 8.2 RPO / RTO 目標

| 環境 | RPO | RTO | 機制 |
| :--- | :--- | :--- | :--- |
| Dev | N/A | N/A | — |
| Staging | 7 天 | 4 小時 | weekly snapshot + manual restore |
| Production | 1 小時（WAL 連續歸檔） | 1 小時 | GCS WAL + nightly pg_dump |

### 8.3 復原演練排程

- M5 上線前一次性演練（必過）
- 每季一次演練：刪 1 day 資料 → restore → smoke test 通過
- 演練記錄寫入 `dev_docs/operations/recovery_drills.md`

---

## 9. 監控與告警基礎設施

對應 `20_dashboard_specification.md`，部署層面：

### 9.1 元件清單

| 元件 | 容器 | 端口（internal） | 啟用 |
| :--- | :--- | :--- | :--- |
| InfluxDB | `influxdb` | 8086 | M4 |
| Grafana | `grafana` | 3000 | M4 |
| node_exporter | `node_exporter` | 9100 | M4（host metrics） |
| cAdvisor | `cadvisor` | 8080 | M4（container metrics） |
| pg_exporter | `pg_exporter` | 9187 | M5 |
| Discord bot | `alerter` | — | M4 |

### 9.2 Grafana data source 設定

```yaml
# dashboard/grafana_dashboards/provisioning/datasources/datasources.yml
apiVersion: 1
datasources:
  - name: InfluxDB
    type: influxdb
    url: http://influxdb:8086
    access: proxy
    isDefault: true
    jsonData:
      version: Flux
      organization: quant
      defaultBucket: metrics
    secureJsonData:
      token: ${INFLUX_TOKEN}

  - name: TimescaleDB
    type: postgres
    url: timescaledb:5432
    database: quant_trading
    user: grafana_ro
    secureJsonData:
      password: ${GRAFANA_DB_PASSWORD}
    jsonData:
      sslmode: disable
      timescaledb: true
```

---

## 10. CI/CD（M5 啟用）

### 10.1 GitHub Actions 部署 workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    tags: ['v*.*.*']

jobs:
  build-push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      - run: gcloud auth configure-docker asia-east1-docker.pkg.dev
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: |
            asia-east1-docker.pkg.dev/${{ secrets.GCP_PROJECT }}/quant/app:${{ github.ref_name }}
            asia-east1-docker.pkg.dev/${{ secrets.GCP_PROJECT }}/quant/app:latest

  deploy:
    needs: build-push
    runs-on: ubuntu-latest
    steps:
      - uses: google-github-actions/ssh-compute@v1
        with:
          instance_name: quant-vm
          zone: asia-east1-b
          command: |
            export APP_IMAGE=asia-east1-docker.pkg.dev/${{ secrets.GCP_PROJECT }}/quant/app:${{ github.ref_name }}
            docker compose -f docker-compose.prod.yml pull
            docker compose -f docker-compose.prod.yml up -d --no-build
            sleep 30
            docker compose -f docker-compose.prod.yml ps
```

### 10.2 部署檢查清單（對齊 `14` §3）

部署前：
- [ ] PR merge + tag 已建
- [ ] paper trading 跑同版本 1 週驗證
- [ ] DB migration script 已測試
- [ ] 回滾 SOP 文字化

部署中：
- [ ] `docker compose ps` 全部 healthy
- [ ] Streamlit 可開（through Caddy）
- [ ] Grafana 可開
- [ ] Discord 收到「deploy complete」訊息

部署後：
- [ ] 隔日盤後 smoke test 通過
- [ ] 訊號與 paper 一致
- [ ] 滑點實測未變化

---

## 11. 成本估算

### 11.1 月度成本（NT$）

| 項目 | Dev | Staging | Production |
| :--- | :---: | :---: | :---: |
| 主機 | 0（本機） | 0-500 | 800-1500 |
| FinLab 訂閱 | 0 | 0 | 800-900（年費攤月） |
| GCS backup | 0 | 0 | 30-50 |
| Discord | 0 | 0 | 0 |
| 證券手續費 | 0 | 0 | 浮動 |
| **小計** | **0** | **0-500** | **1630-2450** |

### 11.2 成本最佳化

- M5 初期用 e2-small (NT$ 800)；觀察 RAM 使用率 < 70% 則維持
- Live feed 改 long-polling 而非 5 秒輪詢 → 省 FinLab quota
- bcolz bundle 用 lz4 壓縮 → 省 50% disk
- GCS lifecycle policy：30 天後降為 nearline → 省 60% 儲存費

---

## 12. 變更紀錄

| 版本 | 日期 | 變更 |
| :--- | :--- | :--- |
| v1.0 | 2026-05-31 | 初版（對應 plan §5；擴充 14 號文件部署拓撲；含完整 docker-compose） |
