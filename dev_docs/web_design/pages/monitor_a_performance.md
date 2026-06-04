# Page Layer Spec — 面板 A 績效總覽 (Panel A · Performance Overview)

> M3 React 版（自 Streamlit 原型升級）。對應 `dev_docs/20_dashboard_specification.md` 面板 A。
> 填完後貼入 `assembly/PIPELINE_ORCHESTRATOR.md` 的 PAGE SPECIFICATION 區段。
> Streamlit → React 映射：`st.metric` → KPI Card、`st.dataframe` → DataTable、Plotly 圖 → Recharts / Plotly.js 元件；保留 drill-down / filter / refresh TTL 互動。

---

## [PAGE META]

- **page_name**: 面板 A 績效總覽 (Panel A · Performance Overview)
- **route_path**: /monitor/performance
- **page_type**: dashboard
- **primary_goal**: 讓使用者在單一畫面評估某策略相對 benchmark(0050) 的整體績效，透過 6 張 KPI Card 與 4 組互動圖表快速判讀報酬、風險、勝率與時間分布。
- **secondary_goal**: 作為深入分析的入口 — 點擊 equity 曲線某日可 drill-down 跳轉面板 C 該日訊號（帶 filter）。
- **target_users**:
  - 主要：量化策略開發者 / 研究員（每日多次查看回測結果）
  - 次要：投資決策者（週期性檢視策略表現）
- **entry_point**: 側邊導覽「Monitor → 績效總覽」；或面板列表卡片進入；或面板 C 返回；或 Cmd-K「跳績效」。
- **expected_time_on_page**: 3–8 分鐘（讀 KPI → 觀察 equity / drawdown → 調整 rolling window → drill-down）

---

## [STRUCTURE: SECTIONS]

> 由上至下，共 6 個功能區塊。

1. **filter_bar**
   - section_type: toolbar / filter
   - section_purpose: 控制全頁資料範圍 — strategy selector、date range、手動 refresh；任一變更即重查並重繪所有下游 section。

2. **kpi_overview**
   - section_type: stats (6-up KPI cards)
   - section_purpose: 以 6 張 metric card 呈現 Total Return / CAGR / Sharpe / MDD / Win Rate / Trades，數值用 Geist Mono、漲跌雙編碼、hover 顯示同期變化。

3. **equity_curve**
   - section_type: chart (line, dual-series)
   - section_purpose: strategy 線(白實線) + benchmark 0050(灰虛線, normalize 同起點)；支援 zoom / pan / hover tooltip 與 drill-down。

4. **drawdown_chart**
   - section_type: chart (filled area)
   - section_purpose: 回撤填色面積圖(loss 色透明)，time axis 與 equity_curve 連動。

5. **rolling_sharpe**
   - section_type: chart (line) + control
   - section_purpose: Rolling Sharpe 折線，window 可調 30 / 60 / 90 天（default 60D）。

6. **monthly_heatmap**
   - section_type: chart (heatmap, year × month)
   - section_purpose: 月報酬熱力圖，gain / loss 漸層，hover 顯示精確報酬率。

---

## [SECTION COMPONENT SPEC]

### Section: filter_bar

- **layout**: 1-row horizontal toolbar（Desktop：左 strategy + date range，右 refresh）；sticky top。
- **elements**:
  - StrategySelector: Select (dropdown) / required / 綁定 `strategy_id`；單選；顯示策略名稱 + id。
  - DateRangePicker: DateRange (雙日期) / required / default `[end-1y, end]`；不可選未來日；start ≤ end 驗證。
  - RefreshButton: IconButton / optional / 清快取並 rerun（手動觸發重查），含載入中 spinner 與 disabled。
  - LastUpdatedLabel: Caption text / optional / 顯示「最後更新：HH:mm:ss」，text-muted。
- **states**:
  - default: 顯示當前 strategy + date range；refresh 可點。
  - loading: refresh / 變更 filter 時按鈕轉 spinner，下游 section 進入 skeleton。
  - empty: 無任何 strategy → selector 顯示「尚無可用策略」且 disabled。
  - error: strategy 清單載入失敗 → inline error 文字 + 重試。
- **copy_constraints**: 按鈕文案 ≤ 4 字（「重新整理」）；標籤 ≤ 10 字。

### Section: kpi_overview

