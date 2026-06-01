# Brand System: backtest_platform 監控儀表板

> 本專案的 Global Design System（玩具城規則書）。
> **設計來源**：差異化自 [`design-system-specs/cloning/clones/xai/spec/inspired-design-system.md`](../design-system-specs/cloning/clones/xai/spec/inspired-design-system.md)（inspired by x.ai）。
> **對齊**：`BASE_DESIGN_SYSTEM.md` 分層 + `dev_docs/20_dashboard_specification.md`（面板 A–E 規格）+ `dev_docs/21_data_contract.md`（資料 schema）。
> **設計更新動機**：把現行 Streamlit `primaryColor #00d4ff` 的臨時主題，升級為一致、達 WCAG、dark-first 的 token 化設計系統，供 Lovable 產出 React 版監控儀表板。

---

## [GLOBAL ROLE]

你是「backtest_platform 量化監控平台」的資深前端架構師。你負責確保所有 AI 生成頁面是 **dark-first、資料密集、降噪、可信賴**的交易監控介面——數值準確第一、視覺克制、零分心動畫。

## [PRODUCT CONTEXT LAYER]

- **產品名稱**：backtest_platform 監控儀表板（L7 監控與歸因層）
- **一句話**：量化策略研究者的「我這支策略賺不賺 / 系統還活著嗎」單一真相儀表板。
- **目標用戶**：
  - 主要：量化策略研究者（每日 1–2 次深度檢視）
  - 次要：運維者（隨時巡檢系統健康）
- **核心價值**：把策略績效、部位、訊號、風控、統計驗證，用一致視覺語言可視化，降低判讀成本。
- **網站類型**：Data-dense Monitoring Dashboard（內部工具，非行銷站）
- **平台映射**：現行 Streamlit（面板 A–E）→ 本設計系統定義其 **React 升級版**；Grafana（系統健康 F–I）與 Discord（告警）沿用既有，僅色彩 token 對齊。

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

### Color Tokens（dark-first；已過 WCAG 驗算，見 clone validation）

| Token | 色值 | 用途 | 來源 |
|-------|------|------|------|
| Primary | `#0E7490` | 主行動、選中、品牌（teal） | [override] xai #0A0A0A→teal |
| Primary Hover | `#0C6173` | 主色 hover | [original] |
| Accent (data) | `#22D3EE` | 資料視覺主線 / focus ring（亮 cyan-teal，銜接舊 #00d4ff 意圖） | [override] 銜接 Streamlit cyan |
| Warning Accent | `#F59E0B` | 警示（amber，非品牌色） | [override] |
| **BG Base** | `#0B1220` | 頁面底（近黑藍灰，非純黑） | [override] |
| **BG Surface** | `#131C2B` | 卡片/面板底 | [original] |
| BG Code | `#0D1117` | 程式碼/JSON/終端 | [inspired by: xai] |
| Border | `#243044` | 1px 分隔（取代陰影分層） | [inspired by: xai] |
| Text Primary | `#E6EDF5` | 主文字（15.9:1 AAA） | [override] |
| Text Secondary | `rgba(230,237,245,.65)` | 次文字（7.1:1 AAA） | [inspired by: xai] |
| Text Muted | `rgba(230,237,245,.55)` | 標註/時間戳（5.4:1 AA） | [override .45→.55 修正對比] |
| **Gain** | `#22C55E` | 上漲/獲利（7.5:1 on surface, AAA） | [original] |
| **Loss** | `#F87171` | 下跌/虧損（6.2:1 AA） | [original] |
| Loss AAA | `#FCA5A5` | loss 需 AAA 的關鍵數值（9.0:1） | [original] |
| Success | `#22C55E` | 成功/正常狀態 | [inspired by: xai] |
| Warning | `#E9A60C` | 警告水位 | [inspired by: xai] |
| Error/Critical | `#EF4444` | 錯誤/熔斷 | [inspired by: xai] |
| Info | `#60A5FA` | 資訊提示（7.4:1 AAA） | [override] |

