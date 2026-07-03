# 專案結構指南 — backtest_platform

> **版本：** v1.1 | **更新：** 2026-05-31
> **架構圖**：目錄對應 C4 **L3-A Application** 元件，見 [05_architecture_and_design_document.md §1.1](./05_architecture_and_design_document.md)
> **v1.1 變更**：對齊 M2 重組（commit `ae869f5`）— `strategy/` 改名 `strategies/four_layer_resonance/`、新增 `adapters/` `orchestration/` `monitoring/` `dashboard/`、新增 `sprint_0_spikes/`、移除原規劃但未實作的 `live/`（功能併入 `adapters/brokers/`）
> **v1.2 變更（2026-06-16, ADR-026）**：抽出 `strategies/common/`（中立回測機制單一真實來源，解策略間 leaky abstraction）；`multi_factor` / spikes（原 `sprint_0_spikes/`）/ 舊驗證 scripts 封存至 `legacy/`（src 外，不打包不進 CI）；刪除空目錄 `engines/zipline_adapter/adapters/`
> **v1.3 變更（2026-06-16, ADR-027）**：策略契約 + registry（`strategies/protocol.py`）；**每隻策略自包含**（config + 純邏輯 + `runner.py` 同夾）；新增可複製骨架 `strategies/_template/`、橫斷面共用 `strategies/common/panel.py`、four_layer 純 sim 下移 `sim.py`；`research/runners.py` 降為 aggregator；平台對 `get_strategy(name)` dispatch，不再硬綁 four_layer
> **v1.4 變更（2026-06-17, ADR-029）**：研究流程標準化。**刪除** `backtest_platform/scripts/`（7 支 `inst_flow_*` 一次性腳本）；**新增** `research/workflows/`（通用工作流 `config`/`loader`/`doe`/`go_gates`/`truth_gate`/`paper_replay`，全走 ADR-028 dispatch）；**每隻策略加** `strategies/<name>/research_config.py`（宣告 DOE/GO_GATES/TRUTH_GATE/PAPER_REPLAY）；新增 `api/routers/research_workflows.py`（`POST /research/workflows/{workflow}` + `GET /research/workflows/{strategy}`）。新增策略寫一個 `research_config.py` 即參與所有工作流。
> **v1.5 變更（2026-07-03, ADR-037）**：**刪除** `engines/` 樹（zipline stub 引擎 + `zipline_adapter/`，~2271 LOC）與 `pipeline.py`（legacy M1 CLI）、`dashboard/` 空殼、`monitoring/influx_writer.py`、`validation/full_report.py` + `resampling.py`、`research/momentum_harness.py`（thin shim）。**下放** `engines/.../parquet_cache.py`、`finmind_bundle.py`（僅 ingest 路徑）至 `data/`——它們是資料層而非引擎層。sim 為唯一引擎。
> **v1.6 變更（2026-07-03, ADR-039）**：**新增** `research/evaluation/` 套件（profile 編排層，primitives 之上不動 primitives）+ `research/candidate_state.py` / `candidate_store.py` / `live_oos_queue.py`（候選池狀態機 + live-OOS 人為選取層）；新增 `api/routers/research_evaluation.py` + `research_candidates.py`（9 端點：profiles×2 / evaluations(+report) / candidates×4 / live-oos queue）。CLI 加 `evaluate` + `candidates` 子命令。所有評估結果（含失敗/弱/負）寫 append-only JSONL。

---

## 設計原則

