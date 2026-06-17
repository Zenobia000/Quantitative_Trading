# 專案結構指南 — backtest_platform

> **版本：** v1.1 | **更新：** 2026-05-31
> **架構圖**：目錄對應 C4 **L3-A Application** 元件，見 [05_architecture_and_design_document.md §1.1](./05_architecture_and_design_document.md)
> **v1.1 變更**：對齊 M2 重組（commit `ae869f5`）— `strategy/` 改名 `strategies/four_layer_resonance/`、新增 `adapters/` `orchestration/` `monitoring/` `dashboard/`、新增 `sprint_0_spikes/`、移除原規劃但未實作的 `live/`（功能併入 `adapters/brokers/`）
> **v1.2 變更（2026-06-16, ADR-026）**：抽出 `strategies/common/`（中立回測機制單一真實來源，解策略間 leaky abstraction）；`multi_factor` / spikes（原 `sprint_0_spikes/`）/ 舊驗證 scripts 封存至 `legacy/`（src 外，不打包不進 CI）；刪除空目錄 `engines/zipline_adapter/adapters/`
> **v1.3 變更（2026-06-16, ADR-027）**：策略契約 + registry（`strategies/protocol.py`）；**每隻策略自包含**（config + 純邏輯 + `runner.py` 同夾）；新增可複製骨架 `strategies/_template/`、橫斷面共用 `strategies/common/panel.py`、four_layer 純 sim 下移 `sim.py`；`research/runners.py` 降為 aggregator；平台對 `get_strategy(name)` dispatch，不再硬綁 four_layer
> **v1.4 變更（2026-06-17, ADR-029）**：研究流程標準化。**刪除** `backtest_platform/scripts/`（7 支 `inst_flow_*` 一次性腳本）；**新增** `research/workflows/`（通用工作流 `config`/`loader`/`doe`/`go_gates`/`truth_gate`/`paper_replay`，全走 ADR-028 dispatch）；**每隻策略加** `strategies/<name>/research_config.py`（宣告 DOE/GO_GATES/TRUTH_GATE/PAPER_REPLAY）；新增 `api/routers/research_workflows.py`（`POST /research/workflows/{workflow}` + `GET /research/workflows/{strategy}`）。新增策略寫一個 `research_config.py` 即參與所有工作流。

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
├── legacy/                       # ★ ADR-026 封存樹（src 外，不打包不進 CI）；契約見 legacy/README.md
│   ├── README.md
│   ├── strategies/multi_factor/  # 已從 src 搬出（零 production 引用的葉子策略實驗）+ 其測試
│   ├── spikes/                   # 原 sprint_0_spikes/（M2 啟動前 6 spike + RUNBOOK + gate_review）已封存
│   └── scripts/                  # 非 inst_flow_* 的一次性 momentum / DOE / candidate-D / factor-baseline 驗證腳本
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
│   ├── strategy_config.py        # StrategyConfig (Pydantic frozen) + four_layer presets
│   └── settings.py               # ★ ADR-027 Stage 2 — 集中環境設定 (Settings/BaseSettings)：憑證+Postgres+路徑，取代散落 os.getenv
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
├── strategies/                   # ★ M2 改名 — 多策略 namespace（每隻策略自包含 config+邏輯+runner）
│   ├── __init__.py
│   ├── protocol.py               # ★ ADR-027 — 策略契約 + registry（StrategyRunner / StrategyRun / register_strategy / get_strategy）
│   ├── _template/                # ★ ADR-027 — 可複製的策略撰寫骨架（玩家複製此夾→填 alpha）；註冊為 "template"（等權買進持有 baseline）
│   │   ├── __init__.py
│   │   ├── strategy.py           # TemplateConfig + backtest_template（純函式；填你的訊號邏輯）
│   │   ├── runner.py             # TemplateRunner（4 行 adapter：建 panel→跑 backtest→回 StrategyRun）
│   │   └── README.md             # 撰寫 checklist + I/O 契約說明
│   ├── common/                   # ★ ADR-026/027 — 中立共用層（策略間零互相依賴）
│   │   ├── __init__.py           # TRADING_DAYS / clean_returns / rebalance_dates / vol_target re-export
│   │   ├── mechanics.py          # 再平衡日曆 + 波動目標部位 + 報酬清洗（原 momentum 私有函式抽出，ADR-026）
│   │   └── panel.py              # ★ ADR-027 — 橫斷面策略共用：column_panel / flow_panels / panel_metrics（用 validation.metrics）
│   ├── four_layer_resonance/     # M1 四層共振策略（診斷證實負 edge，待砍）
│   │   ├── __init__.py           # 對外 re-export (compute_scores, compute_signals, ...)
│   │   ├── indicators.py         # RSI / KD / MACD / SwingHigh/Low
│   │   ├── scoring.py            # compute_scores（四層計分）
│   │   ├── signals.py            # compute_signals + evaluate_bar
│   │   ├── sim.py                # ★ ADR-027 — 純 close-to-close 組合 sim helper（原 is_harness 私有，下移至策略層）
│   │   └── runner.py             # ★ ADR-027 — FourLayerRunner（per-stock event-driven，註冊 "four_layer"）
│   ├── momentum/                 # ★ v0.8 新增 — 跨截面 12-1 動能（Jegadeesh-Titman）；ADR-026 解耦後改依賴 common
│   │   ├── __init__.py           # MomentumConfig / backtest_momentum re-export
│   │   ├── strategy.py           # MomentumConfig + backtest_momentum（純函式 over 價格面板）
│   │   └── runner.py             # ★ ADR-027 — MomentumRunner（註冊 "momentum"）
│   └── inst_flow/                # ★ 正式 paper-ready 候選（ADR-024/025）；依賴 common（非反向挖 momentum）
│       ├── strategy.py           # InstFlowConfig + backtest_inst_flow
│       ├── signal_fn.py          # paper/live 訊號函式
│       └── runner.py             # ★ ADR-027 — InstFlowRunner（註冊 "inst_flow"）
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
| `strategies/momentum/` | | | ✅ v0.8（12-1 跨截面動能 + IS harness + MOMENTUM_GATE；證平台 strategy-agnostic） | | |
| `adapters/data_bundle/` | | ✅ | | | |
| `adapters/data_feed/` | | | | ✅ | |
| `adapters/brokers/paper_broker.py` | | | | ✅ | |
| `adapters/brokers/shioaji_broker.py` | | | | | ✅ |
| `engines/vectorbt_adapter.py` | | | ✅ | | |
| `validation/` | | | ✅ | | |
| `orchestration/` | | | ✅ v0.7 daily_flow（fail-fast staged engine + cli，Prefect-optional；real collaborator 接線 = 7.D.3 follow-up） | | |
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
- `sprint_0_spikes/` 已於 ADR-026 封存至 `legacy/spikes/`（保留溯源，不打包不進 CI）
- 一致性比嚴格遵守模式更重要
