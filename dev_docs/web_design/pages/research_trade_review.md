# Page Layer Spec — 逐筆覆盤 (Research · Trade Review)

> 來源：補強需求（回看每隻策略在哪檔股票的進出場點位）；把 `research_04_run_report.md` 的 `TradeListLink`（疊 K 線 + hover 回跳）展開成完整頁。
> 對齊 `03` §taxonomy「Trade markers 疊 K 線 + hover 回跳」（✅ ADR-017 重設進場最直接的 debug 工具）+ §1.5「逐筆 trade 表可回跳市場狀態」+「四層共振歸因下鑽」。
> 繼承 Global v2.0（**Grok 單色 dark** / Geist Mono 數值 / 白環 focus / 漲跌 ↑↓ 雙編碼）。
> **狀態**：M3 設計 spec；assembly 隨 React 化再產出。

---

## [PAGE META]

- **page_name**: 逐筆覆盤 (Trade Review)
- **route_path**: /research/runs/:id/trades
- **page_type**: detail (review)
- **primary_goal**: 讓研究者對某 run 逐檔股票回看進出場點位——個股 K 線疊 entry/exit marker、hover 回跳當日市場狀態與四層共振分數，肉眼核對訊號合理性，作為 IS gate FAIL 後重設進場的直接 debug 工具。
- **secondary_goal**: 以四層共振歸因下鑽，量化每筆交易/每檔股票各層（L1–L4）的貢獻，找出「哪一層在這檔/這段失效」。
- **target_users**:
  - 主要：量化研究者（覆盤、重設進場邏輯）
  - 次要：操盤手（核對 live 策略某檔進出場是否如預期）
- **entry_point**: Run Report `next_step_bar` 的「逐筆 trade 表」連結；Panel C 訊號日誌「看此訊號在 run 內的進出場」；Cmd-K「跳覆盤 by run id」。
- **expected_time_on_page**: 5–15 分鐘（選股 → 看 K 線 marker → hover 核對 → 歸因下鑽 → 回研究迴圈改假設）

---

## [STRUCTURE: SECTIONS]

> 由上至下，共 5 個功能區塊。

1. **review_header**
   - section_type: toolbar / context
   - section_purpose: 顯示 run ref（id / 策略版本 / IS-OOS 期間）+ 標的選擇器（哪一檔股票）+ 期間範圍，驅動下方覆盤。

2. **candlestick_chart**
   - section_type: chart (candlestick + markers)
   - section_purpose: 選定個股的 K 線圖，疊 entry（▲）/ exit（▼）marker + 停損線；hover 任一 bar 回跳當日市場狀態與四層共振分數。

3. **trade_list**
   - section_type: data_table (round-trip)
   - section_purpose: 該股逐筆 round-trip（進場時間/價、出場時間/價、持有天數、報酬、觸發 reason）；點列高亮 K 線對應 marker。

4. **resonance_attribution**
   - section_type: chart + stats（四層共振歸因）
   - section_purpose: 該筆/該股各層 L1–L4 貢獻分解（哪層帶 alpha、哪層拖累），對映四層共振計分。

5. **context_drawer**
   - section_type: drawer（hover/點選觸發）
   - section_purpose: 回跳某日市場狀態快照——當日四層分數、訊號 reason_json、價量籌碼 context。

---

## [SECTION COMPONENT SPEC]

### Section: review_header

- **layout**: 1-row context bar，sticky top。
- **elements**:
  - RunRef: Mono / required / run_id + 策略版本 + IS/OOS 期間 + engine。
  - SymbolSelector: Select（含搜尋）/ required / 該 run 有交易的個股清單（依貢獻/交易數排序）。
  - PeriodRange: DateRange / optional / 縮放覆盤區間（default 該股首進場–末出場）。
  - BackToReport: Link / required / 返回 Run Report。
