# Brand System: backtest_platform 監控儀表板

> 本專案的 Global Design System（玩具城規則書）。
> **設計來源**：**Grok 單色 dark 設計語言**（忠實還原自 `cloning/clones/grok`，目標 grok.com）。v1 曾誤用 x.ai 行銷頁 + teal 差異化，已修正為 Grok 單色。
> **對齊**：`BASE_DESIGN_SYSTEM.md` 分層 + `dev_docs/20_dashboard_specification.md`（面板 A–E 規格）+ `dev_docs/21_data_contract.md`（資料 schema）。
> **設計意圖**：Grok 式單色 dark、達 WCAG、token 化的設計系統（取代早期 `#00d4ff` cyan 臨時主題），供 React 監控儀表板消費。
> **註**：Grok 精確 token（hex/字型）為路徑 2 重建近似值（grok.com 受 CF 擋無法擷取），待 DevTools 手動擷取補正；設計語言（單色 dark / 大圓角 / flat / 極簡）為 high 信心。

---

## [GLOBAL ROLE]

你是「backtest_platform 量化監控平台」的資深前端架構師。你負責確保所有 AI 生成頁面是 **dark-first、資料密集、降噪、可信賴**的交易監控介面——數值準確第一、視覺克制、零分心動畫。

## [PRODUCT CONTEXT LAYER]

- **產品名稱**：backtest_platform — 個人量化 edge 驗證工廠 + 晉升管線（本監控儀表板為其 L7 監控與歸因層）
- **一句話**：單人量化研究者的 edge 驗證工作台——「這支候選有沒有真 edge / 過不過審判庭 / 上線後還活著嗎」的單一真相儀表板。
- **產品定位**：策略是消耗品、審判庭是資產、連續 NO-GO 是平台正常運作的證據。監控區服務「已晉升 paper/live 的少數策略」，研究區服務「持續掃描下一個候選」。
- **目標用戶**：單人雙帽——研究者（每日 1–2 次深度檢視候選/在營運策略）為主、運維者（巡檢系統健康）為次。
- **核心價值**：把策略績效、部位、訊號、風控、統計驗證，用一致視覺語言可視化，降低判讀成本。
- **部署假設**：single-user standalone、localhost-only 綁定（ADR-031），非多租戶行銷站。
- **網站類型**：Data-dense Monitoring Dashboard（內部工具）
- **系統邊界**：本設計系統定義監控面板 A–D 的 React 前端；Grafana（系統健康 F–I）與 Discord（告警）沿用既有，僅色彩 token 對齊。

## [BRAND & VOICE LAYER]

### 設計原則

| # | 原則 | 說明 | 當衝突時 |
|---|------|------|---------|
| 1 | 數值優先 | 數字的可讀性與準確性高於一切裝飾 | 砍留白/動畫保資料密度 |
| 2 | 降噪 | 交易介面要讓人專注，不分心 | 移除漸層裝飾、即時數據不加進場動畫 |
| 3 | 一致分層 | 用 1px border + 底色分層，不用陰影 | flat 永遠優先於 drop shadow |
| 4 | 風險可見 | 用顏色 + 進度條傳達風險水位 | 顯示「4.2% / 6% (70%)」而非「偏高」 |

### 品牌性格

| 維度 | 我們是 | 我們不是 |
|------|--------|---------|
| 語氣 | 精準、沉穩、可信 | 炫技、花俏 |
| 視覺 | 克制、密集、dark-first | 留白行銷風、亮色狂歡 |
| 數據 | 漲跌用色 + 等寬對齊 | 模糊形容詞 |

### 文案規則

- 數值一律附單位與基準（`-3.2% / Limit -15%`）。
- 狀態用語意色 + 文字雙重編碼（不只靠顏色，色盲友善）。
- 錯誤：先說發生什麼再說怎麼辦（「查詢逾時，請縮小日期區間後重試」）。
- 空狀態：說明 + 引導（「此區間無訊號，調整日期或策略」）。
- 語言：繁體中文 UI，技術術語 / 指標名保留英文（Sharpe、MDD、PBO）。

---

## [VISUAL DESIGN SYSTEM LAYER]

### Color Tokens（**Grok 單色 dark**；已過 WCAG 驗算）

