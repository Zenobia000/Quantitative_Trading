# 系統架構總覽 — backtest_platform

> **定位**：單一入口的薄地圖。不重新推導架構，只把現行模組收斂成一張支柱地圖，並指向各權威文件。歧異一律以右欄權威 + 實際 codebase 為準。

## 產品定位

backtest_platform 是一座 **個人量化 edge 驗證工廠 + 晉升管線**：single-user、standalone（單機自託管、localhost-only 綁定，[ADR-031](./adrs/ADR-031-standalone-auth-decision.md)）、台股專用。策略是消耗品、審判庭（PBO/DSR/WFA/survivorship-clean 兩段驗證閘，[ADR-025](./adrs/ADR-025-two-stage-validation-gate-and-paper-promotion.md)/ADR-030）是核心資產、連續 NO-GO 是平台正常運作的證據。完整敘事見 [02 PRD v4.0](./02_project_brief_and_prd.md)。

---

## 1. 一頁總覽

```
┌─ 後端：模組化單體 + Pure-function 核心 ──────────────┐   ┌─ 前端：React 19 SPA ───────┐
│  資料 → 策略契約 → 研究工作流 + 審判庭 → 編排/Paper  │   │  三 zone: Research/Monitor  │
│  Python src-layout / FastAPI（15 router）            │   │  /System + Home + Cmd-K     │
│  zipline-reloaded + vectorbt 雙引擎（研究主力=離線   │   │  TS strict + Tailwind       │
│  sim + panel runner）/ FinLab 主 + FinMind fallback  │   │  + TanStack Query           │
│  / parquet+manifest / TimescaleDB                    │   │                             │
└──────────────────────────┬───────────────────────────┘   └──────────────┬──────────────┘
                           │           REST 契約（唯一耦合）              │
                           └──── doc 25 envelope / 裸根 5 前綴 / OpenAPI ──┘
```

- **後端 = 模組化單體**：純函式 domain（策略計分、validation、risk 全零 IO），外部系統（資料源 / 券商 / 引擎）以 adapter 隔離。
- **唯一耦合 = REST 契約**（[doc 25](./25_fe_be_rest_contract.md)）：前後端只透過 HTTP envelope 溝通，OpenAPI 為機器真相。
- **CI 三 job hard gate**：pytest+coverage / tsc+vitest / contract-drift；契約漂移不過即擋。測試現況 1116 passed、coverage ~92.6%。

---

## 2. 五支柱地圖

以「假設 → 判決 → 晉升」的價值鏈排列。每支柱對應 `backtest_platform/src/backtest_platform/` 現行模組。

| 支柱 | 現行模組 | 職責 | 權威文件 |
| :--- | :--- | :--- | :--- |
| **① 資料層** | `data/`（finlab_source 主 / finmind_etl fallback / db_reader / db_writer / universe_builder）、`adapters/data_bundle/`、`config/universe.py` | FinLab 付費全史（survivorship-clean）主源、FinMind 免費 fallback、parquet 快取 + manifest 血統、TimescaleDB telemetry | [21 資料契約](./21_data_contract.md) |
| **② 策略契約層** | `strategies/protocol.py`（`StrategyRunner` + registry）、`strategies/conformance.py`、`strategies/{four_layer_resonance,momentum,inst_flow,_template}/`、`strategies/common/`、`engines/`（zipline event 引擎；`engines/protocol.py` 已 DEPRECATED） | 平台↔策略接縫畫在**輸出**（`StrategyRun`）；name→runner registry dispatch；per-strategy `gate` 宣告；每隻策略自包含（config + 純邏輯 + runner） | [ADR-027](./adrs/ADR-027-strategy-contract-and-registry.md)/[ADR-028](./adrs/ADR-028-strategy-dispatch-contract.md) |
| **③ 研究工作流 + 審判庭** | `research/workflows/`（doe / go_gates / truth_gate / paper_replay / universe）、`research/`（is_harness / runs_store / sweep / promotion_service）、`validation/`（two_stage_gate / dsr / pbo / wfa / gate_state / gate_machine） | **核心資產**。策略以 `research_config.py` 宣告、平台 dispatch 執行；兩段閘（真偽閘 hard-fail + 配置閘 sizing）判 REAL/REJECTED | [ADR-029](./adrs/ADR-029-research-workflow-standardization.md)/[ADR-032](./adrs/ADR-032-survivorship-universe-workflow.md)、[ADR-025](./adrs/ADR-025-two-stage-validation-gate-and-paper-promotion.md)/ADR-030 |
| **④ 編排 + Paper 運維** | `orchestration/`（daily_flow staged engine + collaborators）、`runtime/`（market_reader / paper_daemon）、`adapters/brokers/paper_broker.py`、`risk/`（risk_gate 12 檢查 + circuit_breaker）、`monitoring/`（influx_writer / discord_notifier / alert_rules） | ETL→signals→risk→orders→log 每日鏈；paper 收 live OOS；pre-trade 風控 + 三級熔斷；Discord 告警 | [24 風控規格](./24_risk_management_spec.md)、[23 部署拓撲](./23_deployment_topology.md) |
| **⑤ 介面層** | `api/`（app 工廠 + envelope + 15 router）、`frontend/`（React 19、三 zone + Home + Cmd-K、17 路由） | 裸根 5 前綴 REST；研究時段 CLI-first、GUI 檢視；運維時段 GUI + Discord | [25 REST 契約](./25_fe_be_rest_contract.md)、[12 前端架構](./12_frontend_architecture_specification.md) |

