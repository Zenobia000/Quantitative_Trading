# 前端架構規範 - backtest_platform（四層共振戰法回測平台）

> **版本:** v3.0（對齊現實）| **更新:** 2026-06-04 | **狀態:** M3 目標規格（前端尚未實作）
> **決策依據:** [ADR-015](./adrs/ADR-015-dashboard-design-system-and-react-upgrade.md)（策略績效層 Streamlit→React）、[ADR-009](./adrs/)（三層儀表板分工）。
>
> **MECE 邊界**：本文件**只談技術視角**（stack / 分層 / 量化指標 / 工程化）。
> 使用者視角（頁面職責、旅程、導航、路由內容）全部在 **`web_design/`**（本專案的前端 IA 真相源）。
> ⚠️ 注意：`dev_docs/17` 是 *m2_to_m5_master_plan*，**不是**前端 IA；前端 IA 不在 dev_docs 編號序列，而在 `web_design/`。
>
> | 你想找的 | 看這份 |
> |---|---|
> | 用什麼框架、怎麼分層 | 12（本檔）§2 |
> | 設計令牌、元件分層 | 12（本檔）§3；token 真相源 `web_design/global/02_backtest_platform_brand_system.md` |
> | LCP / INP / CLS 數字目標 | 12（本檔）§4 |
> | 響應式斷點、a11y 標準 | 12（本檔）§5 |
> | 專案 file 組織、測試框架 | 12（本檔）§6 |
> | API client 技術選型 | 12（本檔）§7；契約 `21_data_contract.md` |
> | 哪些**頁面**存在、頁面職責 | `web_design/pages/{research_0N,monitor_a~d,system_*}.md` |
> | 使用者旅程、導航結構、三區 IA | `web_design/03_uiux_benchmark_and_reinforcement_plan.md` §4.7 / §5.2 |
> | 可貼 Lovable 的組裝 Prompt | `web_design/assembly/<page>_integrated.md` |

---

## 第 1 部分: 架構目標（量化）

| 維度 | 目標 | 衡量指標 |
| :--- | :--- | :--- |
| **效能** | 載入與互動回應 | LCP, INP, CLS, TTI |
| **技術可用性** | 各裝置/輔助技術可達 | 響應式覆蓋率、a11y 通過率（AA 文字 / AAA KPI 數值） |
| **可維護性** | 單人迭代效率 | 複雜度、覆蓋率、技術債 |
| **可靠性** | 各環境穩定運行 | 錯誤率、四態完備率（default/loading/empty/error） |

> 本平台為**單人開發**；前端工程負擔是 ADR-015 明確接受的取捨（換取設計系統一致性與 a11y 天花板）。
> 「使用者完成目標的難易度」屬 IA 視角 → `web_design/03` §1 §4。

---

## 第 2 部分: 系統化分層

```
用戶感知層    -- 視覺元件、Grok 單色樣式系統、圖表（Recharts/Plotly.js）
互動邏輯層    -- 事件處理、表單驗證（RunConfig 等 schema）
狀態管理層    -- Server State（runs/research）、URL State（filter/saved views）、本地狀態
資料通訊層    -- REST API client（對 FastAPI 後端）、資料轉換、TTL 快取
基礎設施層    -- Vite 建置、Vitest/Playwright 測試、前端監控、CI
```

### 各層職責與技術選型（已定）

