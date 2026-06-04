# 專案結構指南 — backtest_platform

> **版本：** v1.1 | **更新：** 2026-05-31
> **架構圖**：目錄對應 C4 **L3-A Application** 元件，見 [05_architecture_and_design_document.md §1.1](./05_architecture_and_design_document.md)
> **v1.1 變更**：對齊 M2 重組（commit `ae869f5`）— `strategy/` 改名 `strategies/four_layer_resonance/`、新增 `adapters/` `orchestration/` `monitoring/` `dashboard/`、新增 `sprint_0_spikes/`、移除原規劃但未實作的 `live/`（功能併入 `adapters/brokers/`）

---

## 設計原則

- **按功能組織**：每個 sub-package 為一個明確職責
- **明確職責**：`config/` = 參數、`data/` = IO、`strategies/` = 策略邏輯、`adapters/` = 廠商接口、`engines/` = 引擎 wrapper、`validation/` = 統計檢驗、`orchestration/` = 排程、`monitoring/` = 監控、`dashboard/` = UI
- **一致命名**：Python `snake_case.py`、測試 `test_*.py`、CLI module 用 `python -m <module>`
- **配置外部化**：`.env` + Pydantic `BaseSettings`（M2 引入 `config/settings.py`）
- **根目錄簡潔**：原始碼放 `src/`，根目錄只放 `pyproject.toml`、`README.md`、`docker-compose.yml`

---

## 頂層結構

