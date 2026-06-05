# frontend/GOAL.md — backtest_platform 前端開發北極星

> **這是什麼**：開發本專案 React 前端時的**常駐目標 + 硬約束 + 建置順序**。每次動前端先讀本檔。
> **目標**：在 monorepo 頂層 `frontend/` 建出完整 React app，依既有設計與契約把 17 頁建出來並串接 FastAPI 後端。
> **狀態**：M3 目標。後端僅 11/71 端點 shipped，其餘 pending —— 見 §6。
> **路徑慣例**：以下 `dev_docs/...` 為 repo 根相對；從 `frontend/` 看是 `../dev_docs/...`。

---

## 1. 真相源（一律「讀這些文件」，不要自己重新發明）

| 你要什麼 | 讀這份 |
| :--- | :--- |
| 系統前後端架構地圖 | `dev_docs/00_system_architecture_overview.md` |
| 前端技術棧 / 資料夾結構 | `dev_docs/12_frontend_architecture_specification.md` |
| **前後端 REST 契約**（envelope / 5 前綴 / TTL / auth / 端點帳本）| `dev_docs/25_fe_be_rest_contract.md`（OpenAPI 為機器真相）|
| 設計 token（Grok 單色）| `dev_docs/web_design/global/02_backtest_platform_brand_system.md` |
| 三區 IA / 旅程 / sidebar | `dev_docs/web_design/03_uiux_benchmark_and_reinforcement_plan.md` §4.7 / §5.2 |
| 每頁規格（細節：sections/元件/四態/RWD）| `dev_docs/web_design/pages/<page>.md` |
| 可貼的組裝 Master Prompt（17 份齊全）| `dev_docs/web_design/assembly/<page>_integrated.md` |
| **視覺稿 / 版面構圖（每頁 frame 佈局）** | `dev_docs/web_design/pages/design.pen`（Pencil canvas JSON，22 frame、token 化 Grok 單色；**Phase 2 建頁的視覺真相**）|

> **三者分工**：`assembly/` 給結構與行為（要做什麼）、`design.pen` 給**視覺佈局/構圖/間距/層級**（長什麼樣）、`pages/<page>.md` 給細節規格（四態/copy/RWD）。建頁時三者對齊；版面有歧異以 `design.pen` 對應 frame 為準。
| 後端 | `backtest_platform/src/backtest_platform/api/`（跑 `uvicorn backtest_platform.api.app:app`，契約在 `GET /openapi.json`）|

---

## 2. 硬約束（不可違反）

1. 只動 `frontend/`；**禁止改後端任何 Python 邏輯**，只透過 REST 消費（後端收口是另一條 goal，見 §6）。
2. 型別一律由 OpenAPI 生成（`openapi-typescript` → `src/types/api.gen.ts`），**禁手寫 API 形狀、禁臆造端點**。
3. 所有 HTTP 走單一 client（`src/services/http.ts`）：解 envelope `{success,data,error,meta}`、帶 static Bearer slot、快取 TTL 讀 `meta.ttl`。realtime 用 polling，唯一 WebSocket 是 `/ws/positions/live`（M5，先留接口）。
4. 視覺 100% 用 Grok 單色 token（CSS vars from `global/02`）：**無陰影、flat 1px border #2A2A2A、button 白底 pill 12px、focus 單色白環 rgba(245,245,245,.7)、數值 Geist Mono tabular-nums**。禁舊 teal、禁彩色品牌色（漲跌 gain/loss + ↑↓ 是唯一彩色）。
5. 每個 section 四態完備：default / loading(skeleton) / empty / error，且 error≠empty。
6. a11y：文字 WCAG AA、KPI 數值 AAA、漲跌「色+符號」雙編碼、表格列鍵盤可 drill-down。
7. RWD：Desktop ≥1280 / Tablet 768–1279 / sidebar→drawer @<1024（**兩態，不用 icon-rail**）；ResearchTable / 艦隊 / 密集表 @<1024 **橫向捲動不轉 card**。
8. **端點未 live 的，渲染規格的 empty/pending 態（`meta.data_source:"pending_m4"`），絕不假造數字。**

---

## 3. 目標結構（`frontend/src/`，per doc 12 §6）

```
frontend/src/
├── types/        api.gen.ts(openapi-typescript 產, 禁手改) + domain.ts(view-model)
├── services/     http.ts(envelope 解包+Bearer) / queryClient.ts(TTL←meta.ttl) / ws.ts(單一 /ws/positions/live, M5)
├── features/     research/ · monitor/ · system/ · home/   (三區 IA = feature roots)
│                   每 feature: components/ hooks/(useXxxQuery) api/(typed fns) pages/
├── components/   共用基底(Button 白 pill / KPICard / StatusBadge / DataTable / ResearchTable /
│                   ChartFrame / CompareChart / CodeEditor / Cmd-K / FirstRunEmptyState)
├── layouts/      AppShell(三區 ZoneNav + Cmd-K + drawer @<1024)
├── pages/        路由葉  ·  stores/  Zustand(僅 UI 狀態)  ·  styles/ tokens.css(源 global/02)
└── hooks/  utils/
```

技術棧（ADR-015 / doc 12）：React + TypeScript strict + Tailwind + TanStack Query + URL state + 輕量 Zustand + Recharts/Plotly.js + Monaco + React Router + Vite + Vitest/Playwright。

