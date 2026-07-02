# 前端架構規範 — backtest_platform

> **版本:** v4.0 | **更新:** 2026-07-02 | **狀態:** 對齊實作（React 前端已落地）
> **決策依據:** [ADR-015](./adrs/ADR-015-dashboard-design-system-and-react-upgrade.md)（React 升級 + 設計系統）、[ADR-021](./adrs/ADR-021-unify-rest-contract-into-single-doc-and-openapi.md)（REST 契約合一）、[ADR-031](./adrs/ADR-031-standalone-auth-decision.md)（standalone auth = localhost-only）。
>
> **MECE 邊界**：本文件**只談技術視角**（stack / 分層 / 量化指標 / 工程化）。頁面職責、旅程、導航內容全部在 **`web_design/`**（前端 IA 真相源）。
>
> | 你想找的 | 看這份 |
> |---|---|
> | 用什麼框架、怎麼分層 | 12（本檔）§2 |
> | 設計令牌、元件分層 | 12（本檔）§3；token 真相源 `web_design/global/02_backtest_platform_brand_system.md` |
> | LCP / INP / CLS 數字目標 | 12（本檔）§4 |
> | 響應式斷點、a11y 標準 | 12（本檔）§5 |
> | 專案 file 組織、測試框架 | 12（本檔）§6 |
> | API client 技術選型 | 12（本檔）§7；**契約 [`25_fe_be_rest_contract.md`](./25_fe_be_rest_contract.md)** |
> | 哪些**頁面**存在、頁面職責 | `web_design/pages/`；路由清單見本檔 §2.3 |
> | 使用者旅程、三區 IA | `web_design/03_uiux_benchmark_and_reinforcement_plan.md` |

---

## 第 1 部分：架構目標（量化）

| 維度 | 目標 | 衡量指標 |
| :--- | :--- | :--- |
| **效能** | 載入與互動回應 | LCP, INP, CLS, TTI |
| **技術可用性** | 各裝置 / 輔助技術可達 | 響應式覆蓋率、a11y 通過率（AA 文字 / AAA KPI 數值）|
| **可維護性** | 單人迭代效率 | 複雜度、覆蓋率、契約型別對齊 |
| **可靠性** | 各狀態穩定呈現 | 四態完備率（default / loading / empty / error）|

> 本平台為**單人開發**；前端工程負擔是 ADR-015 明確接受的取捨（換取設計系統一致性與 a11y 天花板）。
> 「使用者完成目標的難易度」屬 IA 視角 → `web_design/03`。

---

## 第 2 部分：系統化分層

```
感知層    -- React 元件、Grok 單色 dark tokens、圖表（Recharts / Plotly.js）
互動層    -- 事件處理、表單驗證（對齊後端 Pydantic schema）
狀態層    -- Server State（TanStack Query）、URL State（filter / saved views）、輕量全域（Zustand）
通訊層    -- 單一 REST client（http.ts）、envelope 解包、TTL 快取
基礎設施  -- Vite 建置、Vitest / Playwright 測試、CI（GitHub Actions）
```

### 2.1 技術選型（已落地，見 `frontend/package.json`）

| 層級 | 技術 | 版本 |
| :--- | :--- | :--- |
| 框架 | **React** + **TypeScript strict** | 19 / 5.6 |
| 建置 | **Vite** | 6 |
| 樣式 | **Tailwind CSS**（token 化 Grok 單色）| 3.4 |
| 路由 | **React Router**（`createBrowserRouter`，三區 IA）| 7 |
| Server 狀態 | **TanStack Query**（快取 + TTL 輪詢）| 5 |
| 全域 UI 狀態 | **Zustand**（輕量）| 5 |
| 圖表 | **Recharts**（一般）+ **Plotly.js**（heatmap / parcoords / scatter）| 2 |
| 編輯器 | **Monaco**（`@monaco-editor/react`，策略 config authoring）| 4 |
| 型別生成 | **openapi-typescript**（OpenAPI → `api.gen.ts`）| 7 |
| 測試 | **Vitest** + Testing Library + **Playwright** | 2 / 1.49 |

> 後端為 **FastAPI REST API**；React 不直連 TimescaleDB（ADR-015 取捨），一律走 REST（§7）。