- **states**:
  - default: 預選貢獻最大個股。
  - loading: header skeleton。
  - empty: 該 run 無 trade → 「此 run 無逐筆交易（可能未成交或純訊號）」。
  - error: inline error + 重試。
- **copy_constraints**: run_id mono；期間 ISO。

### Section: candlestick_chart

- **layout**: 全寬 K 線圖；高度 360–460px；右上 marker 圖例。
- **elements**:
  - Candles: Candlestick series（Plotly.js）/ required / 個股日 K，**漲 gain / 跌 loss**（沿用漲跌語義）。
  - EntryMarkers: Marker ▲ / required / 進場點（gain 色 + ▲，hover 顯進場價/原因）。
  - ExitMarkers: Marker ▼ / required / 出場點（loss/gain 依損益 + ▼，hover 顯出場價/報酬）。
  - StopLossLine: ReferenceLine / optional / 停損價（dashed warning）。
  - HoverBridge: 互動 / required / hover 任一 bar → 觸發 context_drawer 顯當日四層分數/訊號（回跳市場狀態）。
  - ZoomPan: 互動 / required / 框選 zoom / 拖曳 pan / 雙擊 reset。
- **states**:
  - default: K 線 + entry/exit marker + 圖例。
  - loading: 圖表 skeleton。
  - empty: 該股無 K 線資料 → 置中提示。
  - error: 「K 線載入失敗」+ 重試。
- **copy_constraints**: marker 圖例 ≤ 8 字（進場/出場）；價格 tabular-nums。

### Section: trade_list

- **layout**: 全寬 DataTable（round-trip）；橫向捲動保密度。
- **elements**:
  - EntryCols: Mono / required / 進場時間（ISO）+ 進場價。
  - ExitCols: Mono / required / 出場時間 + 出場價。
  - HoldingDays: Mono / required / 持有天數。
  - PnlCell: Mono / required / 報酬 %（漲跌 ↑↓ + 色雙編碼）。
  - ReasonCell: Text (truncate) / required / 進/出場觸發 reason（溢出 tooltip / 點開 reason_json）。
  - RowHighlight: 互動 / required / 點列 → 高亮 K 線對應 entry/exit marker + 滾動定位。
- **states**:
  - default: 依進場時間排序。
  - loading: 列 skeleton。
  - empty: 該股無 round-trip。
  - error: inline error + 重試。
- **copy_constraints**: reason 單行 ≤ 40 字；比率 2 位小數。

### Section: resonance_attribution

- **layout**: 上 4 層貢獻 bar，下 per-trade 歸因表。
- **elements**:
  - LayerBars: Bar ×4 / required / L1–L4 各層對該股/該筆的貢獻（單色明度階 + 文字標層名與分數）。
  - AttributionTable: DataTable / optional / 每筆 trade 的四層分數 + 結果（命中/失效，色+文字）。
  - WeakLayerNote: Inline / required / 標「哪一層在此失效」（服務重設進場）。
- **states**:
  - default: 4 層 bar + 歸因。
  - loading: skeleton。
  - empty: 「無歸因資料（需四層分數留存）」。
  - error: inline error + 重試。
- **copy_constraints**: 層名固定 L1–L4 + 中文標籤；分數 2 位小數。

### Section: context_drawer

- **layout**: 右側 drawer（hover bar / 點 marker 觸發）。
- **elements**:
  - DaySnapshot: Stats / required / 當日四層共振分數（L1–L4）+ 總分。
  - SignalReason: JSONViewer（bg-code #161616 / Geist Mono）/ required / 當日訊號 reason_json（scores / prices / context）。
  - PriceVolChip: Mini / optional / 當日價量 / 籌碼摘要（法人 / 主力，若有 FinLab 資料）。
- **states**:
  - default: 隱藏，hover/點選顯示。
  - loading: drawer skeleton。
  - empty: 「該日無訊號 context」。
  - error: inline error。
- **copy_constraints**: 分數 tabular-nums。

---