```plaintext
backtest_platform/
├── docker/                       # 容器映像與初始化
│   └── timescaledb/init.sql      # DB schema
├── docs/                         # 工程文件（M1_setup、m1_data_audit）
├── data/                         # ETL 產出 cache + Zipline bundles（gitignore）
│   ├── parquet/
│   └── zipline_bundles/          # M2+：FinLab bundle 中繼產物
├── reports/                      # CLI 輸出報表（gitignore）
├── src/backtest_platform/        # 原始碼（見下）
├── tests/                        # pytest（見下）
├── sprint_0_spikes/              # M2 啟動前 6 spike + RUNBOOK（gate 通過後可刪）
│   ├── RUNBOOK.md
│   ├── s1_tquant_hello_world.py    # ❌ FAIL → ADR-013 切到 zipline-reloaded（spike 結果保留）
│   ├── s2_m1_plug_zipline.py
│   ├── s3_finlab_bundle_poc.py
│   ├── s3_verify_bundle.py
│   ├── s4_shioaji_sandbox.py
│   ├── s5_finlab_live_polling.py
│   ├── s6_seed_equity_data.py
│   ├── s6_streamlit_dashboard.py
│   ├── gate_review.py
│   └── results/                  # spike 產出（gitignore）
├── .env.example                  # 環境變數樣板（含 FINLAB / TEJ / SHIOAJI / DISCORD / ...）
├── .gitignore
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

## 原始碼結構（src/backtest_platform/）

```plaintext
src/backtest_platform/
├── __init__.py
│
├── config/                       # 純資料層
│   ├── __init__.py
│   ├── strategy_config.py        # StrategyConfig (Pydantic frozen)
│   └── settings.py               # M2+：環境設定 (Pydantic Settings)
│
├── data/                         # Infrastructure：IO + 外部 API
│   ├── __init__.py
│   ├── schemas.py                # Pydantic models + ETLBundle
│   ├── finmind_etl.py            # FinMind 拉取 + normalize + CLI（fallback 來源）
│   ├── adjustment.py             # 前復權因子計算（FinMind 用；FinLab 已預調整）
│   ├── db_writer.py              # TimescaleDB idempotent upsert
│   ├── universe.py               # 標的池過濾（v2.md 2.2）
│   └── universe_builder.py       # ★ 候選 D：point-in-time 中小型 universe builder（ADR-020，純函式）
│
├── strategies/                   # ★ M2 改名 — 多策略 namespace
│   ├── __init__.py               # （未來：strategy registry）
│   └── four_layer_resonance/     # M1 四層共振策略
│       ├── __init__.py           # 對外 re-export (compute_scores, compute_signals, ...)
│       ├── indicators.py         # RSI / KD / MACD / SwingHigh/Low
│       ├── scoring.py            # compute_scores（四層計分）
│       └── signals.py            # compute_signals + evaluate_bar
│
├── adapters/                     # ★ M2 新增 — 廠商接口層 (ADR-005/006/008)
│   ├── __init__.py
│   ├── data_bundle/              # Zipline bundle ingesters
│   │   ├── __init__.py
│   │   ├── finlab_bundle.py      # M2：FinLab → Zipline bundle (主)
│   │   └── finmind_bundle.py     # M2：包裝 M1 finmind_etl (fallback)
│   ├── data_feed/                # 即時資料 (M4+)
│   │   ├── __init__.py
│   │   ├── finlab_live.py        # FinLab realtime polling
│   │   └── shioaji_quote.py      # Shioaji 報價（備援）
│   └── brokers/                  # 下單接口 (M4-M5)
│       ├── __init__.py
│       ├── paper_broker.py       # M4：模擬撮合
│       └── shioaji_broker.py     # M5：永豐金實盤
│
├── engines/                      # M3+：vectorbt 副引擎 (ADR-007)
│   ├── __init__.py
│   └── vectorbt_adapter.py       # grid/WFA 最佳化
│                                 # (註：ADR-001 rqalpha 已 superseded by ADR-005)
│
├── validation/                   # M3+：統計驗證
│   ├── __init__.py
│   ├── metrics.py                # 30+ 指標 enum + functions
│   ├── pbo.py                    # PBO/CSCV (自寫，避 pypbo AGPL)
│   ├── dsr.py                    # Deflated Sharpe Ratio (López de Prado)
│   ├── wfa.py                    # Walk-Forward splitter
│   └── reports.py                # quantstats wrapper
│
├── orchestration/                # ★ M2/M4 新增 — 排程編排
│   ├── __init__.py
│   ├── daily_flow.py             # 每日 ETL → algo → 下單 → log
│   └── cli.py                    # click entry (M2+ 主入口)
│
├── monitoring/                   # ★ M4 新增 — 監控與告警 (ADR-009)
│   ├── __init__.py
│   ├── metrics_emitter.py        # Algorithm hook，每 bar 寫 metrics
│   └── alerter.py                # Discord bot + 規則引擎 (3 級)
│
├── dashboard/                    # ★ M3/M5 新增 — UI (ADR-009)
│   ├── __init__.py
│   ├── streamlit_app.py          # 5 策略面板 (A 績效 B 部位 C 訊號 D 風控 E 驗證)
│   ├── grafana_dashboards.json   # 4 系統面板 (F ETL G quota H 排程 I 資源)
│   └── db_schema.sql             # TimescaleDB 13 表 DDL
│
├── api/                          # ★ v0.6 新增 — HTTP API (FastAPI, ADR-015 / 21 §8)
│   ├── __init__.py               # create_app / API_VERSION re-export
│   ├── app.py                    # create_app 工廠 + 信封 exception handlers
│   ├── envelope.py               # {success,data,error,meta} 統一信封
│   ├── schemas.py                # 請求模型（extra=forbid 邊界驗證）
│   ├── deps.py                   # runs path + run executor 依賴注入
│   └── routers/                  # presets / runs / gate / metrics（薄轉接層）
│
└── pipeline.py                   # Application：M1 端到端 CLI（backward-compat shim）
                                  # M2+ 主入口改為 orchestration/cli.py
