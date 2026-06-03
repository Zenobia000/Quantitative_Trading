# Page Layer Spec — 面板 D 風控指標 (Risk Metrics)

> 對應 `dev_docs/20_dashboard_specification.md` 面板 D。React 版（自 Streamlit 升級）。
> 填完後貼入 `assembly/monitor_d_risk_integrated.md` 的 CURRENT TASK 區段。

---

## [PAGE META]

- **page_name**: 風控指標面板 (Risk Metrics Panel)
- **route_path**: /monitor/risk
- **page_type**: dashboard
- **primary_goal**: 即時呈現策略當前風險水位（DD / VaR / Heat / Concentration），讓使用者一眼判斷是否觸及熔斷層級
- **secondary_goal**: 提供近 7 日風險事件審計軌跡與單一事件的 drill-down context，支援事後歸因
- **target_users**:
  - 主要：策略操盤手 / 風控人員（交易時段高頻巡檢，每日多次）
  - 次要：策略開發者（回測後檢視風險表現）
- **entry_point**: 主儀表板側邊導航「風控」分頁，或 Status badge CRITICAL 告警通知的跳轉連結
- **expected_time_on_page**: 巡檢模式 30-90 秒；事件 drill-down 模式 3-5 分鐘

---

## [STRUCTURE: SECTIONS]

> 由上至下 4 個功能區塊。

1. **risk_status_header**
   - section_type: stats / status_badge
   - section_purpose: 頂部以單一 Status badge（NORMAL / WARN / CRITICAL）總結整體風控狀態，色 + 文字雙編碼，做為全頁第一視覺焦點

2. **risk_water_levels**
   - section_type: progress_bars (KPI Cards with bars)
   - section_purpose: 三條水位條呈現 Current DD、Daily PnL vs VaR95、Heat 的當前佔用百分比，顏色依 % 門檻分級，快速辨識逼近上限的指標

3. **mdd_trend_chart**
   - section_type: chart (line + threshold lines)
   - section_purpose: 90 日 MDD 折線圖疊加 3 條熔斷 hline（L1/L2/L3），hover 顯示對應熔斷層級，呈現回撤趨勢與安全邊際

4. **recent_risk_events**
   - section_type: table (DataTable with drill-down)
   - section_purpose: 近 7 日風險事件表（時間 / event_type / 說明），列點擊 drill-down 進入事件 context，提供審計軌跡

---

## [SECTION COMPONENT SPEC]

### Section: risk_status_header

