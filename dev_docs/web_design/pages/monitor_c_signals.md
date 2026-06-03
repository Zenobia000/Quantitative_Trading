# Page-Level Prompt: 面板 C — 訊號日誌 (Signal Log, M3)

> 從 Streamlit 原型升級為 React 版頁面規格。對齊 `pages/page_template.md` 章節。
> 來源：`dev_docs/20_dashboard_specification.md` 面板 C。
> Streamlit → React 對照：st.metric → KPI Card、st.dataframe → DataTable、Plotly 圖 → Recharts / Plotly.js 元件；保留原互動（drill-down / filter / refresh TTL）。

---

## [PAGE META]

- **page_name**: Signal Log (訊號日誌)
- **route_path**: `/monitor/signals`
- **page_type**: dashboard
- **primary_goal**: 讓交易者檢視當日產生的策略訊號、追蹤每筆訊號的執行狀態（Signal → Fill），快速定位未成交或延遲訊號
- **secondary_goal**: 透過 30 天時間軸與 Funnel 轉換率，評估訊號品質與下單管線健康度（latency / fill rate）
- **target_users**:
  - 主要：策略交易者 / 自營操盤手（盤中每日多次查看）
  - 次要：策略開發者（盤後分析訊號→成交轉換與延遲）
- **entry_point**: 左側 Sidebar「訊號日誌」項目 / 從面板 A（總覽）的待處理訊號數字 drill-down 進入
- **expected_time_on_page**: 盤中 30 秒-2 分鐘快速巡檢；盤後分析 5-10 分鐘

---

## [STRUCTURE: SECTIONS]

1. **filter_bar**
   - section_type: filter_controls
   - section_purpose: 提供 date 選擇與 action 類型過濾（All / buy / add / reduce / exit / stoploss），同時驅動下方所有 section 的資料範圍

2. **todays_signals_table**
   - section_type: data_table
   - section_purpose: 列出選定日期的訊號（Time / Symbol / Action / Reason / Status），支援 action 過濾與 row drill-down 展開 JSON reason

3. **signal_timeline_30d**
   - section_type: scatter_chart
   - section_purpose: 多軌散點圖呈現近 30 天各類型訊號分布，hover 顯示訊號詳情、點擊 dot drill-down 至訊號詳情

4. **signal_fill_funnel**
   - section_type: funnel_chart
   - section_purpose: 呈現 Generated → Submitted → Filled 轉換漏斗與各階段平均延遲（signal→submit、submit→fill）

---

## [SECTION COMPONENT SPEC]

### Section: filter_bar

- **layout**: 全寬單欄橫向工具列，左對齊（DatePicker 在左、ActionFilter 在右、Refresh 狀態在最右）
- **elements**:
  - date_picker: DatePicker / required / 選擇查詢日期，預設今日；不可選未來日期
  - action_filter: SegmentedControl / required / 選項 All / buy / add / reduce / exit / stoploss，預設 All；同步過濾 table 與 timeline 軌道
  - refresh_indicator: Badge + Caption / optional / 顯示「即時 · {n}s 前更新」，TTL 倒數；歷史日期時顯示「歷史快照」
- **states**:
  - default: 顯示今日日期 + All + 即時刷新中
  - hover: SegmentedControl 選項 hover 邊框轉單色白邊 rgba(245,245,245,.7)
  - loading: DatePicker / Filter 維持可互動，refresh_indicator 顯示 spinner（無進場動畫，僅旋轉指示器）
  - error: refresh_indicator 轉 error 色 #EF4444 + 「更新失敗，點擊重試」
  - empty: 不適用（控制列恆顯示）
  - disabled: 歷史日期模式下 refresh_indicator 停用倒數
- **copy_constraints**: action 標籤使用英文原詞；refresh 文案 ≤ 12 字

### Section: todays_signals_table