---

## 4. 17 頁 → feature 對映（每頁都有 assembly 可直接照做）

| feature | 頁面（pages/ + assembly/<page>_integrated.md）| route |
| :--- | :--- | :--- |
| `research/` | research_01_strategy_library / research_02_run_new / research_03_runs_table / research_04_run_report / research_05_compare / research_06_sweep / research_07_validate_gate / research_08_promote / research_trade_review | `/research/*` |
| `monitor/` | monitor_a_performance / monitor_b_positions / monitor_c_signals / monitor_d_risk / monitor_fleet | `/monitor`、`/monitor/*` |
| `system/` | system_data / system_alerts | `/system/*` |
| `home/` | home_overview | `/` |

> 每頁照其 `assembly/<page>_integrated.md`（已 17 份齊全）；接後端用 §6 typed hook。

---

## 5. 建置順序（分階段，做完回報、確認再下一步）

**禁止一發大招把 17 頁一次做完。** 每階段做完回報：做了什麼、對應哪份規格、四態/typegen 是否通過、還缺什麼。

### Phase 0 — Scaffold
建 `frontend/`：Vite + React + TS(strict) + Tailwind + React Router + TanStack Query + Zustand + Recharts + Plotly.js + Monaco；vitest + playwright。建 §3 `src/` 結構。`styles/tokens.css` 落 `global/02` Grok token（dark/light CSS vars）接進 tailwind。`services/{http,queryClient,ws}`。`layouts/AppShell`（三區 sidebar + Cmd-K 佔位 + drawer@<1024）。**跑得起來 + tsc strict 無錯 = 通過。**

### Phase 1 — 契約型別 + API client
跑後端抓 `/openapi.json` 存 `frontend/openapi.json` → `openapi-typescript` 產 `src/types/api.gen.ts`。每 zone 一個 typed API 模組（只包既有端點，標 shipped vs pending 依 doc 25 帳本）。寫 3–5 個 TanStack Query hook 打**真實 shipped 端點**驗證 envelope 解包。

### Phase 2 — 逐區建頁（順序：research → system → monitor → home）
一次一頁，**三源對齊**：`assembly/<page>_integrated.md`（結構/行為）+ `design.pen` 對應 frame（視覺佈局/構圖/間距）+ `pages/<page>.md`（細節/四態/RWD）；接 Phase 1 typed hook；端點 pending 就渲染 empty/pending 態。順序理由：research 區真實資料最多 → system → monitor（多為 deferred-stub）→ home（依賴前三區的 BFF 聚合，最後做）。
> design.pen 是 JSON canvas，可程式讀取對應 frame（frame name = 頁名，如 `Research · Runs Table`）取其子元素佈局/座標/token，據以還原版面。

---

## 6. 後端串接（契約 = 唯一耦合）

- 前後端只透過 doc 25 REST 契約：envelope、裸根 5 前綴 `/runs /research/* /monitor/* /system/* /home/*` + `/health` + `/ws/*`、static Bearer、polling+TTL、單一 WS。
- **現況：僅 11/71 端點 shipped**（44 ready-but-unwired / 12 needs-work / 4 monitor deferred-stub）。所以「完整串接」今天 = **11 真接 + 其餘 pending 態**。
- 要更完整需**平行的後端 goal**（不在本前端 goal）：
  > 依 `dev_docs/00` §6 NOW + `dev_docs/25` 端點帳本，在 `backtest_platform/src/backtest_platform/api/routers/` 新增 `research.py / monitor.py(stub) / system.py / home.py(BFF 聚合)`，把 44 ready 端點接線（複用既有 `research/`、`risk/`、`monitoring/` 模組與 `api/envelope.py`，禁重造信封），在 `app.py` 註冊；monitor 區回 typed empty + `meta.data_source:"pending_m4"`；每 router 配 `tests/api/routers/` 測試，覆蓋率維持 ≥ 現況。

---

## 7. 驗收（Definition of Done，每頁）

- [ ] 照對應 `assembly/<page>_integrated.md` 的 sections 全到位
- [ ] 四態完備（default / loading / empty / error），error≠empty
- [ ] 型別來自 `api.gen.ts`（無手寫 API 形狀、無臆造端點）
- [ ] pending 端點渲染 pending 態，**無假造數字**
- [ ] Grok 單色：無陰影、border #2A2A2A、白 pill、focus 白環、Geist Mono；無 teal、無彩色品牌色
- [ ] a11y AA / KPI AAA / 漲跌雙編碼 / 鍵盤 drill-down
- [ ] RWD 三斷點；密集表 @<1024 橫向捲動不轉 card
- [ ] `tsc --noEmit` strict 通過；vitest 該頁元件四態測試通過

---

## 8. 提示詞寫作原則（往後複用）

1. **引用，不重述**——規格在 `pages/` 與 `assembly/`，提示詞只「指路」。
2. **契約優先**——先 OpenAPI 生型別再寫頁；明令「禁臆造端點」防幻覺。
3. **分階段 + 要回報**——17 頁一次做必崩；每階段剎得住車。
4. **約束寫死成清單**——四態 / Grok 無陰影 / 雙編碼 / 不假造數字，列硬約束它才遵守。
5. **pending 不可造假**——未 live 渲染 pending 態，不做出「看起來能跑、其實全假資料」的前端。
