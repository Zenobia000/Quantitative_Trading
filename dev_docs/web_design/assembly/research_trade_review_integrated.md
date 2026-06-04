# Integrated Master Prompt — 逐筆覆盤 (Research · Trade Review)

> 由 `global/02_backtest_platform_brand_system.md`（壓縮 Tokens v2.0）+ `pages/research_trade_review.md` 組裝的最終 Prompt。
> 可直接貼給 Lovable / Claude。對應 `guides/lovable_組裝.md` SOP，格式同 `assembly/monitor_a_performance_integrated.md`。
> **路徑/契約以 `25_fe_be_rest_contract.md` §6 為準**（裸根 `/runs/{id}/*`）。歸因為**動態 N 因子/層**（讀 reason_json），非寫死四層。

---

## === GLOBAL PROJECT GUIDELINE (DO NOT OVERRIDE) ===

你是 backtest_platform 的資深前端產品架構師。以下為最高準則，所有元件必須繼承此處定義的配色、字體、形狀與間距；除非 EXCEPTION RULES 明確說明，否則不得違反。

```
# backtest_platform Design System — Compressed Tokens (Grok 單色 dark v2.0)
COLORS (monochrome — 無彩色品牌色)  primary/text #F5F5F5 ; 白底 pill 按鈕 text 用 base 深色
  bg-base #0F0F0F / bg-surface #1A1A1A / bg-input #1E1E1E / bg-code #161616 / border #2A2A2A
  text #F5F5F5 / text-secondary rgba(245,245,245,.65) / text-muted rgba(245,245,245,.55)
  gain #22C55E(配↑) / loss #F87171(配↓) / loss-aaa #FCA5A5
  success #F5F5F5+✓(不用綠以免與 gain 混) / warning #E9A60C / error #EF4444
  dataviz 單色優先: strategy #F5F5F5 實線 / benchmark rgba(255,255,255,.40) 虛線 ; 多序列用明度+線型
  受控例外(僅資料區, §6.1): Categorical 8-色盤(低飽和 WCAG) / Diverging gain↔灰↔loss / Sequential 灰階
TYPE  H1 28/600 H2 22/600 H3 18/600 Body 14/400 Label 13/500 Caption 12/500
  Metric 20-32/600 Geist-Mono tabular-nums ; UI font Inter / Noto Sans TC ; mono Geist Mono
SHAPE radius sm4 md8 lg12 ; NO shadow (1px border #2A2A2A) ; button 白底 pill radius 12px
GRID fluid 100% ; bp sm640 md768 lg1024 xl1280 ; section-gap 16-24px ; table→card & sidebar→drawer @<1024px
RULES Grok 單色 dark-first ; 無彩色品牌色 ; 文字 AA / KPI 數值 AAA ; 漲跌=色+↑↓文字雙編碼(唯一彩色) ; 即時數據無進場動畫 ; flat 分層 ; focus-visible 單色白環 rgba(245,245,245,.7)
```

**最高準則聲明**：Grok 單色 dark-first、無彩色品牌色、flat 1px border #2A2A2A 無陰影、數值一律 Geist Mono tabular-nums、漲跌以「顏色 + ↑↓ 文字」雙編碼、focus 單色白環、即時數據無進場動畫；此區段為唯一真實來源，不得被下游任務覆寫。

---

## === CURRENT TASK: BUILD 逐筆覆盤 (Trade Review) ===

實作某 run 的逐檔股票覆盤頁（route `/research/runs/:id/trades`）：個股 K 線疊 entry/exit marker、hover 回跳當日市場狀態與訊號因子分數，肉眼核對訊號合理性（IS gate FAIL 後重設進場最直接的 debug 工具）+ 因子/層級歸因下鑽。完整規格見 `pages/research_trade_review.md`，以下為 sections 重點摘要（勿重貼整份 spec）。

**Sections（由上至下，5 個）**

1. **review_header**（sticky）：RunRef（run_id + 策略版本 + IS/OOS 期間 + engine）+ SymbolSelector（該 run 有交易個股，依貢獻排序）+ PeriodRange + 返回 Run Report。
2. **candlestick_chart**（Plotly.js）：選定個股日 K（漲 gain/跌 loss）+ EntryMarkers ▲ + ExitMarkers ▼（依損益 gain/loss）+ StopLossLine（dashed warning）+ HoverBridge（hover bar → 觸發 context_drawer 當日因子分數/訊號）+ zoom/pan。
3. **trade_list**（DataTable round-trip，橫向捲動）：進場時間/價 + 出場時間/價 + 持有天數 + 報酬%（漲跌 ↑↓ 雙編碼）+ reason（truncate→reason_json）+ 點列高亮 K 線對應 marker。
4. **attribution**（因子/層級歸因，動態 N）：各因子/層貢獻 bar（單色明度階 + 文字標因子名與分數）+ per-trade 歸因表 + 標「哪因子/層在此失效」（服務重設進場）。**因子數動態讀 reason_json，非寫死四層。**
5. **context_drawer**（hover/點 marker 觸發）：當日因子分數 + 訊號 reason_json（JSONViewer bg-code #161616）+ 價量/籌碼摘要（若有 FinLab 資料）。

**互動重點**：自 Run Report 帶 run_id 載入、預選貢獻最大個股；切 SymbolSelector 重繪 K 線/trade/歸因；hover K 線 bar 或點 marker → context_drawer 回跳當日因子分數+reason；點 trade 列高亮 K 線 marker；歸因標失效因子 → 回研究迴圈改假設。

**資料/契約**：走 doc 25 裸根 `/runs/{id}/*`（`/traded-symbols`、`/trades?symbol=`、`/candles?symbol=&start=&end=`、`/attribution?symbol=`（回 reason_json 動態 N 因子）、`/day-context?symbol=&date=`）。run 為快照 TTL 300s；切個股懶載入。

**RWD**：Desktop K 線全寬 + trade list/歸因兩欄 + context 右 drawer；Tablet 單欄堆疊 + trade list 橫捲 + sidebar→drawer@<1024 + context 底部 sheet；Mobile K 線縮高觸控 + marker hover 改點選 + context 全屏 sheet。

---

## === EXCEPTION RULES ===

- candlestick_chart 的 K 棒漲/跌沿用既有 **gain/loss** 漲跌語義（紅綠 + entry ▲ / exit ▼ 符號雙編碼），屬交易剛需彩色，僅限圖表內容區。
- trade_list 在 @<1024px 橫向捲動不轉 card。
- 其餘完全遵循 Global Guideline。

---

## === OUTPUT REQUIREMENTS ===

1. **結構確認**：先列出 5 個 sections 與關鍵元件（review header + symbol selector / candlestick + ▲▼ markers / trade round-trip table / N 因子歸因 / context drawer）。
2. **一致性落實**：K 棒/marker gain-loss + ▲▼ 雙編碼僅限圖表區、數值 Geist Mono、reason_json 用 bg-code #161616、歸因因子數動態（非寫死四層）、flat border #2A2A2A、focus 單色白環。
3. **程式碼**：產出完整可運行 React + Tailwind + Plotly.js 代碼，含 candlestick + entry/exit markers + hover 回跳 context_drawer、round-trip trade table（點列高亮 marker）、動態 N 因子歸因、四態、橫向捲動 RWD。

---

*組裝日期: 2026-06-05 | 使用 backtest_platform Design System (Grok 單色 dark v2.0) | 逐筆覆盤 (M3)*
