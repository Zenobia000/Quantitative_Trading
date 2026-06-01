# Integrated Master Prompt: 面板 C — 訊號日誌 (Signal Log, M3)

> 可直接貼給 Lovable 的最終 Prompt。對齊 `lovable_組裝.md` SOP 與 `assembly/01_dashboard_integrated.md` 格式。
> 對應頁面規格：`pages/02_panel_c_signals.md`。

---

## === GLOBAL PROJECT GUIDELINE (DO NOT OVERRIDE) ===

```
# backtest_platform Design System — Compressed Tokens (dark-first)
COLORS  primary #0E7490 / hover #0C6173 / accent #22D3EE
  bg-base #0B1220 / bg-surface #131C2B / bg-code #0D1117 / border #243044
  text #E6EDF5 / text-secondary rgba(230,237,245,.65) / text-muted rgba(230,237,245,.55)
  gain #22C55E / loss #F87171 / loss-aaa #FCA5A5
  success #22C55E / warning #E9A60C / error #EF4444 / info #60A5FA
  dataviz #22D3EE #A78BFA #F59E0B #34D399 #F472B6 ; benchmark rgba(230,237,245,.45) dashed
TYPE  H1 28/600 H2 22/600 H3 18/600 Body 14/400 Label 13/500 Caption 12/500
  Metric 20-32/600 Geist-Mono tabular-nums ; UI font Inter / Noto Sans TC ; mono Geist Mono
SHAPE radius sm4 md8 lg12 ; NO shadow (1px border #243044) ; button radius 8px
GRID fluid 100% ; bp sm640 md768 lg1024 xl1280 ; section-gap 16-24px ; table→card & sidebar→drawer @<1024px
RULES dark-first ; 文字 AA / KPI 數值 AAA ; 漲跌=色+文字雙編碼 ; 即時數據無進場動畫 ; flat 分層 ; focus-visible ring accent #22D3EE
```

最高準則聲明：
- 本區段為整個 backtest_platform 專案的唯一設計系統來源，為最高準則，優先於任何模型預設審美。
- 所有元件、圖表、狀態必須繼承此處定義的配色、字級、圓角、間距與斷點。
- 除非下方 EXCEPTION RULES 明確說明，否則不得違反。

---

## === CURRENT TASK: BUILD 面板 C — 訊號日誌 (Signal Log) ===

本次任務：依上方 Global Guideline，實作量化交易平台的「訊號日誌」儀表板頁面（route `/dashboard/signals`）。
目的：讓交易者檢視當日策略訊號、追蹤每筆訊號 Signal→Fill 執行狀態，並透過 30 天時間軸與轉換漏斗評估訊號品質與下單管線健康度。
這是 React 升級版（原 Streamlit 原型）：st.metric → KPI Card、st.dataframe → DataTable、Plotly 圖 → react-plotly.js / Recharts 元件；保留 drill-down / filter / refresh TTL 互動。

需實作的 Sections（重點摘要，完整規格見 `pages/02_panel_c_signals.md`）：

1. **filter_bar**（filter_controls）
   - DatePicker（預設今日、禁未來）+ ActionFilter SegmentedControl（All / buy / add / reduce / exit / stoploss）+ refresh_indicator（即時「{n}s 前更新」/ 歷史快照）
   - filter 同步驅動下方所有 section

2. **todays_signals_table**（data_table）
   - 標題 "Today's Signals"；欄位 Time / Symbol / Action / Reason / Status
   - Action 用 Badge 色+文字雙編碼；Status Badge（FILLED=success / REJECTED=error / SUBMITTED / PENDING）
   - 點 row → accordion 展開 JSONViewer 顯示完整 reason_json（scores / prices / context），bg-code #0D1117

3. **signal_timeline_30d**（scatter_chart）
   - 標題 "Signal Timeline (30D)"；多軌散點（buy/add/reduce/exit/stoploss），react-plotly.js go.Scatter 多軌、dataviz 色盤分軌
   - hover tooltip 顯示 time/symbol/action/status/score；點 dot → drill-down 訊號詳情（高亮對應 table row）；Legend 可切軌

4. **signal_fill_funnel**（funnel_chart）
   - 標題 "Signal → Fill Rate"；go.Funnel 三階 Generated → Submitted(%) → Filled(%)
   - 兩張 latency KPI Card：Avg Latency Signal→Submit、Submit→Fill（Geist Mono、AAA 對比、附 ms/s 單位）

互動與資料更新重點：
- 即時面板（今日）TTL 30s 自動刷新；歷史面板（非今日）TTL 300s，切換為「歷史快照」並停用即時刷新
- 即時數據更新無進場動畫，就地替換數值
- API：GET `/api/signals`、`/api/signals/timeline`、`/api/fills`、`/api/signals/funnel`（latency = fills.submit_time − signals.signal_time、fill_time − submit_time）

RWD 重點：
- Desktop ≥1280：filter 橫列 + 全寬 table + timeline + funnel 2 欄
- Tablet 768-1023：單欄堆疊、funnel/KPI 上下排、Sidebar 收合
- Mobile <768：DataTable → Card 列表、timeline 橫向捲動、Sidebar → drawer

---

## === EXCEPTION RULES ===

無特殊例外，完全遵循 Global Guideline。

---

## === OUTPUT REQUIREMENTS ===

1. **結構確認**：先列出本頁 4 個 Sections（filter_bar / todays_signals_table / signal_timeline_30d / signal_fill_funnel）及各自關鍵元件清單。
2. **一致性說明**：簡述如何落實設計系統一致性——dark-first 背景分層（bg-base / bg-surface / bg-code）、flat 1px border #243044 無陰影、所有數值與 latency 用 Geist Mono tabular-nums、Action/Status 色+文字雙編碼、即時數據無進場動畫、文字達 AA / KPI 數值達 AAA、focus-visible 用 accent #22D3EE ring。
3. **程式碼**：產出完整可運行的 React + Tailwind + Recharts / react-plotly.js 代碼：
   - 四個 section 元件 + 容器頁面，配色全部來自 Global Tokens
   - 每個 section 含四態（default / loading skeleton / empty / error + 重試）
   - 完整 RWD（<1024px：table→card、sidebar→drawer）
   - 含 TTL 刷新邏輯（今日 30s / 歷史 300s）與 drill-down / filter 互動

---

*組裝日期: 2026-06-01 | 使用 backtest_platform Global System (dark-first) | 對應 pages/02_panel_c_signals.md*