> **設計語言：Grok 式單色（monochrome）**——近黑底 + 白/灰文字，**無彩色品牌色**。
> 唯一的功能性彩色是交易剛需的 `gain`/`loss` 漲跌（且配 `↑/↓` 符號雙編碼）。
> 來源：`clones/grok`（忠實還原 grok.com，路徑 2 重建；精確值待擷取補正）。

| Token | 色值 | 用途 | 來源 |
|-------|------|------|------|
| **Primary** | `#F5F5F5` | 主行動（**白底 pill 按鈕**，text 用 base 深色）、選中 | [inspired by: grok] 單色主按鈕 |
| Primary Hover | `#E2E2E2` | 主按鈕 hover（白稍降明度） | [inspired by: grok] |
| **無彩色 accent** | — | 不設彩色品牌色；focus/互動以白灰明度 + 邊框區分 | [inspired by: grok] |
| Focus Ring | `rgba(245,245,245,.7)` | focus-visible（單色白環，非彩色） | [override] 取代 teal/cyan |
| **BG Base** | `#0F0F0F` | 頁面底（近黑，非純黑） | [inspired by: grok] |
| **BG Surface** | `#1A1A1A` | sidebar / 卡片 / 面板底 | [inspired by: grok] |
| BG Input/Elevated | `#1E1E1E` | 輸入框 / 浮起層 | [inspired by: grok] |
| BG Code | `#161616` | 程式碼/JSON/終端 | [inspired by: grok] |
| Border | `#2A2A2A`（≈ rgba(255,255,255,.10)） | 1px 細淡分隔（取代陰影分層） | [inspired by: grok] |
| Text Primary | `#F5F5F5` | 主文字（17.6:1 AAA） | [inspired by: grok] |
| Text Secondary | `rgba(255,255,255,.70)` | 次文字（9.6:1 AAA） | [inspired by: grok] |
| Text Muted | `rgba(255,255,255,.60)` | 標註/時間戳/placeholder（7.2:1 AAA） | [inspired by: grok] |
| **Gain** | `#22C55E` | 上漲/獲利（7.6:1 on surface, AAA；**配 ↑**） | [original] 交易剛需 |
| **Loss** | `#F87171` | 下跌/虧損（6.3:1 AA；**配 ↓**） | [original] 交易剛需 |
| Loss AAA | `#FCA5A5` | loss 需 AAA 的關鍵數值（9.2:1） | [original] |
| Success | `#F5F5F5` + ✓ | 正常狀態（單色 + 符號，不用綠以免與 gain 混） | [override] |
| Warning | `#E9A60C` | 風險警示水位（功能性，克制） | [original] |
| Error/Critical | `#EF4444` | 錯誤/熔斷（功能性） | [original] |

> Light mode 備援：`BG Base #FAFAFA` / `Text #0F0F0F`（盤中或列印用）。**預設 dark**。

#### Data-viz 序列色盤（圖表線/標記用，dark 底）
**單色優先**：strategy 線用 `#F5F5F5`（白實線）；benchmark 用 `rgba(255,255,255,.40)`（灰虛線）。
多序列需區分時：以**白→灰明度階 + 線型（實/虛/點）**為主，避免彩色噪音；漲跌區域填色才用 `gain`/`loss` 加透明度。
（若多策略疊圖實在需要色相區分，最多引入低飽和灰調，不引入鮮豔彩色——維持 Grok 單色基調。）

### Typography

| Token | 字級 | 行高 | 字重 | 用途 |
|-------|------|------|------|------|
| H1 | 28px | 1.2 | 600 | 頁面標題 |
| H2 | 22px | 1.25 | 600 | 區塊標題 |
| H3 | 18px | 1.3 | 600 | 小標題 |
| Body | 14px | 1.5 | 400 | 標準內文（UI 主力） |
| Label | 13px | 1.4 | 500 | 表頭/欄位標籤 |
| Caption | 12px | 1.3 | 500 | 時間戳/註腳 |
| **Metric** | 20–32px | 1.1 | 600 | KPI 數值（**Geist Mono + tabular-nums**） |

- UI/中文：`Inter` / `Noto Sans TC`（開源；Grok 字型 TBD，以 Inter 近似 grotesk）。
- 數值/程式碼：`Geist Mono`（tabular-nums，價格/績效對齊）。
- 字重僅 400/500/600 三級。

### 元件風格（**Grok 大圓角 + flat 單色**）