| 層級 | 職責 | 技術選型 |
| :--- | :--- | :--- |
| 感知層 | 渲染 UI、視覺一致性 | **React + TypeScript** + **Tailwind**（token 化 Grok 單色） |
| 圖表 | 績效/比較/熱圖 | **Recharts**（一般）+ **Plotly.js**（互動/科研級：parcoords、heatmap、scatter） |
| 編輯器 | 策略邏輯 authoring | **Monaco**（CodeEditor，沿用 dark 主題微調） |
| 互動層 | 輸入、表單驗證 | **React Hook Form** + schema 驗證（對齊後端 Pydantic RunConfig） |
| 狀態層 | Server / URL / 本地 | **TanStack Query**（server state + 輪詢 TTL）+ **URL state**（filter/saved views）+ 輕量 **Zustand**（全域 UI 狀態） |
| 通訊層 | API 呼叫與快取 | **fetch 封裝 client** + TanStack Query 快取（TTL 分級見 §4） |
| 路由 | 三區導航 | **React Router**；路由表/URL 命名 → `web_design/03` §4.7 + 各 page `route_path` |
| 基礎設施 | 建置與品質 | **Vite** + **Vitest** + Testing Library + **Playwright** |
| 產出方式 | 初版生成 | **Lovable** 依 `assembly/<page>_integrated.md` Master Prompt 產出，再手調 |

> 後端為 **FastAPI REST API**（v0.6 已落地）；React 不直連 TimescaleDB（ADR-015 取捨），一律走 REST。

---

## 第 3 部分: 設計系統（Grok 單色 dark v2.0）

> **Token 真相源**：`web_design/global/02_backtest_platform_brand_system.md`。以下為技術對接摘要，歧異以該檔為準。

### 設計令牌 (Design Tokens)

| 類別 | 值（Grok 單色） | 備註 |
| :--- | :--- | :--- |
| 背景 | bg-base `#0F0F0F` / surface `#1A1A1A` / input `#1E1E1E` / code `#161616` | dark-first |
| 邊框 | border `#2A2A2A`（**flat 1px 分層**） | — |
| 文字 | text `#F5F5F5` / secondary / tertiary（明度階） | **無彩色品牌色** |
| 功能色 | gain `#22C55E`(↑) / loss `#F87171`(↓) / loss-aaa `#FCA5A5` / warning `#E9A60C` / error `#EF4444` | 唯一彩色＝漲跌，**配 ↑↓ 符號雙編碼** |
| 受控 data-viz 例外 | Categorical 8-色盤 / Diverging(gain↔灰↔loss) / Sequential 灰階 | 僅圖表內容區（§6.1） |
| 字體 | UI: Inter / Noto Sans TC；**數值: Geist Mono**（tabular-nums） | KPI 數值對齊 |
| 圓角 | **button 白底 pill radius 12px**；sm4 / md8 / lg12 | — |
| **陰影** | **無（NO shadow）** | ⚠️ 本系統 flat，不用陰影分層，改 1px border |
| Focus | **單色白環** `rgba(245,245,245,.7)` | 非彩色 ring |

### 元件分層 (Atomic Design — Atoms → Templates)

```
原子 (Atoms)      → Button(白 pill/ghost)、Input、StatusBadge、Icon、Tag、ProgressBar
分子 (Molecules)  → KPICard、FilterChip、SearchBar、FormField、ParamPill、GateBadge
組織 (Organisms)  → Sidebar(三區)、Cmd-K CommandPalette、DataTable / ResearchTable(virtualized)、
                    ChartFrame / CompareChart、CodeEditor、FirstRunEmptyState、PromotionStepper
模板 (Templates)  → AppShell(三區殼: Research/Monitor/System + drawer @<1024)
```

> **Pages 不在本檔**（IA 概念）→ `web_design/pages/`。技術上 Page = `Template + 資料注入（TanStack Query）`。
> 共用基底元件（Button/KPICard/DataTable/StatusBadge/ProgressBar/ChartFrame）由 Lovable 步驟 1 一次性產出，避免跨頁重複（見 `02_backtest_dashboard_design_update.md` §4）。

---

## 第 4 部分: 效能策略（量化）

### Core Web Vitals 目標