- **按功能組織**：每個 sub-package 為一個明確職責
- **明確職責**：`config/` = 參數、`data/` = IO、`strategies/` = 策略邏輯、`adapters/` = 廠商接口、`validation/` = 統計檢驗、`orchestration/` = 排程、`monitoring/` = 監控（前端見 `frontend/`）
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
├── __init__.py                   # 版本 + v2.md（legacy）章節對照註記
│
├── config/                       # 純資料層設定
│   ├── settings.py               # 集中環境設定（憑證 / Postgres / 路徑）
│   └── universe.py               # 中立 DEFAULT_UNIVERSE（策略 research_config 由此 import，無 zipline 依賴）
│
├── data/                         # ETL + 血統
│   ├── finlab_source.py          # FinLab 主資料源（全史 + 下市股；ingest_universe_finlab）
│   ├── finmind_etl.py            # FinMind fallback ETL（三表 → parquet，原子寫）
│   ├── parquet_cache.py          # parquet 快取讀取（ADR-037 由 engines/ 下放；EODParquetFeed 用）
│   ├── finmind_bundle.py         # FinMind universe 批次 ingest（ADR-037 下放；collaborators ingest 路徑）
│   ├── adjustment.py             # 除權息還原
│   ├── universe_builder.py       # point-in-time universe 過濾
│   ├── universe.py               # universe 輔助
│   ├── bundle_registry.py        # 掃 data/parquet* manifest → bundle 讀模型（GET /system/bundles 後端）
│   ├── db_writer.py / db_reader.py  # TimescaleDB upsert / telemetry 讀取
│   └── schemas.py                # Pydantic 資料 schema
│
├── strategies/                   # ★ 策略契約層（ADR-027/028）
│   ├── protocol.py               # StrategyRunner Protocol + GateSpec + registry（register/get/list）
│   ├── conformance.py            # 契約 conformance gate（parametrized 全 registry；gate keys ⊆ metrics）
│   ├── common/                   # 中立回測機制（clean_returns / rebalance_dates / vol_target / trim_overlap / panel）
│   ├── _template/                # 新策略複製骨架（config + 純邏輯 + runner 自包含）
│   ├── four_layer_resonance/     # legacy 契約實作之一（ADR-023 判負 edge；registry 對照標本）
│   ├── momentum/                 # 12-1 動能（NO-GO，ADR-023）
│   ├── inst_flow/                # 三大法人資金流（REJECTED @ 真實成本，見 inst_flow_truth_gate_verdicts）
│   └── reversal/                 # 短期反轉（做多近期輸家；預註冊 weekly/5/skip1/decile，驗證待跑）
│
├── research/                     # 研究迴圈
│   ├── workflows/                # ★ 平台工作流（ADR-029/032）：doe / go_gates / truth_gate / paper_replay / universe
│   │   ├── config.py             # 各工作流 frozen config（含 TruthGateConfig.parquet_dir / UniverseConfig）
│   │   └── loader.py             # 依策略名載入 research_config 宣告
│   ├── evaluation/               # ★ 評估編排層（ADR-039）：profile 之上 primitives 不動
│   │   ├── profiles.py           # 四內建 profile registry（契約真相源 = evaluation_profile.schema.json examples）
│   │   ├── orchestrator.py       # evaluate(strategy, profile)：wrap doe/go_gates/truth_gate/single_run → RunBundle
│   │   ├── result_builder.py     # RunBundle + profile → 契約 EvaluationResult（verdict/checks/lineage/data_gaps）
│   │   ├── scorecards.py         # 五維 scorecard（per-metric pass/warn/fail/not_available，誠實標 gap）
│   │   ├── report_pack.py        # summary/metrics/scorecards/report.md + manifest（+ sha256）
│   │   └── store.py              # evaluations.jsonl（append-only，含失敗者）
│   ├── candidate_state.py        # ★ 候選狀態機（ADR-039，純函式，全轉移可測）
│   ├── candidate_store.py        # ★ 候選池 + candidate_decisions.jsonl（override 強制 reason）
│   ├── live_oos_queue.py         # ★ live-OOS 人為選取 queue（Goal 10 才接 paper replay）
│   ├── is_harness.py             # run_and_judge（gate 隨策略 dispatch）+ load_merged_parquet
│   ├── run_config.py             # RunConfig（strategy + params，ADR-028）
│   ├── runs_store.py / run_series_store.py / run_tags_store.py  # runs ledger（JSONL）
│   ├── run_persist.py            # persist_run：ledger append + best-effort runs 表鏡射（A0）
│   ├── batch.py                  # run_batch：spec × 股票組 fan-out，有界 ThreadPool + 生命週期鏡射（A1）
│   ├── promotion_service.py / promotion_store.py  # 晉升狀態機服務
│   ├── trials_counter_store.py   # 試驗計數（DSR deflation 審計）
│   ├── sweep.py / compare.py / validation_store.py / saved_views_store.py
│   ├── finlab_universe.py        # survivorship universe 選擇（select_survivorship_universe / cached_universe_symbols）
│   ├── momentum_harness.py       # 委派 runner 的相容層
│   ├── runners.py                # registry 聚合 re-export（相容層）
│   └── cli.py                    # 研究 CLI（run-is / runs / compare / validate / promote-check / sweep / doe / go-gates / truth-gate / build-universe / paper-replay / evaluate / candidates）
│
├── validation/                   # ★ 審判庭（純函式）
│   ├── two_stage_gate.py         # ADR-025 真偽閘 + 配置閘（TruthGateInput / SizingInput / evaluate_two_stage）
│   ├── portfolio_gate.py         # ADR-036 組合級證據軸 + pod 資本配置（combine_returns / sleeve_weights / apply_stop_outs）
│   ├── gate_state.py             # gate 準則（DEFAULT_GATE / MOMENTUM_GATE / PANEL_GATE）
│   ├── gate_machine.py           # IS→WFA→OOS 不可逆狀態機
│   ├── dsr.py / pbo.py / wfa.py  # 防過擬合統計（DSR 含輸入衛兵，ADR-030）
│   ├── metrics.py                # sharpe / cagr / maxdd 單一規範源
│   ├── full_report.py / tearsheet.py / resampling.py / trials.py / health_indicators.py
│
├── risk/                         # 風控（純函式、狀態注入）
│   ├── risk_gate.py              # 12 條 ex-ante 規則（EX-001..012）
│   ├── circuit_breaker.py        # 3 級熔斷狀態機
│   └── types.py                  # AccountState / Order / Position
│
├── orchestration/                # 每日流程引擎 + after-close 排程
│   ├── daily_flow.py             # staged ETL→signals→risk→orders→log（fail-fast）
│   ├── collaborators.py          # production 協作者工廠（真實倉位快照 + 批次現金遞減 + side 轉換）
│   ├── after_close.py            # after-close 排程核心（交易日/收盤後/冪等守門 + Discord 告警，全注入式）
│   └── cli.py                    # run / list-stages / after-close 子命令
│
├── runtime/                      # paper 執行
│   ├── paper_daemon.py           # 逐日重放 / 前進 daemon
│   ├── market_reader.py          # FinLab EOD 活 panel + make_position_signal_fn 通用 adapter
│   └── trading_calendar.py       # 台股交易日 gate（XTAI 日曆；未裝 extra 退化週一至五近似）
│
├── deploy/                       # after-close 排程範例（systemd user units + cron + 安裝 SOP）
│   ├── after-close.service / after-close.timer / after-close.cron.example / README.md
│
├── adapters/
│   ├── brokers/paper_broker.py   # 紙上券商（簡化撮合 + heat）；shioaji（M5）
│   └── data_feed/                # 讀取層 seam（ADR-035）：DataFeed Protocol + EODParquetFeed（realtime 延後）
│
├── api/                          # FastAPI（127.0.0.1，ADR-031）
│   ├── app.py                    # 15 routers + /health；統一 envelope
│   ├── routers/                  # runs / gate / metrics / strategies / research_* / monitor / system / home
│   ├── schemas.py / response_models.py / envelope.py / deps.py
│
├── monitoring/                   # Discord 告警 + alert rule engine
│   ├── alert_rules.py / discord_notifier.py
│
└── jobs/                         # 輕量背景 job（JSONL 快照 + daemon thread）
    └── job_runner.py / job_store.py / models.py