- **layout**: 1-column 橫向 bar（左：面板標題 H2 + 資料時間戳；右：Status badge + 手動 refresh icon button）
- **elements**:
  - PanelTitle: Text(H2) / required / 「風控指標」標題 + 副標 route 說明
  - DataTimestamp: Text(Caption, Geist Mono) / required / 最後更新時間，tabular-nums
  - StatusBadge: Badge / required / 三態 NORMAL(success #22C55E) / WARN(warning #E9A60C) / CRITICAL(error #EF4444)，色塊 + 文字標籤雙編碼，CRITICAL 不使用動畫僅靜態強對比
  - RefreshButton: IconButton / optional / 手動觸發重新抓取，loading 時 icon 轉為 spinner（即時數據區唯一允許的進度指示）
- **states**:
  - default: badge 依 risk_metrics 推導之狀態顯示對應色 + 文字
  - loading: badge 區顯示 skeleton 色塊，timestamp 顯示「載入中…」
  - empty: 無 risk_metrics 資料 → badge 顯示「NO DATA」灰階 + text-muted
  - error: badge 顯示「狀態不可用」error 色 + 重試按鈕
- **copy_constraints**: badge 文字固定枚舉值（NORMAL / WARN / CRITICAL），標題 ≤ 12 字

### Section: risk_water_levels

- **layout**: 3-column grid（Desktop）／responsive，每格一張含水位條的 KPI Card
- **elements**:
  - CurrentDdBar: ProgressBar + KPI / required / 顯示 -3.2% / Limit -15%，佔用 21%；數值 Geist Mono tabular-nums
  - DailyPnlVarBar: ProgressBar + KPI / required / Daily PnL vs VaR95，佔用 38%
  - HeatBar: ProgressBar + KPI / required / 4.2% / 6%，佔用 70%
  - LevelLegend: Text(Caption) / optional / 門檻說明「<60 安全 / 60-85 警戒 / >85 危險」
  - 顏色規則（水位條 fill）: <60% → gain/success #22C55E；60-85% → warning #E9A60C；>85% → loss/error #F87171，且各條附文字百分比（雙編碼，不單靠顏色）
- **states**:
  - default: 三條水位條依 % 著色，KPI 數值 AAA 對比
  - loading: 三張卡片 skeleton bar
  - empty: 顯示「—」佔位 + text-muted「尚無風險指標」
  - error: 卡片內 inline error + 重試
- **copy_constraints**: 每張卡片標籤 ≤ 18 字；數值一律保留 1 位小數並帶單位（%）

### Section: mdd_trend_chart

- **layout**: 1-column 全寬圖表卡（Recharts LineChart 或 Plotly.js）
- **elements**:
  - MddLine: LineSeries / required / 90 日 MDD 折線，單色 strategy #F5F5F5 白線，無進場動畫
  - ThresholdL1: ReferenceLine(hline) / required / -10% 暫停（warning #E9A60C dashed）
  - ThresholdL2: ReferenceLine(hline) / required / -15% 減倉（amber #F59E0B dashed）
  - ThresholdL3: ReferenceLine(hline) / required / -20% 全停（error #EF4444 dashed）
  - HoverTooltip: Tooltip / required / hover 顯示日期 + MDD 值 + 命中之熔斷層級文字（L1/L2/L3）
  - YAxis/XAxis: Axis / required / Y 軸百分比、X 軸 90 日；軸標 Geist Mono
- **states**:
  - default: 折線 + 3 條 hline，benchmark 風格虛線標註門檻
  - loading: 圖表區 skeleton 占位（固定高度避免 layout shift）
  - empty: 「近 90 日無 MDD 資料」置中提示
  - error: 圖表區 error 訊息 + 重試按鈕
- **copy_constraints**: 門檻 label 固定「L1 暫停 / L2 減倉 / L3 全停」+ 百分比

### Section: recent_risk_events

- **layout**: 1-column 全寬 DataTable；Mobile 轉 card 列表
- **elements**:
  - EventTable: DataTable / required / 欄位：時間(time) / event_type(HEAT_WARN / CONCENT …) / 說明(description)
  - EventTypeTag: Tag / required / event_type 以 tag 呈現，色依嚴重度但附文字（雙編碼）
  - RowDrillDown: Interaction / required / 點擊列開啟 drawer/modal 顯示事件 context（觸發指標快照、原始 metric 值）
  - TimeColumn: Text(Geist Mono) / required / 事件時間 tabular-nums
- **states**:
  - default: 依時間倒序列出近 7 日 `event_type IS NOT NULL` 事件
  - loading: table skeleton rows
  - empty: 「近 7 日無風險事件」插圖 + text-secondary（正向訊號）
  - error: table 區 error banner + 重試
- **copy_constraints**: 說明欄 ≤ 60 字（超出截斷 + tooltip 全文）；event_type 維持原始枚舉碼

---

## [INTERACTION & STATE FLOW]

### 主要互動流程

1. 頁面載入 → 並行請求 risk_metrics（水位 + 狀態 + 趨勢）與 risk events → 渲染四區
2. 使用者掃視 Status badge + 水位條顏色 → 判斷是否需介入（巡檢主路徑）
3. hover MDD 折線 → tooltip 顯示命中熔斷層級
4. 點擊事件表某列 → drill-down drawer 顯示該事件 context → 關閉返回
5. 點擊 RefreshButton 或 TTL 到期 → 重新抓取並就地更新（無全頁 reload）

### RWD 行為差異

| 斷點 | 佈局 | 差異說明 |
|------|------|---------|
| Desktop (≥1024px) | 水位條 3 欄並排、圖表全寬、事件 DataTable 完整欄位 | 標準佈局 |
| Tablet (768-1023px) | 水位條 3 欄壓縮或 2+1、圖表全寬 | section-gap 縮至 16px，DataTable 保留但欄寬自適 |
| Mobile (<768px) | 全部單欄堆疊 | DataTable → card 列表、drill-down drawer → 全螢幕 sheet、badge 置頂固定 |

### 資料更新策略

- risk_metrics（水位 + 狀態 + MDD 趨勢）：交易時段輪詢，TTL 30 秒；即時數據無進場動畫，更新採就地替換
- risk events：TTL 60 秒輪詢；新事件出現時 table 頂部插入（無閃爍動畫）
- 手動 refresh：忽略 TTL 立即重抓，期間僅 RefreshButton 顯示 spinner

---

## [DATA & API]

- **uses_api**: true
- **endpoints**:
  - GET `/api/risk/metrics` — 回傳 risk_metrics 最新列（current_dd / var_95 / heat / concentration）+ 推導之 status
  - GET `/api/risk/mdd-trend?window=90d` — 回傳 90 日 MDD 序列供折線圖
  - GET `/api/risk/events?window=7d` — 回傳近 7 日 `event_type IS NOT NULL` 事件清單
  - GET `/api/risk/events/{id}` — 單一事件 drill-down context（指標快照）
- **error_cases**:
  - 網路錯誤：各 section 獨立顯示 inline error + 重試，不阻塞其他區塊
  - API 錯誤（5xx）：保留上一次成功資料並標示「資料可能過期」+ timestamp，提供重試
  - 權限不足（403）：整頁顯示「無風控資料存取權限」提示，隱藏資料區
  - 無資料（200 空）：對應 section 進入 empty 態

---

## [EXCEPTION TO GLOBAL RULES]

完全遵循 Global System。即時數據區嚴格無進場動畫；唯一允許的動態回饋為手動 refresh 的 spinner。

---

## [ACCEPTANCE CRITERIA]

- [ ] 4 個 Section 功能正常（status / 水位條 / MDD 趨勢 / 事件表）
- [ ] 每個 Section 四態完備（default / loading / empty / error）
- [ ] Status badge 與 event_type tag、水位條皆為「色 + 文字」雙編碼，不單靠顏色
- [ ] 水位條顏色門檻正確（<60 綠 / 60-85 琥珀 / >85 紅）並對齊規格百分比（DD 21% / VaR 38% / Heat 70%）
- [ ] MDD 圖含 3 條熔斷 hline（-10/-15/-20%）且 hover 顯示層級
- [ ] 事件表列 drill-down 可開啟 context 並正確關閉
- [ ] RWD 行為符合上表（Desktop 3 欄 / Mobile 單欄 + table→card + drawer→sheet）
- [ ] 所有數值使用 Geist Mono tabular-nums，KPI 數值對比達 AAA、一般文字達 AA
- [ ] 資料更新 TTL（metrics 30s / events 60s）與手動 refresh 正確運作，無全頁 reload
- [ ] dark-first（Grok 單色）、flat 1px border #2A2A2A 無陰影；單色基調繼承自 Global System v2.0