> Light mode 備援：`BG Base #F8FAFC` / `Text #0B1220`（盤中或列印用）。預設 dark。

#### Data-viz 序列色盤（圖表線/標記用，dark 底）
`#22D3EE`(主) · `#A78BFA`(紫) · `#F59E0B`(琥珀) · `#34D399`(綠) · `#F472B6`(粉) · benchmark 用 `rgba(230,237,245,.45)` 虛線。
- 規則：strategy 線用 Accent；benchmark 用 muted 虛線；漲跌區域填色用 Gain/Loss 加透明度。

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

- UI/中文：`Inter` / `Noto Sans TC`（開源，取代 xai 專有 universalSans）。
- 數值/程式碼：`Geist Mono`（tabular-nums，價格/績效對齊）。
- 字重僅 400/500/600 三級。

### 元件風格

| Token | 值 | 用途 |
|-------|-----|------|
| Radius SM | 4px | Tag, Badge |
| Radius MD | 8px | 按鈕、輸入框、KPI 卡（pill 收斂為 8px） |
| Radius LG | 12px | 面板容器 |
| Shadow | **無**（flat） | 一律 1px border + 底色分層 |
| Border | `1px solid #243044` | 預設邊框 |
| Button Primary | bg Primary / text #fff / radius 8px / 8px 16px / 14px 500 | 主行動 |
| Button Secondary | 透明 / 1px ring Border / text Primary | 次行動（ring 非實線） |
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

- **Monitoring Shell**：左側深色 sidebar（面板切換 A–E，240px，<1024px 收 drawer）+ 頂列（strategy selector + date range + refresh）+ 主內容區。
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
| Button | Primary(Teal) / Secondary(Ring) / Ghost / Danger | Default / Hover / Active / Disabled / Loading |
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
- **鍵盤**：所有互動元件 keyboard-operable + `focus-visible` ring（用 Accent `#22D3EE`，對比達標）；表格列可 focus + Enter drill-down。
- Hover：按鈕加深、卡片邊框轉 Accent（不位移、不加陰影）。

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
- 大數字 KPI：即時切換不滾動動畫（取代 xai 的 number-flow）。

---

## [壓縮版 Global Tokens]（給 assembly Master Prompt 直接嵌入，≤50 行）

```
# backtest_platform Design System — Compressed Tokens (dark-first)
COLORS
  primary #0E7490  primary-hover #0C6173  accent #22D3EE
  bg-base #0B1220  bg-surface #131C2B  bg-code #0D1117  border #243044
  text #E6EDF5  text-secondary rgba(230,237,245,.65)  text-muted rgba(230,237,245,.55)
  gain #22C55E  loss #F87171  loss-aaa #FCA5A5
  success #22C55E  warning #E9A60C  error #EF4444  info #60A5FA
  dataviz: #22D3EE #A78BFA #F59E0B #34D399 #F472B6 ; benchmark rgba(230,237,245,.45) dashed
TYPE
  H1 28/600  H2 22/600  H3 18/600  Body 14/400  Label 13/500  Caption 12/500
  Metric 20-32/600 Geist-Mono tabular-nums
  font UI: Inter / Noto Sans TC ; mono: Geist Mono
SHAPE
  radius sm4 md8 lg12 ; NO shadow (use 1px border #243044) ; button pill→8px
GRID
  fluid 100% ; breakpoints sm640 md768 lg1024 xl1280 ; section-gap 16-24px
  table→card @<1024px ; sidebar→drawer @<1024px
RULES
  dark-first ; 文字 AA / KPI 數值 AAA ; 漲跌=色+文字雙編碼
  即時數據無進場動畫 ; flat 分層 ; focus-visible ring accent
```

---

**版本**：v1.0 ｜ **套用對象**：backtest_platform 監控儀表板 React 版 ｜ **最後更新**：2026-06-01
**衍生自**：x.ai design clone（`cloning/clones/xai/`）
