# 系統架構總覽 — backtest_platform（台股四層共振 研究/回測平台）

> **版本**：v1.0 ｜ **日期**：2026-06-05 ｜ **狀態**：架構真相地圖（前端 M3 才實作）
> **定位**：**單一入口的薄地圖**——不重新推導架構，只把散落的 5 大支柱與**定版資料夾結構**收斂在一處，並指向各權威文件。歧異一律以右欄權威為準。

## 0. 怎麼讀（5 支柱 + 決策 ADR）

| 你想找 | 權威文件 |
| :--- | :--- |
| 架構風格 / 分層 / 邊界 | `05_architecture_and_design_document.md` |
| **後端**資料夾結構 | `08_project_structure_guide.md`（v1.1 為真相）+ 本檔 §3 |
| **前端**結構 / 技術棧 | `12_frontend_architecture_specification.md` + 本檔 §4 |
| 部署拓撲（dev/staging/prod）| `23_deployment_topology.md` + 本檔 §6 |
| **前後端 REST 契約** | `25_fe_be_rest_contract.md`（OpenAPI 為機器真相）+ 本檔 §5 |
| 頁面職責 / 三區 IA / 旅程 | `web_design/03_uiux_benchmark_and_reinforcement_plan.md` §4.7 / §5.2 |
| 關鍵決策 | ADR-005/013(引擎)、ADR-009(三層儀表板)、ADR-015(React 升級)、ADR-021(契約合一) |

---

## 1. 一頁總覽

```
┌─ 後端：模組化單體 + 六角（ports/adapters）──────────┐      ┌─ 前端：React SPA（M3）──────┐
│  Domain(純) → Use-case → Port/Adapter → api/(BFF)  │      │  三區 IA: Research/Monitor  │
│  Python src-layout / FastAPI v0.6 / zipline+vectorbt│      │  /System + Home cockpit     │
│  TimescaleDB / FinLab+FinMind / Shioaji(M5)         │      │  React+TS+Tailwind(Grok 單色)│
└──────────────────────────┬─────────────────────────┘      └──────────────┬──────────────┘
                           │            REST 契約（唯一耦合）              │
                           └──── doc 25 envelope / 5 前綴 / OpenAPI ───────┘
                          部署：dev(WSL2) → staging(paper M4) → prod(GCP M5)
```

- **後端 = 模組化單體 + 六角**：domain 純函數（禁 import IO/adapters），外部系統（資料源/券商/引擎）以 adapter + Protocol 隔離。
- **前端 = React SPA**：三區 IA，經 Lovable 依 assembly Master Prompt 產出，token 化 Grok 單色。
- **唯一耦合 = REST 契約**（doc 25）：前後端只透過 HTTP envelope 溝通，OpenAPI 為機器真相。
- **`api/` 即 BFF**：無獨立 gateway；`/home/*` 在程序內聚合。

---

## 2. Repo 根結構（monorepo 雙頂層 app）

> **決策**：`frontend/` 為 repo 頂層 sibling，與 `backtest_platform/` 並列——Python src-layout 不動、Node 工具隔離、docker 兩個乾淨 build context。

```
Quantitative_Trading/
├── backtest_platform/        # 後端 app（EXISTS，src-layout，不遷移）
│   ├── pyproject.toml        #   套件設定 + optional extras（mainframe/engines/data_paid/api/ui/broker…）
│   ├── src/backtest_platform/#   見 §3
│   ├── tests/                #   鏡像 src 結構（~93% 覆蓋）
│   ├── docker/  docker-compose.yml   # 現 dev compose（infra 提升延後 M4）
│   └── reports/  scripts/
├── frontend/                 # 前端 app（NEW，M3 才 scaffold；見 §4）
├── infra/                    # NEW（M4）docker-compose.{dev,staging,prod}.yml + caddy/
├── dev_docs/                 # 00(本檔) + 05/08/12/23/25 + adrs/ + web_design/
└── tools/  docs/
```

---

## 3. 後端結構（六角 ports/adapters）

`backtest_platform/src/backtest_platform/`（與實際樹一致，2026-06-05 核對）：