| 指標 | 目標 | 優化策略 |
| :--- | :--- | :--- |
| LCP | < 2.5s | 預載關鍵資源、字型子集化（Geist Mono / Inter） |
| INP | < 200ms | Code Splitting、減少主執行緒阻塞、圖表懶渲染 |
| CLS | < 0.1 | **四態 skeleton 佔位**（固定高度避免 layout shift） |
| TTI | < 3s (4G) | 路由級懶載入 |

### 本平台特有效能規則（對齊 page 規格）

- **即時數據無進場動畫**：數據更新採就地替換（瞬時切換），尊重 `prefers-reduced-motion`。
- **ResearchTable 虛擬化**：runs table 千列以 virtualization 渲染，不卡頓；**@<1024 橫向捲動不轉 card**（研究級密集表反模式）。
- **metrics-dict-first 低延遲迴圈**：先回結構化 metrics dict 秒判，重圖（tear sheet）按需 render。
- **快取 TTL 分級**：研究/驗證資料 300s；部位 60s；訊號（今日）30s / 歷史 300s；queued/running run 以輪詢或 SSE 更新至終態。
- **四態完備**：每 section 必備 default / loading(skeleton) / empty / error，error 與 empty 明確區分。

---

## 第 5 部分: 技術可用性（量化標準）

### 響應式設計斷點（本專案實際值）

| 名稱 | 寬度 | 目標裝置 | 行為 |
| :--- | :--- | :--- | :--- |
| sm | >= 640px | 手機橫向 | — |
| md | >= 768px | 平板 | — |
| lg | >= 1024px | 筆電 | **≥1024 sidebar 展開；<1024 → drawer**；table→card（ResearchTable 除外，改橫向捲動） |
| xl | >= 1280px | 桌面 | Desktop 完整佈局（KPI 1×6 等） |

> 三斷點主規則：Desktop ≥1280 / Tablet 768–1279 / **sidebar→drawer @<1024**。sidebar 一律**兩態**（展開 ↔ drawer），不用 icon-rail。

### 無障礙 (A11y) 量化要求

- WCAG 2.2 **AA（一般文字 ≥4.5:1）**，**KPI 關鍵數值 AAA（≥7:1）**（loss 用 `#FCA5A5`）。
- **漲跌/狀態「顏色 + 文字/符號」雙編碼**（↑↓ / ✓✗ / PASS-FAIL），色盲友善——不可只靠顏色。
- 語義化 HTML、ARIA；鍵盤完整可操作，**表格列可 focus + Enter drill-down**。
- **focus-visible 單色白環** `rgba(245,245,245,.7)`（非彩色）。

### 國際化 (i18n)

- **繁體中文為主**（單一 locale）；技術術語 / 指標名保留英文（Sharpe、MDD、PBO、DSR）。
- 日期/數字以 **Intl API** 格式化（價格/績效 tabular-nums 對齊）。
- 無 RTL 需求。

---

## 第 6 部分: 工程化實踐

### 專案 file 組織（M3 新建 React app；與 Python 後端分離）

```
frontend/                # ADR-015：dashboard 策略績效層由 Streamlit 轉為獨立 React app
├── src/
│   ├── components/      # 共用基底（Atoms/Molecules/Organisms）
│   ├── features/        # 按 IA 三區組織
│   │   ├── research/    # strategies/runs/compare/sweep/validate/promote
│   │   ├── monitor/     # performance/positions/signals/risk
│   │   └── system/      # data/alerts
│   ├── hooks/           # 共用 Hooks（含 TanStack Query hooks）
│   ├── layouts/         # AppShell（三區殼）
│   ├── pages/           # 路由進入點（內容 → web_design/pages/）
│   ├── services/        # REST API client（對 FastAPI）
│   ├── stores/          # Zustand 輕量全域
│   ├── styles/          # Tailwind config + Grok token（CSS vars dark/light）
│   ├── types/           # 型別（由 OpenAPI 生成 + 手寫）
│   └── utils/
└── (Streamlit MVP 過渡期並存，見 ADR-015「短期雙軌」)
```