> **依賴方向鐵律**：`strategies → common/validation`、`research → strategies registry`、`api/orchestration → research/data/adapters`；`validation` 不 import `strategies`（無循環）。完整 DAG 見 [09](./09_file_dependencies_template.md)。

---

## 3. 後端結構（src-layout）

`backtest_platform/src/backtest_platform/`，結構真相源見 [08](./08_project_structure_guide.md)。三組獨立 Click CLI（無 console_scripts）：

- `research/cli.py` — `doe` / `go-gates` / `truth-gate` / `paper-replay` / `build-universe`（研究工作流，`--dry-run`）+ run 帳本
- `orchestration/cli.py` — daily flow 執行（staged engine）
- `engines/zipline_adapter/cli.py` — `ingest` / `backtest-run` / `list-bundles`（zipline event 引擎）

HTTP 入口：`uvicorn backtest_platform.api.app:app`（綁 `127.0.0.1`）。

---

## 4. 前端結構（React 19 SPA）

`frontend/src/`，技術棧與分層見 [12](./12_frontend_architecture_specification.md)：

```
frontend/src/
├── app/         router.tsx（17 路由）+ nav.ts（三 zone + Cmd-K 命令源）
├── features/    research/ · monitor/ · system/ · home/   ← 三 zone = feature roots
│                  每 feature: pages/ hooks/ api/(typed fns) components/
├── types/       api.gen.ts（openapi-typescript 產，禁手改）
└── services/    http.ts（envelope 解包）/ queryClient
```

三 zone 職責：Research（研究迴圈主軸）、Monitor（live 艦隊子視圖，gated 於 paper-ready 策略）、System（bundle/ingest/alerts）；Home 為 root cockpit，Cmd-K（⌘K/Ctrl+K）全域跳轉。

---

## 5. 前後縫 — REST 契約（唯一耦合）

真相源 [25](./25_fe_be_rest_contract.md)；機器真相 = OpenAPI（`/openapi.json`）。

- **Envelope**：`{success, data, error{code,message,detail}, meta}`，由 `api/envelope.py` 定義；404/422/500 同一形狀。
- **裸根 5 前綴**（無 `/api`、無 `/v1`）：`/runs`、`/research/*`、`/monitor/*`、`/system/*`、`/home/*` + `/health` + `/strategies` + `/gate` + `/metrics`。
- **Auth**：無 app 層 auth，邊界 = loopback bind（[ADR-031](./adrs/ADR-031-standalone-auth-decision.md)）。
- **型別鎖步**：`openapi-typescript /openapi.json → frontend/src/types/api.gen.ts`，CI contract-drift job 守門。

---

## 6. 剩餘路線（現況 → 里程碑）

研究迴圈 + 審判庭 + 前端三 zone 已完成；`inst_flow` 於 survivorship-clean universe 工作流平台化後重驗中（fallback 態續 REJECTED，見 [16 WBS §1](./16_wbs_development_plan.md)）。剩餘關鍵路徑：修好審判庭 → 重驗 inst_flow → **after-close 排程器收 live OOS** → 3 個月 paper → M5 小倉位實盤（2027-Q2）。詳見 [17 master plan](./17_m2_to_m5_master_plan.md)。