| 層 | 模組 | 規則 |
| :--- | :--- | :--- |
| **Domain（純，禁 import IO/adapters）** | `strategies/four_layer_resonance/`（indicators/scoring/signals）、`config/strategy_config.py`（Pydantic frozen）、`validation/`（pbo/dsr/wfa/gate_machine/gate_state）、`risk/`（risk_gate/circuit_breaker）| domain ⊁ infra |
| **Use-case** | `research/`（runs_store/run_config/is_harness/sweep/compare/cli）、`orchestration/`（daily_flow/cli）| 編排 domain + infra |
| **Port** | `engines/protocol.py`（Engine Protocol）| 結構型介面 |
| **Adapter（引擎）** | `engines/zipline_adapter/`（cli/algorithms/bundles/validation）| 實作 Port |
| **Infra / adapters** | `adapters/`（brokers/paper_broker、data_bundle、data_feed）、`data/`（finmind_etl/db_writer/adjustment/universe）、`monitoring/`（alert_rules/discord_notifier/influx_writer）| adapters 之間不互 import |
| **BFF** | `api/`（app.py / envelope.py / deps.py / schemas.py + `routers/`）| 5 個 REST zone 前綴 owner（§5）|
| **入口 shim** | `pipeline.py`（M1 向後相容）| — |
| **待刪** | `dashboard/`（空，只 `__init__.py`）| 被 `frontend/` + `api/` BFF 取代；Grafana F–I 為外部（doc 20）。標記移除，非本次執行 |

**CLI（3 組獨立 Click，無 console_scripts）**：`research/cli.py`（run-is/runs）、`orchestration/cli.py`（run/list-stages）、`engines/zipline_adapter/cli.py`（ingest/backtest-run/list-bundles）。

---

## 4. 前端結構（M3 target，per doc 12 + 三區 IA）

> 技術棧（ADR-015 / doc 12）：React + TypeScript strict + Tailwind（Grok 單色 token，無陰影）+ TanStack Query（server state）+ URL state（filter/saved views）+ 輕量 Zustand（UI）+ Recharts/Plotly.js + Monaco + React Router + Vite + Vitest/Playwright。初版頁面由 **Lovable** 依 `web_design/assembly/<page>_integrated.md` 產出。

```
frontend/src/
├── types/        api.gen.ts（openapi-typescript 產，禁手改）+ domain.ts（view-model）
├── services/     http.ts（envelope 解包 + Bearer）/ queryClient.ts（TTL ← meta.ttl）/ ws.ts（單一 /ws/positions/live, M5）
├── features/     research/ · monitor/ · system/ · home/   ← 三區 IA = feature roots
│                   每 feature: components/ hooks/(useXxxQuery) api/(typed fns) pages/
├── components/   共用基底（Button 白 pill / KPICard / StatusBadge / DataTable / ResearchTable / ChartFrame / CodeEditor / Cmd-K / FirstRunEmptyState）
├── layouts/      AppShell（三區 ZoneNav + drawer @<1024）
├── pages/        路由葉（組合 feature pages）
├── stores/       Zustand（僅 UI 狀態，非 server state）
├── styles/       tokens.css（源 web_design/global/02_backtest_platform_brand_system.md）
└── hooks/  utils/
```

**17 份 page 規格 → feature 對映**（`web_design/pages/`）：

| Zone | 頁面 | 數 |
| :--- | :--- | :-: |
| `features/research/` | research_01..08 + research_trade_review | 9 |
| `features/monitor/` | monitor_a..d + monitor_fleet（/monitor zone home）| 5 |
| `features/system/` | system_data、system_alerts | 2 |
| `features/home/` | home_overview（root `/` cockpit）| 1 |

Assembly Master Prompt 14 份已存在，4 份（sweep/validate_gate/promote/system_*）+ 補強 3 頁（home/fleet/trade-review）隨 React 化補。

---

## 5. 前後縫 — REST 契約（唯一耦合）

> 真相源 `25_fe_be_rest_contract.md`；機器真相 = OpenAPI（`/openapi.json`）。