- **layout**: 全寬單欄 DataTable，可垂直捲動；row 點擊向下展開 detail panel（accordion）
- **elements**:
  - section_title: H2 / required / "Today's Signals"
  - data_table: DataTable / required / 欄位 Time / Symbol / Action / Reason / Status
    - col_time: Cell (Geist Mono, tabular-nums) / required / signals.signal_time，HH:mm:ss
    - col_symbol: Cell (Geist Mono) / required / stock_id
    - col_action: Badge / required / buy / add / reduce / exit / stoploss，色+文字雙編碼（buy/add 偏 gain、reduce/exit/stoploss 偏 loss/warning）
    - col_reason: Text (truncate) / required / reason_json 摘要（如主因 score），溢出省略
    - col_status: StatusBadge / required / FILLED / SUBMITTED / PENDING / REJECTED，FILLED 用 success #22C55E、REJECTED 用 error #EF4444
  - row_expand_detail: JSONViewer / required / 點 row 展開 reason_json 完整內容（scores / prices / context），bg-code #161616、Geist Mono
- **states**:
  - default: 依 filter 顯示訊號列，依 signal_time 倒序
  - hover: row 背景轉 bg-surface 高亮、cursor pointer
  - loading: Skeleton rows（5-8 列佔位）
  - error: 表格區紅色提示 + 「載入訊號失敗」+ 重試按鈕
  - empty: "今日尚無符合條件的訊號" + Caption 提示調整 action 過濾
  - disabled: 不適用
- **copy_constraints**: Reason 摘要單行 ≤ 40 字；展開 JSON 不限長度，超高度內部捲動

### Section: signal_timeline_30d

- **layout**: 全寬圖表卡片，內含多軌（buy / add / reduce / exit / stoploss）散點圖（Plotly.js go.Scatter 多軌；React 中以 react-plotly.js 包裝）
- **elements**:
  - section_title: H2 / required / "Signal Timeline (30D)"
  - scatter_chart: ScatterChart (multi-track) / required / X=日期(30天)、Y=action 軌道；每點代表一筆訊號，5 軌用 §6.1 **Categorical 8-色盤**（低飽和、dark 底 WCAG 達標的受控例外）。此處正是 §10 GAP-1「單色在 ≥5 類別破功」的實證：以受控離散色盤取代 v1 鮮豔虹色
  - point_tooltip: ChartTooltip / required / hover 顯示 time / symbol / action / status / 主因 score
  - track_legend: Legend / required / 五軌可點擊切換顯示
- **states**:
  - default: 顯示近 30 天散點，受 action_filter 收斂軌道
  - hover: 顯示 tooltip，點放大描邊
  - loading: 圖表區 Skeleton（矩形佔位，無進場動畫）
  - error: "時間軸載入失敗" + 重試
  - empty: "近 30 天無訊號資料"
  - disabled: 不適用
- **copy_constraints**: 軸標籤英文；tooltip 每行 ≤ 1 指標

### Section: signal_fill_funnel

- **layout**: 全寬圖表卡片，左側 Funnel、右側 latency KPI（Desktop 2 欄；窄屏堆疊）
- **elements**:
  - section_title: H2 / required / "Signal → Fill Rate"
  - funnel_chart: FunnelChart / required / Plotly.js go.Funnel；三階 Generated → Submitted(%) → Filled(%)，含階段間百分比
  - latency_kpi_submit: KPI Card / required / "Avg Latency · Signal→Submit" + 數值(ms/s, Geist Mono, AAA 對比)
  - latency_kpi_fill: KPI Card / required / "Avg Latency · Submit→Fill" + 數值
- **states**:
  - default: 顯示漏斗 + 兩張 latency KPI
  - hover: 漏斗階段 hover 顯示絕對數量 + 轉換率 tooltip
  - loading: Funnel + KPI Skeleton
  - error: "轉換率載入失敗" + 重試
  - empty: "無足夠訊號計算轉換率"
  - disabled: 不適用
- **copy_constraints**: KPI 標籤 ≤ 28 字；latency 數值附單位（ms / s）

---

## [INTERACTION & STATE FLOW]

### 主要互動流程

