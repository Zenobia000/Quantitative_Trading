# Page-Level Prompt: 面板 E — 統計驗證 (M5)

> 對應 `page_template.md`。React 版（自 Streamlit 升級）：st.metric → KPI Card、st.dataframe → DataTable、Plotly 圖 → Recharts/Plotly.js 元件。
> 來源面板規格：`dev_docs/20_dashboard_specification.md` → 面板 E。
> 繼承 backtest_platform Global Design System（dark-first / teal 主色 / flat 1px border / Geist Mono 數值 / 漲跌雙編碼）。

---

## [PAGE META]

- **page_name**: 統計驗證 (Statistical Validation Panel E)
- **route_path**: `/dashboard/validation`
- **page_type**: dashboard
- **primary_goal**: 呈現策略的 Walk-Forward Analysis (WFA) 與過擬合風險指標 (PBO / DSR)，讓使用者判斷策略在樣本外 (OOS) 是否穩健、是否存在過擬合
- **secondary_goal**: 以 Rolling 視窗追蹤 PBO/DSR 隨時間的劣化，提早預警策略衰退
- **target_users**:
  - 主要：量化研究員 / 策略開發者（驗收策略上線前的最後一道統計門檻）
  - 次要：風控 / 投委會（審查策略是否達顯著性門檻）
- **entry_point**: 主導覽列 Dashboard → 面板 E 分頁；或自策略詳情頁「查看驗證結果」連結進入
- **expected_time_on_page**: 1-3 分鐘（先掃 KPI 判斷紅旗，再 drill-down WFA scatter 與 Rolling 趨勢）

---

## [STRUCTURE: SECTIONS]

1. **summary_bar**
   - section_type: stats / summary_header
   - section_purpose: 一行摘要最新一次 WFA 執行狀態（Latest WFA Run 日期 / Windows 數 / IS-OOS 配置 24m/6m）

2. **wfa_scatter**
   - section_type: chart (scatter)
   - section_purpose: 以 IS Sharpe vs OOS Sharpe 散點 + 對角線參考，視覺化各 window 的樣本內外一致性；對角線上方=穩健

3. **risk_kpi**
   - section_type: stats_cards (KPI)
   - section_purpose: 三張 KPI 卡呈現 PBO / DSR / Min Track Record Length，PBO 高=過擬合風險（警示色編碼）

4. **rolling_trend**
   - section_type: chart (dual line)
   - section_purpose: Rolling 30D 的 PBO 與 DSR 雙折線，追蹤過擬合風險與顯著性隨時間變化

---

## [SECTION COMPONENT SPEC]

### Section: summary_bar

- **layout**: 全寬單欄，3 個 inline 摘要欄位（Desktop 1 行 3 欄；Mobile 縱向堆疊）
- **elements**:
  - latest_run_date: Metric (Geist Mono, tabular-nums) / required / "Latest WFA Run" + ISO 日期（取 `method='WFA'` 最新 `run_time`）
  - windows_count: Metric / required / "Windows" + 整數（該次 WFA 的 window 數）
  - is_oos_config: Label + Value / required / "IS-OOS" + "24m / 6m"（樣本內 24 個月、樣本外 6 個月）
  - refresh_btn: IconButton / optional / 手動重新整理，顯示上次更新時間 tooltip
- **states**:
  - default: 顯示三欄摘要值，數值右對齊 tabular-nums
  - loading: 三欄各一條 skeleton bar
  - empty: 「尚無 WFA 執行紀錄」+ 說明文字（無 CTA，唯讀面板）
  - error: 「無法載入 WFA 摘要」+ 重試按鈕（error 色 #EF4444 文字 + icon 雙編碼）
- **copy_constraints**: 標籤 ≤ 16 字元；日期一律 ISO `YYYY-MM-DD`

### Section: wfa_scatter