- **Envelope**：`{success, data, error{code,message,detail}, meta{total,page,limit,ttl,data_source}}`。
- **裸根 5 前綴**（無 `/api`、無 `/v1`）：`/runs`、`/research/*`、`/monitor/*`、`/system/*`、`/home/*` + `/health` + `/ws/*`。
- **Router 擁有權**：全在 `api/routers/`。現有 `runs/gate/metrics/presets`（v0.6 shipped，zero-refactor）；待新增 `research.py`(補 44 ready)/`monitor.py`(4 stub `data_source:"pending_m4"`)/`system.py`/`home.py`(BFF 聚合)。
- **Auth**：static Bearer（單人）。
- **Realtime**：HTTP polling + `meta.ttl`（研究 300s / 部位 60s / 訊號 30s）；長任務 = `202 {job_id}` + poll；**單一 WebSocket** `/ws/positions/live`（M5）。
- **型別**：`openapi-typescript /openapi.json → frontend/src/types/api.gen.ts`，前後端鎖步。
- **端點帳本 71**：11 shipped(v0.6) / 44 ready-but-unwired / 12 needs-work / 4 monitor deferred-stub。

```
React features/*/api ──HTTP──► 裸根 5 前綴 ──► api/routers/{zone}.py ──(程序內)──► research/ risk/ monitoring/
   useXxxQuery(TanStack)         envelope                BFF（含 /home 聚合）
   http.ts 解包 ◄── meta.ttl ── 快取/輪詢提示
   types/api.gen.ts ◄── OpenAPI typegen
```

---

## 6. 分階段建立（尊重 M0/M2 無 edge、前端 M3）

| 階段 | 後端 | 前端 | 部署 |
| :--- | :--- | :--- | :--- |
| **NOW (M2)** | 補 4 zone router（research/monitor stub/system/home）+ OpenAPI 匯出腳本 + import-linter 六角邊界 + 刪空 `dashboard/` | — | 現 dev compose（`backtest_platform/`）|
| **M3** | — | scaffold `frontend/`、openapi typegen、Lovable 17 頁（research → system → monitor → home）| — |
| **M4** | Monitor producers（翻 `pending_m4`→live）| 接 live 資料 | 提升 `infra/` compose + PaperBroker + Prefect（`orchestration/daily_flow.py`）|
| **M5** | `adapters/brokers/shioaji_broker.py` | `services/ws.ts` 接 `/ws/positions/live` | GCP e2-small + Caddy + Secret Manager |

> **鐵律**：前端 scaffold 不提前於 M3（現無 edge、API 約 44 端點未接線）。

---

## 7. 文件漂移狀態（2026-06-05 核對）

| # | 項目 | 狀態 |
| :-- | :--- | :--- |
| D1 | `strategy/` → `strategies/four_layer_resonance/` | ✅ 已修（doc 09 v1.1 banner + substitute 表）|
| D2 | doc 20 Streamlit 直連 SQL 已 superseded | ✅ 已修（doc 20 ADR-021 定位 banner：本檔餵契約非 host 契約）|
| D3 | doc 25 殘留「401/403」應統一 401（單人無 RBAC，403 不適用）| ⚠️ 待收口（doc 25 line 33/130 + doc 12 §7；建議由 contract-drift-sweep 工作線統一為 401）|

## 8. 既有資產（禁重建）

`api/app.py`（create_app + envelope handlers）、`api/envelope.py`（ok/fail 單一信封源）、`api/deps.py`、`api/schemas.py`、`engines/protocol.py`（Engine Port）、`research/runs_store.py`（runs ledger）、`strategies/four_layer_resonance/`、`config/strategy_config.py`（frozen 契約）。新增 router 一律 **extend `app.py` 註冊**、複用 `envelope.py`，不另造信封。

---

## 變更紀錄
- v1.0 (2026-06-05)：初版。收斂 05/08/12/23/25 + ADR 為單一入口架構地圖；定版 monorepo 雙頂層（frontend/ 頂層 sibling）、後端六角樹、前端三區樹、REST 縫、分階段建立表；記錄文件漂移狀態（D1/D2 已修、D3 待收口）。