```

### 模組現況一覽

| 模組 | 狀態 | 備註 |
| :--- | :--- | :--- |
| `config/` `data/` `strategies/` `research/` `validation/` `risk/` | ✅ 現行 | 研究迴圈 + 審判庭主體 |
| `orchestration/` `runtime/` `adapters/brokers/paper_broker` | ✅ 現行 | paper 鏈 + after-close 排程器（cron/systemd 級，`deploy/` 附範例）已落地 |
| `api/` `monitoring/` `jobs/` | ✅ 現行 | 15 routers；Discord 告警 |
| `data/parquet_cache` `data/finmind_bundle` | ✅ 現行 | parquet 快取讀取 + FinMind universe ingest（ADR-037 由 engines/ 下放）|
| `adapters/data_feed/` | 🟡 seam | 讀取層介面已定義（DataFeed Protocol + EODParquetFeed，ADR-035）；realtime 實作延後、未 rewire 既有 caller |
| `adapters/data_bundle` | 空殼 | 保留套件位 |
| `adapters/brokers/shioaji_broker` | M5 | 實盤下單（未實作） |

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
│ data/        │  │ strategies/      │  │ adapters/      │
│ parquet_cache│  │ four_layer_*/    │  │ data_bundle    │
│ finmind_bundle│ │ (Domain 純函式)  │  │ data_feed      │
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
| ~~資料源（TEJ）~~ | ~~`TEJAPI_KEY`~~ | — | ADR-013 已棄用 TEJ 路徑；主路徑（FinLab/FinMind bundle）不依賴 TEJ |
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