| Token | 值 | 用途 |
|-------|-----|------|
| Radius SM | 8px | Tag, Badge |
| Radius MD | 12px | 按鈕、輸入框 |
| Radius LG | 16px | 卡片 / 面板容器（Grok 大圓角） |
| Radius Input | 12–16px / pill | 輸入框（Grok 招牌大圓角） |
| Shadow | **無**（flat） | 一律 1px border + 底色明度階分層 |
| Border | `1px solid #2A2A2A`（細淡） | 預設邊框 |
| Button Primary | **白底 pill**：bg `#F5F5F5` / text `#0F0F0F` / radius 12px-pill / 8px 16px / 14px 500 | 主行動（Grok 式單色） |
| Button Secondary | 透明 / 1px ring `#2A2A2A` / text Primary | 次行動（ring 非實線） |
| Button Ghost | 透明 / text Muted | 低層級（filter/icon） |

### RWD / Grid

| 屬性 | 值 |
|------|-----|
| 容器 | 儀表板 fluid 100%（行銷頁才 max 1280px） |
| 斷點 | sm640 / md768 / lg1024 / xl1280 / 2xl1536（Tailwind，對齊 00_spec） |
| Grid | 12 欄；KPI 卡 `auto-fit minmax(160px,1fr)` |
| Section gap | 16–24px（資料密集，砍掉行銷大留白） |
| 關鍵響應 | **table → card list @<1024px**；sidebar → drawer；雙欄圖表 → 垂直堆疊 |

---

## [UX PATTERN LAYER]

### 常用佈局 Pattern

- **Application Shell**（三區 IA，對齊 [`../03_uiux_benchmark_and_reinforcement_plan.md`](../03_uiux_benchmark_and_reinforcement_plan.md) §4.7/§5.2 + [`../02_backtest_dashboard_design_update.md`](../02_backtest_dashboard_design_update.md) §3）：左側深色 sidebar（240px，<1024px 收 drawer）採三段式——上段 **Research 研究工作區**（研究迴圈主層級：策略庫 / New Run / Runs / Compare / Sweep / Validate / Promote）、中段 **Monitor 監控**（A 績效總覽 / B 部位狀態 / C 訊號日誌 / D 風控指標，均為 live 策略子視圖；Panel E 統計驗證已重定位至 Validate gate）、下段 **系統**（資料管理 / 告警設定）+ 頂列 **Cmd-K 全域命令列** + strategy selector + date range + refresh + 主內容區。（取代 v1 單區「A–E 面板切換」shell，承 ADR-018 研究迴圈優先 pivot。）
- **KPI Stat Row**：頂部 4–6 張 KPI 卡，數值 Geist Mono，漲跌上色，1px border 無陰影，即時切換無動畫。
- **Chart + Table Split**：左 2/3 主圖（Plotly/Recharts），右 1/3 明細表；<1024px 垂直堆疊、表格轉卡片。
- **Drill-down**：圖表點選 → 跳到關聯面板並帶 filter（如 equity 點某日 → 面板 C 該日訊號）。

### 狀態設計規則（每個資料區塊必備四態）

| 狀態 | 規則 |
|------|------|
| Loading | Skeleton（卡片/列骨架）；長查詢顯示進度或「載入中…」 |
| Empty | 說明 + 引導 CTA（「此區間無資料，調整 filter」） |
| Error | 紅色提示區 + 具體錯誤（含逾時/權限）+ 重試按鈕 |
| Populated | 正常資料 |

### 元件狀態定義（核心元件）

| 元件 | Variants | States |
|------|----------|--------|
| Button | Primary(白 pill) / Secondary(Ring) / Ghost / Danger | Default / Hover / Active / Disabled / Loading |
| KPI Card | Default / Trend(↑↓ gain/loss) / Threshold(進度條) | Default / Hover(tooltip) / Loading(skeleton) |
| DataTable | Default / Sortable / Drill-row | Default / Hover(row) / Selected / Empty / Loading |
| Status Badge | Normal / Warn / Critical | 色+文字雙編碼 |
| Progress Bar | Risk water-level | 顏色依百分比（<60 綠 / 60–85 琥珀 / >85 紅） |

---

## [INTERACTION & ACCESSIBILITY]