### 2.2 三區 IA（sidebar 導覽，真相源 `src/app/nav.ts`）

- **Research**（主軸）：策略研究者的研究迴圈入口。
- **Monitor**（telemetry-driven）：艦隊運維者的 live 子視圖，資料由 daemon 餵入（M4 前多為 typed-empty stub，§5.4 of doc 25）。
- **System**：資料管理、告警設定。
- **Home**（root `/`）：跨三區聚合的每日進場 cockpit。

### 2.3 路由清單（17 條，真相源 `src/router.tsx`）

| Zone | 路由 | 頁面 |
| :--- | :--- | :--- |
| Home | `/` | HomePage（cockpit）|
| Research | `/research/strategies` | 策略庫 |
| Research | `/research/runs/new` | New Run 設定 |
| Research | `/research/runs` | Runs Table |
| Research | `/research/runs/:id` | Run Report |
| Research | `/research/runs/:id/trades` | 逐筆覆盤 |
| Research | `/research/compare` | Compare |
| Research | `/research/sweep` | Sweep |
| Research | `/research/validate` | Validate gate |
| Research | `/research/promote/:strategyId` | Promote |
| Monitor | `/monitor` | 艦隊總控 |
| Monitor | `/monitor/performance` | 績效總覽 |
| Monitor | `/monitor/positions` | 部位狀態 |
| Monitor | `/monitor/signals` | 訊號日誌 |
| Monitor | `/monitor/risk` | 風控指標 |
| System | `/system/data` | 資料管理 |
| System | `/system/alerts` | 告警設定 |

> **Cmd-K CommandPalette** 為跨頁快速跳轉（Organism 級元件，§3）。ADR-029 研究工作流（doe / go_gates / truth_gate / paper_replay / build_universe）的 GUI 入口尚在收斂中，CLI + HTTP 為現行主路徑。

---

## 第 3 部分：設計系統（Grok 單色 dark）

> **Token 真相源**：`web_design/global/02_backtest_platform_brand_system.md`。以下為技術對接摘要，歧異以該檔為準。

### 設計令牌（Design Tokens）

| 類別 | 值 | 備註 |
| :--- | :--- | :--- |
| 背景 | bg-base `#0F0F0F` / surface `#1A1A1A` / input `#1E1E1E` / code `#161616` | dark-first |
| 邊框 | border `#2A2A2A` | **flat 1px 分層** |
| 文字 | text `#F5F5F5` / secondary / tertiary（明度階）| **無彩色品牌色** |
| 功能色 | gain `#22C55E`(↑) / loss `#F87171`(↓) / loss-aaa `#FCA5A5` / warning `#E9A60C` / error `#EF4444` | 唯一彩色＝漲跌，**配 ↑↓ 符號雙編碼** |
| 受控 data-viz 例外 | Categorical 8-色盤 / Diverging(gain↔灰↔loss) / Sequential 灰階 | 僅圖表內容區 |
| 字體 | UI: Inter / Noto Sans TC；**數值: Geist Mono**（tabular-nums）| KPI 數值對齊 |
| 圓角 | button pill 12px；sm4 / md8 / lg12 | — |
| **陰影** | **無（NO shadow）** | flat，改 1px border 分層 |
| Focus | **單色白環** `rgba(245,245,245,.7)` | 非彩色 ring |

### 元件分層（Atomic Design）

```
原子      → Button(白 pill / ghost)、Input、StatusBadge、Icon、Tag、ProgressBar
分子      → KPICard、FilterChip、SearchBar、FormField、ParamPill、GateBadge
組織      → Sidebar(三區)、Cmd-K CommandPalette、DataTable / ResearchTable(virtualized)、
            ChartFrame、CodeEditor(Monaco)、FirstRunEmptyState、PromotionStepper、WiredPage(四態殼)
模板      → AppShell(三區殼 + drawer @<1024)
```

> **Page = Template + 資料注入（TanStack Query hooks）**。共用基底元件集中於 `src/components/`，避免跨頁重複。

---

## 第 4 部分：效能策略（量化）

### Core Web Vitals 目標

