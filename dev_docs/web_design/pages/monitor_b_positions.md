# Page-Level Prompt: 面板 B — 部位狀態 (Positions)

> backtest_platform M3 儀表板頁面規格。React 版（自 Streamlit 升級）。
> 對應 `pages/page_template.md` 結構。繼承 `global/02_backtest_platform_brand_system.md`。

---

## [PAGE META]

- **page_name**: 面板 B — 部位狀態 (Positions)
- **route_path**: `/monitor/positions`
- **page_type**: dashboard
- **primary_goal**: 讓使用者即時掌握當前持倉的風險暴露與損益狀態，快速判斷是否需要調整部位
- **secondary_goal**: 透過產業配置與集中度指標揭露投資組合的結構性風險
- **target_users**:
  - 主要：每日盤中/盤後檢視持倉的交易者（高頻使用）
  - 次要：風險管理者審視組合集中度與 Portfolio Heat
- **entry_point**: 側邊導覽「Monitor → 部位狀態」；由面板 A（總覽）KPI 點擊下鑽進入
- **expected_time_on_page**: 1-3 分鐘（盤中快速掃描），風險檢視時可延長至 5 分鐘

---

## [STRUCTURE: SECTIONS]

1. **header_bar**
   - section_type: page_header
   - section_purpose: 頁面標題 + 資料時間戳 (as of ... TWT)，告知資料新鮮度與 live/snapshot 模式

2. **kpi_row**
   - section_type: stats_cards
   - section_purpose: 四個關鍵風險/資金指標總覽（Portfolio Heat / Cash / Open Positions / Equity）

3. **positions_table**
   - section_type: data_table
   - section_purpose: 逐筆持倉明細，支援排序/過濾/欄寬調整，點列下鑽至該股訊號歷史

4. **industry_allocation**
   - section_type: chart_pie
   - section_purpose: 產業別市值配置圓餅圖，點扇區可過濾下方/同頁表格

5. **concentration_risk**
   - section_type: stats_cards
   - section_purpose: 投資組合集中度指標（Top1/Top3/Top5 % 與 HHI），揭露單一/少數標的風險

---

## [SECTION COMPONENT SPEC]

### Section: header_bar

- **layout**: 全寬單欄，左標題 + 右側資料時間戳，水平兩端對齊
- **elements**:
  - page_title: H1 / required / "部位狀態"
  - as_of_timestamp: Caption (Geist Mono) / required / "as of 2026-06-01 13:30:00 TWT"，數值類 mono tabular-nums
  - mode_badge: Badge / optional / "Snapshot" 或 "Live"（live mode M5 啟用，WebSocket 連線中顯示 info 色點）
  - refresh_indicator: Caption / optional / "每 60s 自動更新" 或最後更新相對時間
- **states**:
  - default: 顯示標題 + 時間戳 + Snapshot/Live badge
  - loading: 時間戳區 skeleton（窄條），標題立即顯示
  - empty: 無快照時時間戳顯示 "—"，badge 隱藏
  - error: 時間戳區顯示 error 色 "資料時間未知"，附小型重試 icon
- **copy_constraints**: 標題 ≤ 10 字；時間戳固定格式 `YYYY-MM-DD HH:mm:ss TWT`

### Section: kpi_row

- **layout**: 1 行 4 列 KPI Card 網格（Desktop）/ 2x2（Tablet）/ 單欄堆疊（Mobile）
- **elements**:
  - heat_card: KPI Card / required / "Portfolio Heat" + Metric "4.2%" + 副文字 "上限 6%"；接近上限（≥ 80% 即 ≥ 4.8%）數值轉 warning 色並加文字標記「接近上限」，達/超上限轉 error 色（色 + 文字雙編碼）
  - cash_card: KPI Card / required / "Cash" + Metric "NT$ 312,450" + 副文字百分比 "28.4%"
  - open_card: KPI Card / required / "Open Positions" + Metric "12 / 15"（持倉數 / 上限）
  - equity_card: KPI Card / required / "Equity" + Metric "NT$ 1,100,200"
- **states**:
  - default: 顯示數值（Metric 20-32/600 Geist Mono tabular-nums，右對齊）
  - loading: 每張卡片 skeleton（標籤條 + 數值條）
  - empty: 數值顯示 "—"，副文字隱藏
  - error: 卡片內顯示 error 色 "載入失敗" + 小重試連結
- **copy_constraints**: KPI 標籤 ≤ 18 字元；金額千分位 NT$ 前綴；百分比 1 位小數