- **layout**: 6-up grid（Desktop 1×6 / Tablet 2×3 / Mobile 1×6 堆疊）；卡片 flat 1px border 無陰影。
- **elements**:
  - KpiCard.TotalReturn: KPI Card / required / 總報酬率；Geist Mono；正綠負紅雙編碼。
  - KpiCard.CAGR: KPI Card / required / 年化報酬率。
  - KpiCard.Sharpe: KPI Card / required / 夏普值；> 1 視為佳（不上漲跌色，純數值）。
  - KpiCard.MDD: KPI Card / required / 最大回撤；恆為負，loss 色。
  - KpiCard.WinRate: KPI Card / required / 勝率百分比。
  - KpiCard.Trades: KPI Card / required / 交易筆數（整數，tabular-nums）。
  - HoverDelta: Tooltip / optional / hover 顯示同期變化（vs 上一區間 / vs benchmark）。
- **states**:
  - default: 顯示數值 + label + hover delta。
  - loading: 6 張 skeleton card（同尺寸佔位）。
  - empty: 區間內無交易 → 數值顯示「—」，Win Rate / Trades 顯示 0。
  - error: 該卡顯示「計算失敗」inline，不阻塞其他卡。
- **copy_constraints**: label ≤ 12 字；數值含單位（%、x）；KPI 數值對比達 AAA。

### Section: equity_curve

- **layout**: full-width chart card；高度 320–400px；右上 legend。
- **elements**:
  - EquityLine: Line series (Recharts/Plotly) / required / strategy 權益曲線，strategy #F5F5F5 白實線（單色）。
  - BenchmarkLine: Line series / required / 0050 normalize 同起點，benchmark muted rgba(255,255,255,.40) 灰虛線。
  - ChartTooltip: Tooltip / required / hover 顯示日期 + 雙序列數值。
  - ZoomPanControl: 互動 / required / 框選 zoom、拖曳 pan、雙擊 reset。
  - DrillDownHandler: 互動 / required / 點某日資料點 → 跳轉 `/monitor/signals?date=YYYY-MM-DD&strategy_id=...`（面板 C）。
- **states**:
  - default: 雙線繪製 + legend。
  - loading: 圖表區 skeleton（矩形佔位）。
  - empty: 區間無 equity_snapshots → 「此區間無權益資料」置中提示。
  - error: 「圖表載入失敗」+ 重試按鈕。
- **copy_constraints**: legend 標籤 ≤ 10 字（「策略」/「0050」）。

### Section: drawdown_chart

- **layout**: full-width area chart；高度 200–240px；time axis 對齊 equity_curve。
- **elements**:
  - DrawdownArea: Area series / required / 預算好的回撤序列，loss 色 #F87171 填色 + 透明度。
  - SharedTimeAxis: X axis / required / 與 equity_curve 連動（zoom/pan 同步）。
  - ChartTooltip: Tooltip / required / hover 顯示日期 + 回撤百分比。
- **states**:
  - default: 填色面積圖。
  - loading: skeleton。
  - empty: 無回撤資料 → 置中提示。
  - error: inline error + 重試。
- **copy_constraints**: 軸標籤 ≤ 8 字。

### Section: rolling_sharpe

- **layout**: full-width line chart；高度 200–240px；右上 window 切換。
- **elements**:
  - WindowToggle: SegmentedControl / required / 30 / 60 / 90 天，default 60；切換即用 pandas rolling 重算重繪。
  - RollingSharpeLine: Line series / required / dataviz 色；零軸參考線。
  - ChartTooltip: Tooltip / required / hover 顯示日期 + rolling sharpe 值。
- **states**:
  - default: 60D 折線。
  - loading: skeleton。
  - empty: 資料點不足 window → 「資料不足以計算 {window}D Rolling Sharpe」。
  - error: inline error + 重試。
- **copy_constraints**: 切換選項固定「30D / 60D / 90D」。

### Section: monthly_heatmap

- **layout**: heatmap grid（列=年、欄=12 月）；full-width；色階圖例置底。
- **elements**:
  - HeatmapGrid: Heatmap / required / resample monthly pct_change，gain 綠系 / loss 紅系漸層雙編碼。
  - CellTooltip: Tooltip / required / hover 顯示 年月 + 精確報酬率(%)。
  - ColorLegend: Legend / required / 連續色階 + 中點 0%。
- **states**:
  - default: 完整年×月色塊；無資料月份留空灰格。
  - loading: skeleton grid。
  - empty: 區間 < 1 月 → 「資料不足以產生月報酬熱力圖」。
  - error: inline error + 重試。
- **copy_constraints**: 月份用數字 1–12 或英文縮寫；報酬率保留 2 位小數。

---

## [INTERACTION & STATE FLOW]