| 指標 | 目標 | 優化策略 |
| :--- | :--- | :--- |
| LCP | < 2.5s | 預載關鍵資源、字型子集化（Geist Mono / Inter）|
| INP | < 200ms | Code Splitting、圖表懶渲染、減少主執行緒阻塞 |
| CLS | < 0.1 | **四態 skeleton 佔位**（固定高度避免 layout shift）|
| TTI | < 3s (4G) | 路由級懶載入 |

### 本平台特有效能規則

- **即時數據無進場動畫**：數據更新就地替換（瞬時切換），尊重 `prefers-reduced-motion`。
- **ResearchTable 虛擬化**：runs table 千列以 virtualization 渲染；**@<1024 橫向捲動不轉 card**（研究級密集表反模式）。
- **metrics-dict-first 低延遲迴圈**：先回結構化 metrics dict 秒判，重圖（tear sheet）按需 render。
- **快取 TTL 分級**：TanStack Query `staleTime` 讀 envelope `meta.ttl`（研究/驗證 300s、部位 60s、訊號今日 30s / 歷史 300s；對齊 25 §5.1）。長任務走 poll-status（submit → status → result，25 §5.2），不投機建 SSE。
- **四態完備**：每 section 必備 default / loading(skeleton) / empty / error，empty 與 error 明確區分（`WiredPage` 統一渲染）。

---

## 第 5 部分：技術可用性（量化標準）

### 響應式斷點（Tailwind 實際值）

| 名稱 | 寬度 | 行為 |
| :--- | :--- | :--- |
| sm | ≥ 640px | — |
| md | ≥ 768px | — |
| lg | ≥ 1024px | **≥1024 sidebar 展開；<1024 → drawer**；table→card（ResearchTable 除外，改橫向捲動）|
| xl | ≥ 1280px | Desktop 完整佈局 |

> sidebar 一律**兩態**（展開 ↔ drawer），不用 icon-rail。

### 無障礙（A11y）量化要求

- WCAG 2.2 **AA（一般文字 ≥4.5:1）**，**KPI 關鍵數值 AAA（≥7:1）**（loss 用 `#FCA5A5`）。
- **漲跌 / 狀態「顏色 + 文字 / 符號」雙編碼**（↑↓ / ✓✗ / PASS-FAIL），色盲友善。
- 語義化 HTML、ARIA；鍵盤完整可操作，**表格列可 focus + Enter drill-down**。
- **focus-visible 單色白環** `rgba(245,245,245,.7)`（非彩色）。

### 國際化（i18n）

- **繁體中文為主**（單一 locale）；技術術語 / 指標名保留英文（Sharpe、MDD、PBO、DSR）。
- 日期 / 數字以 **Intl API** 格式化（價格 / 績效 tabular-nums 對齊）；無 RTL 需求。

---

## 第 6 部分：工程化實踐

### 專案 file 組織（`frontend/src/`，依 IA 三區）

```
frontend/src/
├── app/            # nav.ts（三區導覽）、pageSections.ts
├── components/     # 共用基底（Atoms / Molecules / Organisms）、WiredPage、Placeholder
├── features/       # 按 IA 三區組織，各含 api/ hooks/ pages/
│   ├── research/   # strategies / runs / compare / sweep / validate / promote / trade-review
│   ├── monitor/    # fleet / performance / positions / signals / risk
│   ├── system/     # data / alerts
│   └── home/       # cockpit 聚合
├── hooks/          # 共用 Hooks
├── layouts/        # AppShell（三區殼）
├── services/       # http.ts（單一 client）、queryClient.ts、ws.ts
├── stores/         # Zustand 輕量全域
├── styles/         # Tailwind + Grok token（CSS vars）
├── types/          # api.gen.ts（OpenAPI 生成）+ domain 手寫型別
├── utils/
├── test/           # Vitest setup
├── router.tsx / App.tsx / main.tsx
└── e2e/            # Playwright（endpoint-audit）
```

### 程式碼品質

- 型別：**TypeScript strict**（避免 `any`，對齊 `rules/coding-style.md`）；`npm run typecheck` = `tsc --noEmit`。
- 命名：元件 PascalCase（`KPICard.tsx`）、Hook camelCase + `use`、型別 `*.types.ts`。
- 檔案 200–400 行典型、800 上限；函式 < 50 行；不可變模式。
- 提交：Conventional Commits；feature branch → PR（`rules/git-workflow.md`）。