- **layout**: 全寬單欄圖表卡（卡片 1px border #243044，無陰影）；圖表內含正方形繪圖區以對齊對角線
- **elements**:
  - chart_title: H3 / required / "WFA: IS Sharpe vs OOS Sharpe"
  - scatter_plot: ScatterChart (Recharts `<Scatter>` markers，或 Plotly.js `go.Scatter` mode=markers) / required / X=IS Sharpe、Y=OOS Sharpe，每點為一個 window
  - diagonal_ref: ReferenceLine (y=x) / required / dashed benchmark 色 rgba(230,237,245,.45)，標註「對角線上方=OOS≥IS=穩健」
  - point_tooltip: Tooltip / required / hover 顯示 window 編號、IS/OOS Sharpe、IS-OOS 期間
  - robust_legend: Legend / optional / 標示穩健（上方）/ 衰退（下方）區域語意（色+文字雙編碼，不可只靠顏色）
- **states**:
  - default: 散點 + 對角線；穩健點以 gain #22C55E、衰退點以 loss #F87171 雙編碼（並附形狀/文字輔助）
  - hover: 該點放大 + tooltip；即時數據無進場動畫
  - loading: 圖表區 skeleton（保留座標軸骨架）
  - empty: 「此次 WFA 無 window 資料」置中提示
  - error: 「散點圖載入失敗」+ 重試
- **copy_constraints**: 軸標題 ≤ 20 字元；tooltip 每列 ≤ 24 字元

### Section: risk_kpi

- **layout**: 1 行 3 欄 KPI 卡網格（Desktop）/ 1 行 3 欄或 2+1（Tablet）/ 單欄堆疊（Mobile）
- **elements**:
  - pbo_kpi: KPI Card (st.metric → KPI Card) / required / "PBO" + 數值（例 0.18）+ 狀態註記「低過擬合」；PBO 高 → 卡片切換 warning #E9A60C / error #EF4444 並附文字標記（雙編碼）
  - dsr_kpi: KPI Card / required / "DSR" + 數值（例 0.82）+ 註記「顯著」；達門檻以 success #22C55E
  - mtrl_kpi: KPI Card / required / "Min Track Record Length (months)" + 數值（月）
- **states**:
  - default: 數值以 Metric 字級 20-32 / Geist Mono / tabular-nums（KPI 數值需達 AAA 對比）
  - hover: tooltip 解釋指標定義與門檻（PBO<0.2 佳 / DSR>0 顯著）
  - loading: 三張卡 skeleton
  - empty: 卡片顯示「—」佔位 + 「尚無 PBO/DSR 結果」
  - error: 卡片區「指標載入失敗」+ 重試
- **copy_constraints**: KPI 標籤 ≤ 32 字元；狀態註記 ≤ 8 字元

### Section: rolling_trend

- **layout**: 全寬單欄圖表卡
- **elements**:
  - chart_title: H3 / required / "Rolling 30D PBO / DSR"
  - dual_line_chart: LineChart (Recharts `<Line>` x2，或 Plotly.js scatter mode=lines) / required / X=日期、雙 Y 軸或共享軸的 PBO 與 DSR 兩條折線
  - pbo_line: Line / required / dataviz 色（PBO 用 #F59E0B 警示語意）
  - dsr_line: Line / required / dataviz 色（DSR 用 #22D3EE accent）
  - threshold_ref: ReferenceLine / optional / PBO 警戒線（dashed），跨越時 tooltip 標警示
  - legend: Legend / required / 區分 PBO / DSR（色+文字雙編碼）
- **states**:
  - default: 兩條折線 + 圖例；即時數據無進場動畫
  - hover: 垂直 cursor + 同步 tooltip 顯示當日 PBO/DSR
  - loading: 圖表 skeleton
  - empty: 「Rolling 資料不足（需 ≥ 30 日）」
  - error: 「趨勢圖載入失敗」+ 重試
- **copy_constraints**: 圖例標籤 ≤ 12 字元

---

## [INTERACTION & STATE FLOW]

### 主要互動流程