> 實際存在哪些 page / 對應路由 / 傳什麼資料 → `web_design/pages/` + 各頁 `[DATA & API]`。

### 程式碼品質

- Linter: ESLint + Prettier；型別: **TypeScript strict**（避免 `any`，對齊 `rules/coding-style.md`）。
- 命名：元件 PascalCase（`KPICard.tsx`）、Hook camelCase + `use`、型別 `*.types.ts`。
- 檔案 200–400 行典型、800 上限；函式 < 50 行；不可變模式。
- 提交: Conventional Commits；分支: feature branch → PR（`rules/git-workflow.md`）。

### 測試策略（≥80% 覆蓋）

| 類型 | 工具 | 覆蓋率 | 內容 |
| :--- | :--- | :--- | :--- |
| 單元 | Vitest | 80%+ | 工具函式、Hooks、Store |
| 元件 | Testing Library | 核心元件 + **四態** | 渲染、互動、狀態 |
| E2E | Playwright | 關鍵旅程 | 研究迴圈（New Run→Validate→Promote）、監控 triage（旅程 → `web_design/03` §4） |
| 視覺 | Storybook（選用） | 設計系統 | 元件外觀回歸、Grok 單色一致性 |

---

## 第 7 部分: 前後端協作（技術面）

### API 通訊規範

- 後端：**FastAPI REST API**（v0.6 已落地，覆蓋 research loop）；契約見 `21_data_contract.md`。
- 統一 **API Client 封裝**（不直接 fetch）；請求/回應型別由 **OpenAPI 自動生成 TS**。
- **統一信封格式**：`{ success, data, error, pagination }`（對齊 `rules/patterns.md`）。
- 統一錯誤處理：section 級 inline error + 重試，不整頁崩潰；422 逐欄 inline（如 RunConfig schema）。

### 認證與授權

- **單人自託管平台**：認證從簡（本機 / 內網）。page 規格中的 401/403 → 導向登入為防呆，非多角色 RBAC。
- 若導入：Token 存 httpOnly Cookie / Memory；路由守衛以 middleware 實作。
- **秘密絕不入前端 bundle**：`FINLAB_API_TOKEN` / `DISCORD_*` 等僅後端持有（`rules/security.md`）。

---

## 第 8 部分: 監控與安全

### 前端監控

- 效能：Core Web Vitals 收集（web-vitals lib）。
- 錯誤：全局錯誤邊界（+ Sentry 選用）。
- 流量：FinLab API quota 屬**後端** Grafana 面板 G（ADR-009/010），非前端。

### 前端安全

- [ ] XSS 防護（React 自動跳脫 + CSP）
- [ ] CSRF 防護（SameSite Cookie，若導入認證）
- [ ] 敏感資料不存 localStorage；秘密不入 bundle
- [ ] 依賴掃描（`npm audit`）+ 提交 lock file
- [ ] Subresource Integrity（CDN 資源，如有）

---

## 第 9 部分: 技術上線檢查清單

> 使用者/IA 驗收 → `web_design/guides/quality_checklist.md`。本清單只有技術項。

- [ ] TypeScript strict 無錯誤
- [ ] 單元/元件測試通過、覆蓋率 ≥ 80%（含四態）
- [ ] 響應式覆蓋 §5 斷點（sidebar→drawer @<1024、ResearchTable 橫向捲動例外）
- [ ] WCAG 2.2 AA + **KPI 數值 AAA**、漲跌雙編碼、focus 單色白環自動檢測通過（axe-core / Lighthouse）
- [ ] Core Web Vitals 達標（§4）；即時數據無進場動畫
- [ ] 配色 100% 來自 Grok token（**無硬編碼、無舊 teal `#22D3EE/#243044`、無陰影**）
- [ ] 安全檢查清單 §8 通過；秘密不在 bundle
- [ ] Bundle size 預算未超
- [ ] Code Review 通過