### 測試策略（≥80% 覆蓋，CI 強制）

| 類型 | 工具 | 內容 |
| :--- | :--- | :--- |
| 單元 / 元件 | Vitest + Testing Library | 工具函式、Hooks、Store、核心元件 **四態** |
| 型別回歸 | `tsc --noEmit` | strict 無錯誤（CI frontend job）|
| E2E | Playwright（`e2e/audit`）| 端點稽核 / 關鍵旅程（webServer 進 CI 為 roadmap）|

> CI `frontend` job：`npm ci` → `tsc --noEmit` → `vitest run --coverage`（`@vitest/coverage-v8`）。見 22 §CI。

---

## 第 7 部分：前後端協作（技術面）

### API 通訊規範

- 後端 **FastAPI REST API**；**契約唯一真相源 = [`25_fe_be_rest_contract.md`](./25_fe_be_rest_contract.md)**（ADR-021）。
- **單一 API client `services/http.ts`**（不散落 fetch）：組 URL、送 header、解 envelope、拋 `ApiError`；所有呼叫一律走這裡。
- **型別由 OpenAPI 生成**：後端 `app.openapi()` → `frontend/openapi.json` → `npm run gen:api`（openapi-typescript）→ `src/types/api.gen.ts`。**CI `contract-drift` job 硬 gate** live spec ↔ snapshot 一致（`scripts/check_openapi_drift.py`）；任何 schema 變更必與重生 snapshot 同 PR。
- **統一信封**：`{ success, data, error, meta }`（`error` 為結構化 `{code, message, detail}`，`meta` 帶分頁 / TTL）。422 逐欄 inline，錯誤碼 enum 見 25 §2。
- **section 級錯誤處理**：inline error + 重試，不整頁崩潰。

### 認證與授權（[ADR-031](./adrs/ADR-031-standalone-auth-decision.md)：standalone = localhost-only）

- **邊界 = loopback bind**：後端 API **MUST 綁 `127.0.0.1`**，前端走 vite proxy 同機存取，無公網暴露。**綁定本身即安全邊界，無 app 層 auth**。
- `http.ts` 現送的 `Authorization: Bearer dev-token` 為**無害殘留**（後端不檢查、不授予任何權限）；header slot 保留供 M5 遠端存取或清理。
- **秘密絕不入前端 bundle**：`FINLAB_API_TOKEN` / `DISCORD_*` / `INFLUX_*` 僅後端持有（`rules/security.md`）；`/system/alerts/channels` 回應一律遮罩。
- `401 UNAUTHORIZED`（25 §2）保留於錯誤碼 enum，供 M5 遠端存取啟用 auth 時使用；standalone 期不觸發。

---

## 第 8 部分：前端安全與監控

### 前端安全

- [ ] XSS 防護（React 自動跳脫 + CSP）
- [ ] 敏感資料不存 localStorage；秘密不入 bundle
- [ ] 依賴掃描（`npm audit`）+ 提交 `package-lock.json`
- [ ] 無彩色硬編碼、無陰影（配色 100% 來自 Grok token）

### 前端監控

- 效能：Core Web Vitals 可選收集（web-vitals lib）。
- 錯誤：全域錯誤邊界。
- FinLab API quota / 系統 metrics 屬**後端**（Grafana 系統面板，M4 選配），非前端。

---

## 第 9 部分：技術上線檢查清單

> 使用者 / IA 驗收 → `web_design/`。本清單只有技術項。

- [ ] `tsc --noEmit` strict 無錯誤
- [ ] Vitest 單元 / 元件測試通過、覆蓋率 ≥ 80%（含四態）
- [ ] `contract-drift` 綠燈：`openapi.json` 與 live spec 對齊、`api.gen.ts` 已重生
- [ ] 響應式覆蓋 §5 斷點（sidebar→drawer @<1024、ResearchTable 橫向捲動例外）
- [ ] WCAG 2.2 AA + **KPI 數值 AAA**、漲跌雙編碼、focus 單色白環（axe-core / Lighthouse）
- [ ] Core Web Vitals 達標（§4）；即時數據無進場動畫
- [ ] 配色 100% 來自 Grok token；秘密不在 bundle
- [ ] Code Review 通過