```

### 模組啟用 milestone

| 模組 | M1 | M2 | M3 | M4 | M5 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `config/` | ✅ | + settings.py | | | |
| `data/` | ✅ | | | | |
| `strategies/four_layer_resonance/` | ✅（改名搬入）| | | | |
| `adapters/data_bundle/` | | ✅ | | | |
| `adapters/data_feed/` | | | | ✅ | |
| `adapters/brokers/paper_broker.py` | | | | ✅ | |
| `adapters/brokers/shioaji_broker.py` | | | | | ✅ |
| `engines/vectorbt_adapter.py` | | | ✅ | | |
| `validation/` | | | ✅ | | |
| `orchestration/` | | ✅ (cli.py) | | + daily_flow | |
| `monitoring/` | | | | ✅ | |
| `dashboard/streamlit_app.py` | | | ✅ MVP | | + D/E 面板 |
| `dashboard/grafana_dashboards.json` | | | | ✅ | |
| `api/` (FastAPI HTTP) | | | ✅ v0.6（提前；研究迴圈讀寫面） | + 監控/風控面板端點 | |
| `research/` (run loop) | | | ✅ v0.1-v0.3（RunConfig/IS harness/runs ledger/sweep/compare/CLI） | | |
| `pipeline.py` (M1 shim) | ✅ | (保留) | | | |

---

## 測試結構

```plaintext
tests/
├── conftest.py                   # 全局 fixtures
├── test_strategy_config.py
│
├── data/
│   ├── __init__.py
│   ├── test_finmind_etl.py
│   ├── test_adjustment.py
│   ├── test_db_writer.py         # 含 @integration mark
│   ├── test_universe.py
│   └── test_universe_builder.py  # ★ 候選 D builder（14 合成測試，hermetic）
│
└── strategies/                   # ★ 對應 src/ 改名
    ├── __init__.py
    └── four_layer_resonance/
        ├── __init__.py
        ├── test_scoring.py
        └── test_signals.py
```

### M2+ 測試擴充（詳見 22_test_strategy.md §1.2）

未來新增：
- `tests/unit/adapters/` — adapter 單元
- `tests/integration/` — bundle ingest, Shioaji sandbox, Streamlit DB
- `tests/recon/` — 跨引擎對拍（Zipline vs vectorbt 等 5 條）
- `tests/e2e/` — 三模式 smoke
- `tests/performance/` — 100 檔 × 10 年 < 30 分鐘
- `tests/regression/` — M1 baseline 凍結

### 測試標記

`pyproject.toml` 中定義：
- `@pytest.mark.integration` — 需要 DB / FinMind / FinLab API
- `@pytest.mark.slow` — 執行 > 5 秒
- `@pytest.mark.recon` — 跨引擎對拍（M3+）
- `@pytest.mark.e2e` — 端到端（M3+）
- `@pytest.mark.live` — 需 Shioaji 真實憑證（M5）

執行：
```bash
pytest -m unit                          # PR check
pytest -m "integration and not slow"    # nightly
pytest -m recon                         # milestone gate
pytest -m e2e                           # release gate
```

---

## 文檔結構

```plaintext
backtest_platform/docs/           # 專案內運行手冊（per-milestone）
├── M1_setup.md                   # M1 驗收條件 + 端到端驗證
├── m1_data_audit_2330_2024_11.md # XQ vs FinMind 抽查報告
├── M2_backtest_report.md         # （待 M2 產出）
├── M3_validation_report.md       # （待 M3）
├── M4_paper_trading_log.md       # （待 M4）
└── M5_live_runbook.md            # （待 M5）