### Section: positions_table

- **layout**: 全寬 DataTable（橫向可捲動），表頭固定（sticky），最小寬度撐開後 Mobile 橫向捲動
- **elements**:
  - data_table: DataTable / required / 欄位如下，支援欄排序、欄過濾、column resize
    - Symbol: Text / required / 股票代號（點列觸發下鑽）
    - Industry: Text / required / 產業別（join universe）
    - Qty: Number (mono, 右對齊) / required / 股數
    - Entry: Number (mono, 右對齊) / required / 進場價
    - Current: Number (mono, 右對齊) / required / 現價（daily_bars / live）
    - P&L%: Number (mono, 右對齊) / required / `(current - entry) / entry`；漲 gain 綠 / 跌 loss 紅，附 ▲/▼ 符號（色 + 文字雙編碼）
    - Days: Number (mono, 右對齊) / required / 持有天數
    - StopLoss: Number (mono, 右對齊) / required / 停損價
  - filter_bar: Toolbar / optional / 欄位過濾輸入（Symbol/Industry）+ 清除過濾
  - row_count: Caption / optional / "顯示 12 / 12 筆"
- **states**:
  - default: 顯示持倉列，依預設排序（如 P&L% 降冪），P&L% 上色
  - hover: 列底色微亮（bg-surface 提亮），cursor pointer，提示可下鑽
  - loading: 表格區 skeleton rows（8-10 列灰條）
  - empty: 居中插圖式提示「目前無持倉部位」+ 副文字「待策略產生進場訊號」
  - error: 表格區 error 提示 "持倉資料載入失敗" + 重試按鈕
- **copy_constraints**: Symbol ≤ 8 字元；Industry ≤ 12 字元；數值統一 mono tabular-nums 右對齊

### Section: industry_allocation

- **layout**: 半寬圖表卡（Desktop 與 concentration_risk 並排 2 欄）/ 全寬（Tablet 以下）
- **elements**:
  - section_title: H3 / required / "產業配置"
  - pie_chart: PieChart (Recharts Pie 或 Plotly.js go.Pie) / required / 依產業別市值佔比繪製；色盤用 §6.1 **Categorical 8-色盤**（低飽和、dark 底 WCAG 達標的受控例外，非 v1 鮮豔虹色）
  - tooltip: Tooltip / required / hover 顯示產業名 + 市值金額 (NT$) + 佔比 %
  - legend: Legend / optional / 產業名 + 佔比
- **states**:
  - default: 顯示圓餅圖（即時數據無進場動畫）
  - hover: 對應扇區提亮 + tooltip 顯示金額
  - loading: 圓形 skeleton（灰圈）
  - empty: "無持倉，無產業配置可顯示"
  - error: "產業配置載入失敗" + 重試
- **copy_constraints**: 圖例產業名 ≤ 12 字元；金額千分位 NT$ 前綴
- **互動**: 點扇區 → 以該產業過濾 positions_table（同頁 cross-filter，再點取消）

### Section: concentration_risk

- **layout**: 半寬卡片，內含 3-4 個 st.metric 等價 KPI Card（橫向）/ Mobile 縱向堆疊
- **elements**:
  - section_title: H3 / required / "集中度風險"
  - top1_metric: KPI Card / required / "Top1" + Metric "%"（最大單一部位佔比）
  - top3_metric: KPI Card / required / "Top3" + Metric "%"
  - top5_metric: KPI Card / required / "Top5" + Metric "%"
  - hhi_metric: KPI Card / required / "HHI" + Metric "0.18" + 副文字 "低集中"（`HHI = Σ(mv_i / total)^2`；< 0.15 低 / 0.15-0.25 中 / > 0.25 高，文字標記）
- **states**:
  - default: 顯示百分比與 HHI（Metric mono 右對齊）
  - loading: 各 metric skeleton
  - empty: 數值 "—"，HHI 副文字隱藏
  - error: "集中度計算失敗" + 重試
- **copy_constraints**: 百分比 1 位小數；HHI 2 位小數

---

## [INTERACTION & STATE FLOW]

### 主要互動流程

1. 頁面載入 → 取得 positions latest snapshot + current_price + universe join → 計算 KPI / pnl_pct / HHI → 渲染五個 section
2. 點擊 positions_table 任一列 → 下鑽至面板 C（訊號歷史），帶入該 Symbol filter
3. 點擊 industry_allocation 扇區 → 以該產業 cross-filter positions_table；再點同扇區或「清除過濾」還原
4. 操作 DataTable 表頭 → 排序（單欄升/降冪）/ 欄過濾 / column resize（resize 寬度可選持久化至 localStorage）
5. Portfolio Heat 接近/達上限 → heat_card 變 warning/error 色並顯示文字提示
6. TTL 60s 到期 → 背景重新抓取，時間戳更新，數值就地刷新（無進場動畫，僅數值替換）