- **對比度**：所有文字 ≥ WCAG AA(4.5:1)；KPI 關鍵數值 ≥ **AAA(7:1)**（loss 需 AAA 用 `Loss AAA #FCA5A5`）。
- **色盲友善**：漲跌/狀態一律「顏色 + 文字/符號」雙重編碼，不單靠顏色。
- **Dark/Light**：dark 為預設一等公民；light 為備援，token 用 CSS variables 切換。
- **Motion**：完整 `prefers-reduced-motion`；**即時數據更新預設無進場動畫**（避免抖動/分心），動效僅用於導覽轉場。
- **鍵盤**：所有互動元件 keyboard-operable + `focus-visible` ring（**單色白環** `rgba(245,245,245,.7)`，非彩色；對比達標）；表格列可 focus + Enter drill-down。
- Hover：按鈕明度微調、卡片邊框提亮（`#2A2A2A`→`#3A3A3A`）；不位移、不加陰影、不引入彩色。

---

## [TECH & CONSTRAINT LAYER]

- Frontend：React 18 + TypeScript + Tailwind CSS（token → CSS variables + tailwind theme，class 策略切 dark/light）。
- Charts：Recharts 或 Plotly.js（與既有 Streamlit Plotly 對齊；K 線/heatmap/funnel）。
- State：輕量（Zustand 或 React Query 管 server state + 快取 TTL 對齊面板規格）。
- Data：對齊 `21_data_contract.md` schema；REST/SQL 後端（TimescaleDB）。
- 字型：開源可商用（Inter / Geist），自託管，**不使用 xAI 專有字型**。
- 禁止：inline styles、drop shadow、即時數據進場動畫、硬編碼色值（一律走 token）。

---

## [DATA PATTERN LAYER]

- 日期：`YYYY-MM-DD HH:mm`（含時區標記 TWT）。
- 數字：千分位逗號 + `tabular-nums` mono 對齊。
- 百分比：一位小數（`+47.2%`）；正負加號 + Gain/Loss 上色。
- 金額：`NT$` + 千分位。
- 比率指標：Sharpe/PBO/DSR 兩位小數；MDD/Heat 一位小數 %。
- 大數字 KPI：即時切換不滾動動畫。

---

## [壓縮版 Global Tokens]（給 assembly Master Prompt 直接嵌入，≤50 行）

```
# backtest_platform Design System — Compressed Tokens (Grok 單色 dark)
COLORS (monochrome — 無彩色品牌色)
  primary #F5F5F5 (白底 pill 按鈕, text #0F0F0F)  primary-hover #E2E2E2
  bg-base #0F0F0F  bg-surface #1A1A1A  bg-input #1E1E1E  bg-code #161616  border #2A2A2A
  text #F5F5F5  text-secondary rgba(255,255,255,.70)  text-muted rgba(255,255,255,.60)
  focus-ring rgba(245,245,245,.7) (單色白環)
  gain #22C55E (配↑)  loss #F87171 (配↓)  loss-aaa #FCA5A5  warning #E9A60C  error #EF4444
  dataviz: 單色優先 — strategy #F5F5F5 實線 / benchmark rgba(255,255,255,.40) 虛線 ; 多序列用明度+線型, 不用鮮豔彩色
TYPE
  H1 28/600  H2 22/600  H3 18/600  Body 14/400  Label 13/500  Caption 12/500
  Metric 20-32/600 Geist-Mono tabular-nums
  font UI: Inter / Noto Sans TC ; mono: Geist Mono
SHAPE (Grok 大圓角)
  radius sm8 md12 lg16 input12-16 ; NO shadow (1px border #2A2A2A + 底色明度階) ; button 白 pill
GRID
  fluid 100% ; breakpoints sm640 md768 lg1024 xl1280 ; section-gap 16-24px
  table→card @<1024px ; sidebar→drawer @<1024px
RULES
  Grok 單色 dark-first ; 無彩色品牌色 ; 文字 AA / KPI 數值 AAA
  漲跌=紅綠+↑↓符號雙編碼（唯一彩色）; 即時數據無進場動畫 ; flat 分層 ; focus-visible 單色白環
```

---

**版本**：v2.0（Grok 單色 dark，取代 v1 teal）｜ **套用對象**：backtest_platform 監控儀表板 React 版 ｜ **最後更新**：2026-06-04（§UX Pattern 的 shell 由單區「A–E 面板切換」對齊為三區 Application Shell，承 [`../03_uiux_benchmark_and_reinforcement_plan.md`](../03_uiux_benchmark_and_reinforcement_plan.md) §4.7/§5.2）
**衍生自**：Grok design clone（`cloning/clones/grok/`，忠實還原 grok.com）