## [INTERACTION & STATE FLOW]

### 主要互動流程

1. 自 Run Report 帶 run_id 載入 → review_header 預選貢獻最大個股 → 渲染 K 線 + marker + trade list + 歸因。
2. 切換 SymbolSelector → 重繪該股 K 線 / trade list / 歸因。
3. hover K 線某 bar 或點 marker → context_drawer 回跳當日四層分數 + 訊號 reason（核對進場合理性）。
4. 點 trade_list 某列 → 高亮 K 線對應 entry/exit marker。
5. resonance_attribution 標「哪層失效」→ 回研究迴圈（New Run / Validate）改假設。

### RWD 行為差異

| 斷點 | 佈局 | 差異說明 |
|------|------|---------|
| Desktop (≥1280px) | K 線全寬；trade list + 歸因兩欄；context 右 drawer | 側邊導覽展開 |
| Tablet (768–1279px) | 單欄堆疊；trade list 橫向捲動 | sidebar→drawer（@<1024px）；context 改底部 sheet |
| Mobile (≤767px) | K 線縮高觸控；trade list 橫向捲動 | marker hover 改點選；context 全屏 sheet |

### 資料更新策略

- run 為快照（done 後不變）→ 快取 TTL 300s。
- 切換個股懶載入該股 K 線 + trade + 歸因。

---

## [DATA & API]

- **uses_api**: true
- **主要資料表**: `runs` + `fills`/trade（逐筆）+ `daily_bars`（個股 K 線）+ `signals`（reason_json / 四層分數）。
- **endpoints**:
  - GET `/api/research/runs/:id/traded-symbols` — 該 run 有交易的個股 + 貢獻排序。
  - GET `/api/research/runs/:id/trades?symbol=` — 該股逐筆 round-trip（進/出場時間價、報酬、reason）。
  - GET `/api/research/runs/:id/candles?symbol=&start=&end=` — 個股 K 線 + entry/exit marker 座標。
  - GET `/api/research/runs/:id/attribution?symbol=` — 四層共振歸因。
  - GET `/api/research/runs/:id/day-context?symbol=&date=` — 當日四層分數 + 訊號 reason（context_drawer）。
- **error_cases**:
  - run 無 trade（200 空）：review_header empty。
  - 個股無 K 線：candlestick empty。
  - 無四層分數留存：attribution empty（提示需後端留存分數）。
  - 網路錯誤：section 級 inline error + 重試。

---

## [EXCEPTION TO GLOBAL RULES]

- candlestick_chart 的 K 棒漲/跌沿用既有 **gain/loss** 漲跌語義（紅綠 + entry ▲ / exit ▼ 符號雙編碼），屬交易剛需彩色，非新增語彙；僅限圖表內容區。
- trade_list 在 @<1024px 橫向捲動不轉 card。
- 其餘完全遵循 Global v2.0。

---

## [ACCEPTANCE CRITERIA]

- [ ] 5 個 section（review_header / candlestick_chart / trade_list / resonance_attribution / context_drawer）功能正常。
- [ ] candlestick 疊 entry（▲）/ exit（▼）marker，漲跌 + 符號雙編碼；hover bar 回跳當日四層分數 + 訊號 reason。
- [ ] SymbolSelector 切換個股重繪 K 線 / trade / 歸因。
- [ ] trade_list round-trip（進/出場時間價、報酬、reason）；點列高亮 K 線對應 marker。
- [ ] resonance_attribution 顯 L1–L4 貢獻 + 標「哪層失效」（服務重設進場）。
- [ ] context_drawer 回跳當日四層分數 + reason_json（bg-code #161616）。
- [ ] 每 section 四態完備；K 線/trade 在 @<1024px 橫向捲動不轉 card。
- [ ] 數值 Geist Mono tabular-nums；文字 AA / KPI AAA；focus 白環。
- [ ] dark-first（Grok 單色）、flat 1px border #2A2A2A 無陰影。