1. 頁面載入 → 以今日 + All 取得 signals / fills / latency / 30D timeline
2. 變更 date → 重新查詢四個 section；非今日切換為「歷史快照」並停用即時刷新
3. 切換 action_filter → table 過濾列、timeline 收斂顯示軌道（funnel 維持全體統計或同步收斂，依 filter）
4. 點 table row → 向下展開 JSON reason（scores / prices / context）
5. 點 timeline dot → drill-down 至該訊號詳情（高亮對應 table row 並展開）
6. hover funnel 階段 → 顯示該階段絕對數量與轉換率

### RWD 行為差異

| 斷點 | 佈局 | 差異說明 |
|------|------|---------|
| Desktop (≥1280px) | filter 橫列 + 全寬 table + timeline + funnel 2 欄 | 完整體驗，Sidebar 展開 |
| Tablet (768-1023px) | 單欄堆疊；funnel 與 latency KPI 改上下排列 | Sidebar 收合為 icon |
| Mobile (<768px) | 單欄堆疊；DataTable → Card 列表（Time/Symbol/Action/Status 摘要），點卡展開 reason；timeline 改可橫向捲動精簡軌；Sidebar → drawer | table→card & sidebar→drawer @<1024px |

### 資料更新策略

- 即時面板（今日）：TTL 30s 自動刷新 signals / fills / funnel / latency
- 歷史面板（非今日）：TTL 300s（歷史快照，低頻）
- 即時數據更新無進場動畫，僅就地替換數值（避免閃爍）
- 切換 date / filter 立即重新請求，不等待 TTL

---

## [DATA & API]

- **uses_api**: true
- **endpoints**:
  - GET `/api/signals?date={date}&action={action}` — 取得當日訊號列表（signal_time / stock_id / action / reason_json）
  - GET `/api/signals/timeline?days=30&action={action}` — 取得近 30 天多軌散點資料
  - GET `/api/fills?date={date}` — 取得對應成交（fill_time / signal_id / fill_price / status）
  - GET `/api/signals/funnel?date={date}` — Generated→Submitted→Filled 計數與轉換率，含 avg latency（latency = fills.submit_time − signals.signal_time、fill_time − submit_time）
- **error_cases**:
  - 網路錯誤：section 內顯示重試按鈕，保留前次快取資料 + 「資料可能過期」提示
  - API 錯誤：友善錯誤訊息（不洩露後端細節）+ 重試
  - 權限不足：導向登入頁
  - 空結果：各 section 顯示對應 empty 文案

---

## [EXCEPTION TO GLOBAL RULES]

- signal_timeline_30d 多軌散點（5 action 類別）用 §6.1 **Categorical 8-色盤**（低飽和、dark 底 WCAG 達標）— 屬「chrome 單色、資料區受控離散色盤」例外，僅限圖表內容區。這是 §10 GAP-1 點名的破功點：單色明度階在 ≥5 類別無法區分，故開受控例外。
- 其餘完全遵循 Global v2.0（Grok 單色 dark、flat 1px border #2A2A2A、Geist Mono 數值、白環 focus、漲跌雙編碼、即時數據無動畫、文字 AA / KPI 數值 AAA）。

---

## [ACCEPTANCE CRITERIA]

- [ ] filter_bar / table / timeline / funnel 四個 Section 功能正常
- [ ] date 與 action filter 同步驅動所有 section
- [ ] Table row 點擊可展開 JSON reason（scores / prices / context）
- [ ] Timeline 多軌散點 hover 顯示詳情、dot 點擊 drill-down 至訊號詳情
- [ ] Funnel 顯示 Generated→Submitted(%)→Filled(%) 並含兩段 avg latency
- [ ] 每個 section 四態完備（default / loading / empty / error）
- [ ] 即時面板 TTL 30s、歷史面板 TTL 300s，刷新無進場動畫
- [ ] RWD 三斷點行為正確（<1024px：table→card、sidebar→drawer）
- [ ] 數值（Time / Symbol / Price / Latency / 百分比）使用 Geist Mono tabular-nums 對齊
- [ ] Action / Status 採色+文字雙編碼；文字達 AA、KPI 數值達 AAA 對比
- [ ] 配色完全來自 Global Tokens、flat 1px border 無陰影