### RWD 行為差異

| 斷點 | 佈局 | 差異說明 |
|------|------|---------|
| Desktop (≥1280px) | KPI 1x4 + 全寬表格 + 圖表/集中度 2 欄並排 | 完整體驗，欄寬可調 |
| Tablet (768-1024px) | KPI 2x2 + 全寬表格（橫向捲動）+ 圖表與集中度上下堆疊 | sidebar 收為 drawer |
| Mobile (<768px) | 全部單欄堆疊；DataTable 轉 card 式列表（< 1024px table→card），保留 Symbol/P&L%/Current 重點欄 | filter 收進 drawer |

### 資料更新策略

- Snapshot mode（預設）：刷新 TTL 60s 自動重抓，就地更新數值與時間戳
- Live mode（M5）：WebSocket 推送 current_price，pnl_pct / KPI / 圖表即時重算，無進場動畫
- 使用者離開分頁時暫停輪詢，返回時立即補抓一次

---

## [DATA & API]

- **uses_api**: true
- **主要資料表**: positions + universe + daily_bars
- **endpoints**:
  - GET `/api/positions/snapshot` — 取得 positions latest snapshot（含 qty / entry / days / stop_loss）
  - GET `/api/positions/prices` — 取得 current_price（daily_bars 或 live）
  - GET `/api/positions/kpi` — Portfolio Heat / Cash / Open / Equity 彙總
  - GET `/api/positions/industry-allocation` — 產業別市值彙總（join universe）
  - GET `/api/positions/concentration` — Top1/Top3/Top5 % 與 HHI
  - WS `/ws/positions/live` — live mode 即時報價推送（M5）
- **計算規則**:
  - `pnl_pct = (current_price - entry) / entry`
  - `industry` 由 universe join 取得
  - `HHI = Σ(mv_i / total)^2`，mv_i = 各部位市值
- **error_cases**:
  - 網路錯誤：顯示離線提示，沿用上一份快照並標記「資料可能過時」
  - API 錯誤：各 section 區域顯示友善錯誤 + 重試按鈕，不整頁崩潰
  - 權限不足：導向登入頁
  - 空快照（無持倉）：各 section 顯示 empty 態，KPI 顯示 "—"

---

## [EXCEPTION TO GLOBAL RULES]

- industry_allocation 圓餅圖（多產業類別）用 §6.1 **Categorical 8-色盤**（低飽和、dark 底 WCAG 達標）— 屬「chrome 單色、資料區受控離散色盤」例外，僅限圖表內容區，不汙染 chrome 單色。
- 其餘完全遵循 Global v2.0（Grok 單色 dark、flat 1px border #2A2A2A、Geist Mono 數值、白環 focus、漲跌雙編碼）。

---

## [ACCEPTANCE CRITERIA]

- [ ] 5 個 Section（header / KPI / table / pie / concentration）功能正常
- [ ] 每個 Section 四態完備（default / loading / empty / error）；table 另含 hover 態
- [ ] KPI 四項數值正確（Heat 含上限警示色 + 文字雙編碼）
- [ ] DataTable 支援排序 / 欄過濾 / column resize；P&L% 漲跌色 + 符號雙編碼
- [ ] 點列下鑽至面板 C 並帶入 Symbol filter
- [ ] 圓餅圖 hover 顯示金額；點扇區 cross-filter 表格
- [ ] 集中度 Top1/Top3/Top5 + HHI 計算正確，HHI 含集中度文字標記
- [ ] 所有數值 Geist Mono tabular-nums 右對齊
- [ ] RWD 三斷點行為正確（table→card @<1024px）
- [ ] dark-first（Grok 單色）、flat 1px border #2A2A2A 無陰影
- [ ] 即時數據刷新無進場動畫
- [ ] 產業圓餅用受控 Categorical 8-色盤（達 WCAG），不用 v1 鮮豔虹色
- [ ] 對比達標：一般文字 AA、KPI 數值 AAA；focus-visible ring 單色白環 rgba(245,245,245,.7)
- [ ] 刷新 TTL 60s 生效；live mode 預留 WebSocket 接口（M5）