1. 頁面載入 → 並行取得：最新 WFA windows、最新 PBO/DSR/MTRL、Rolling 30D 序列 → 填入四個 section
2. 掃 summary_bar 與 risk_kpi → 若 PBO 偏高，KPI 卡轉警示色 + 文字提示，引導使用者 drill-down
3. hover wfa_scatter 任一點 → tooltip 顯示該 window 明細（IS/OOS Sharpe、期間），判斷哪個 window 在對角線下方
4. hover rolling_trend → 同步 cursor tooltip，觀察 PBO/DSR 隨時間是否劣化
5. 點 refresh_btn → 重新拉取最新 run（清快取、強制 refetch）

### RWD 行為差異

| 斷點 | 佈局 | 差異說明 |
|------|------|---------|
| Desktop (≥1280px) | summary_bar 1 行 3 欄；scatter 與 rolling 全寬；KPI 1 行 3 欄 | 完整體驗；scatter 維持正方繪圖區 |
| Tablet (768-1024px) | KPI 維持 3 欄或 2+1；圖表全寬 | sidebar 收合為 drawer（@<1024px）；圖表高度略降 |
| Mobile (<768px) | 全部單欄堆疊；summary_bar 縱向；KPI 逐張堆疊 | table→card、sidebar→drawer；圖表改觸控 tooltip，圖例移至圖下方 |

### 資料更新策略

- WFA / PBO / DSR 為離線批次產物，非即時 → 採用快取，**TTL = 300 秒（5 分鐘）**
- summary_bar 與 risk_kpi 共用同一 `validation_runs` 查詢結果，單次請求填充
- 手動 refresh 立即使快取失效並 refetch
- 即時數據（若後端新增 run）無進場動畫，直接替換數值

---

## [DATA & API]

- **uses_api**: true
- **主要資料表**: `validation_runs`
- **endpoints**:
  - GET `/api/validation/wfa/latest` — 取最新一次 `validation_runs WHERE method='WFA'` 的 windows（含每 window 的 IS/OOS Sharpe、IS-OOS 期間、run_time、windows 數），供 summary_bar 與 wfa_scatter
  - GET `/api/validation/metrics/latest` — 取 `validation_runs WHERE method IN ('PBO','DSR') ORDER BY run_time DESC` 最新值（PBO / DSR / Min Track Record Length），供 risk_kpi
  - GET `/api/validation/rolling?window=30` — 取 Rolling 30D 的 PBO / DSR 時序，供 rolling_trend
- **error_cases**:
  - 網路錯誤：各 section 獨立顯示 error 態 + 重試按鈕，不整頁崩潰
  - API 錯誤（5xx）：顯示友善訊息「驗證資料暫時無法載入」+ 重試；伺服器端記錄詳細上下文
  - 無資料（200 空集）：對應 section 顯示 empty 態（區分於 error）
  - 權限不足（403）：導向登入 / 顯示無權限提示

---

## [EXCEPTION TO GLOBAL RULES]

無特殊例外，完全遵循 backtest_platform Global System 規範（dark-first、teal 主色、flat 1px border 無陰影、Geist Mono 數值、漲跌/風險雙編碼、即時數據無動畫）。

---

## [ACCEPTANCE CRITERIA]

- [ ] 4 個 Section（summary_bar / wfa_scatter / risk_kpi / rolling_trend）功能正常
- [ ] 每個 Section 四態完備（default / loading / empty / error），error 與 empty 明確區分
- [ ] WFA scatter 含 y=x 對角線參考，穩健/衰退以「色 + 形狀/文字」雙編碼，不只靠顏色
- [ ] PBO 高時 KPI 卡切換 warning/error 色 **並** 附文字標記（雙編碼）
- [ ] KPI 數值使用 Geist Mono / tabular-nums，數值達 AAA 對比；一般文字達 AA
- [ ] Rolling 30D 雙折線 PBO/DSR 圖例以色+文字雙編碼
- [ ] RWD 三斷點行為正確（@<1024px sidebar→drawer、table→card；Mobile 單欄堆疊）
- [ ] 資料快取 TTL=300s，手動 refresh 可強制刷新
- [ ] 即時數據無進場動畫；卡片 flat 1px border #243044 無陰影
- [ ] 所有數值右對齊 tabular-nums，日期 ISO 格式對齊
- [ ] 符合 Global Design System 視覺規範（teal 主色、accent #22D3EE focus ring）