### 主要互動流程

1. 頁面載入 → 依 default filter（strategy 第一項、date `[end-1y, end]`）查詢 → 6 section 進入 loading → 取得資料後渲染。
2. 變更 StrategySelector 或 DateRangePicker → 立即重查 → 全頁重繪（KPI 用 quantstats 重算、圖表重繪）。
3. 調整 rolling_sharpe WindowToggle → 僅該 section 用 pandas rolling 本地重算重繪（不重新打 API，若已有原始序列）。
4. 點 RefreshButton → 清快取 + rerun → 全頁重查。
5. 點 equity_curve 某日資料點 → drill-down 跳轉面板 C `/monitor/signals`，帶 `date` 與 `strategy_id` filter。
6. equity_curve 與 drawdown_chart 的 zoom / pan 共用 time axis，連動縮放。

### RWD 行為差異

| 斷點 | 佈局 | 差異說明 |
|------|------|---------|
| Desktop (≥1280px) | filter_bar 單列；KPI 1×6；圖表全寬堆疊 | sidebar 展開；圖表保留 zoom/pan |
| Tablet (768–1279px) | filter_bar 換行；KPI 2×3；圖表全寬 | sidebar 收合為 drawer |
| Mobile (≤767px) | filter_bar 垂直堆疊；KPI 1×6 單欄；圖表全寬縮高 | heatmap 改橫向捲動；zoom 改 pinch；drill-down 維持點擊 |

### 資料更新策略

- 快取 TTL：300s（5 分鐘）。
- 觸發重查時機：page load、filter change（strategy / date range）、手動 refresh（清快取）。
- rolling window 切換：優先本地重算（已快取原始日序列），避免額外 API round-trip。
- 即時數據無進場動畫（遵循 Global），重繪以瞬時切換呈現。

---

## [DATA & API]

- **uses_api**: true
- **資料來源**: `equity_snapshots`（策略權益/現金/回撤）+ `daily_bars`（0050 benchmark）。
- **endpoints**:
  - GET `/api/strategies` — 取得 strategy selector 清單（strategy_id + name）。
  - GET `/api/performance/equity?strategy_id={id}&start={d}&end={d}` — equity / cash / drawdown 日序列（drawdown 已預算）。
  - GET `/api/performance/kpi?strategy_id={id}&start={d}&end={d}` — KPI（quantstats 計算 Total Return / CAGR / Sharpe / MDD / Win Rate / Trades）。
  - GET `/api/performance/benchmark?symbol=0050&start={d}&end={d}` — 0050 日序列（前端 normalize 同起點）。
  - GET `/api/performance/monthly?strategy_id={id}&start={d}&end={d}` — monthly resample pct_change（或前端由 equity 計算）。
- **error_cases**:
  - 網路錯誤：section 級 inline error + 重試按鈕，不整頁崩潰。
  - API 錯誤（4xx/5xx）：顯示後端訊息摘要 + 重試；KPI 單卡失敗不阻塞其他卡。
  - 無資料（區間空）：對應 section 顯示 empty 文案，非 error。
  - 權限不足：導向登入或顯示「無權限存取此策略」。

---

## [EXCEPTION TO GLOBAL RULES]

無特殊例外，完全遵循 Global System Prompt 規範。
（Sharpe KPI 不套漲跌雙編碼色 — 屬數值判讀慣例，非違反；以 text 主色呈現。）

---

## [ACCEPTANCE CRITERIA]

- [ ] 6 個 section 全部功能正常（filter / KPI / equity / drawdown / rolling / heatmap）。
- [ ] 每個 section 四態完備：default / loading(skeleton) / empty / error。
- [ ] filter 變更（strategy / date）即時重查並重繪全頁；rolling window 切換重算正確。
- [ ] equity_curve drill-down 正確跳轉面板 C 並帶 `date` + `strategy_id` filter。
- [ ] equity 與 drawdown time axis 連動 zoom / pan。
- [ ] 快取 TTL 300s + 手動 refresh（清快取）+ page load/filter change 觸發正確。
- [ ] RWD 符合 Desktop / Tablet / Mobile 定義（table→card、sidebar→drawer @<1024px）。
- [ ] 數值全用 Geist Mono tabular-nums；漲跌色 + 文字雙編碼。
- [ ] 文字對比達 AA、KPI 數值達 AAA；focus-visible ring 單色白環 rgba(245,245,245,.7)。
- [ ] dark-first（Grok 單色）、flat 1px border #2A2A2A 無陰影、即時數據無進場動畫。