dev_docs/                         # 工程文件（架構/規格/ADR/計劃）
└── （見 INDEX.md，含階段 1-7）
```

---

## 命名慣例

| 檔案類型 | 規則 | 範例 |
| :--- | :--- | :--- |
| Python 模組 | `snake_case.py` | `finmind_etl.py`, `finlab_bundle.py` |
| 策略子套件 | `snake_case/` | `four_layer_resonance/` |
| 測試 | `test_*.py` | `test_scoring.py` |
| 類別 | `PascalCase` | `StrategyConfig`, `ETLBundle`, `PaperBroker` |
| 函式 | `snake_case` | `compute_scores`, `fetch_bundle` |
| 常數 | `UPPER_SNAKE_CASE` | `REQUIRED_COLUMNS`, `SIGNAL_PRIORITY` |
| 私有 helper | `_underscore_prefix` | `_normalize_daily`, `_evaluate_priority` |
| CLI module | 對應檔名 | `python -m backtest_platform.pipeline` |
| Zipline bundle name | `lower_snake` | `finlab`, `finmind` |

---

## 跨層依賴規則（強制）

```
                ┌──────────────────────────────┐
                │  orchestration/cli.py        │
                │  (M2+ 主入口)                │
                └────────────┬─────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌──────────────┐  ┌──────────────────┐  ┌────────────────┐
│ engines/     │  │ strategies/      │  │ adapters/      │
│ vectorbt     │  │ four_layer_*/    │  │ data_bundle    │
│ (副引擎)     │  │ (Domain 純函式)  │  │ data_feed      │
└──────┬───────┘  └────────┬─────────┘  │ brokers        │
       │                   │            └────────┬───────┘
       │                   │                     │
       │                   ▼                     │
       │           ┌──────────────┐              │
       └──────────►│  config/     │◄─────────────┘
                   │  (純資料)    │
                   └──────────────┘
                          ▲
                          │ 不依賴
                          │
                   ┌──────┴──────┐
                   │  data/      │ ← 既有 M1 ETL (作 fallback)
                   │  (Infra)    │
                   └─────────────┘

                   monitoring/ + dashboard/ + validation/
                   側邊掛接，read-only 消費 TimescaleDB
```

**禁止**：
- ❌ `strategies/` 依賴 `data/` 或 `adapters/`（Domain 不知道 IO）
- ❌ `config/` 依賴任何模組（純資料）
- ❌ `adapters/` 之間 cross-import（每個 adapter 獨立）
- ❌ `monitoring/` `dashboard/` 寫入業務 table（read-only consumers）

詳見 [09_file_dependencies_template.md](./09_file_dependencies_template.md)

---

## .env 環境變數

詳細範例見 `backtest_platform/.env.example`（已隨 M2 新增 FINLAB / TEJ / DISCORD / INFLUXDB / ZIPLINE_ROOT 等變數）。

關鍵分類：

| 類別 | 變數 | M | 來源 |
| :--- | :--- | :---: | :--- |
| 資料源（主） | `FINLAB_API_TOKEN` | M2 | https://ai.finlab.tw |
| ~~資料源（TEJ）~~ | ~~`TEJAPI_KEY`~~ | — | ADR-013 已棄用 TEJ 路徑；主路徑（zipline-reloaded + FinLab/FinMind bundle）不依賴 TEJ |
| 資料源（fallback） | `FINMIND_TOKEN` | M1 | https://finmindtrade.com |
| Broker（M4 paper / M5 live） | `SHIOAJI_*` | M4 | 永豐金 API 中心 |
| 儲存 | `POSTGRES_*` | M1 | docker-compose |
| Zipline | `ZIPLINE_ROOT` | M2 | 本機路徑 |
| Metric TSDB | `INFLUXDB_*` | M4 | docker-compose |
| 告警 | `DISCORD_*`（M2 從 Telegram 遷移） | M4 | Discord developer portal |

**規則**：`.env` 永遠 gitignore；任何新環境變數先寫入 `.env.example`。

---

## 演進原則

- 本結構是 **M2 起點**（M1 → M2 重組已完成，commit `ae869f5`）
- 後續 milestone 依需擴充（特別是 `adapters/`、`monitoring/`、`dashboard/` 仍多為空骨架）
- 頂層 sub-package 變更需 ADR（如 ADR-005~009 已記錄本次 M2 重組）
- `sprint_0_spikes/` 在 Sprint 0 gate 通過後可刪除（已 commit）
- 一致性比嚴格遵守模式更重要
