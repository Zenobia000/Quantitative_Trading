# ADR-034: 逐筆覆盤 K 線改用 TradingView lightweight-charts（棄 spec 指定的 Plotly.js）

> **狀態：** 已接受 | **日期：** 2026-07-02 | **決策者：** Self
> **偏離（deviates from）：** [`web_design/pages/research_trade_review.md`](../web_design/pages/research_trade_review.md) §candlestick_chart — 該 spec 於 `Candles` 元素指定 `Candlestick series（Plotly.js）`；本 ADR 記錄實作改採 lightweight-charts 的理由與取捨。
> **相關：** [ADR-028](./ADR-028-strategy-dispatch-contract.md)（策略契約 — marker 重推依 four_layer per-bar 訊號）、[25_fe_be_rest_contract.md](../25_fe_be_rest_contract.md) §6（`/runs/{id}/candles` 契約）

---

## 1. 背景與問題

逐筆覆盤頁（`/research/runs/:id/trades`）的核心區塊 `candlestick_chart` 需要一張個股日 K 線圖，疊 entry ▲ / exit ▼ 進出場 marker，作為「IS gate FAIL 後重設進場」最直接的肉眼 debug 工具（spec §primary_goal）。設計 spec 在元件層指定 **Plotly.js** 作 candlestick series。

實作前重新評估圖表庫時發現，Plotly.js 對一張「K 線 + 少量 marker」的需求而言成本偏高：

- **bundle 體積**：Plotly.js 完整 bundle ~3.5MB（min），即使 partial import（`plotly.js-basic-dist` + finance module）仍 ~1MB 級。本前端目前總 JS bundle ~180KB gzipped；引入 Plotly 會使單一頁面的圖表庫**數倍於整個 app**。
- **用途錯配**：Plotly 是通用科學繪圖庫（3D、統計、地圖…），K 線只是其 finance 子集；為一個專用圖表付通用庫的稅。
- **既有前端無 Plotly**：引入等於新增一條重依賴，且 React 19 + Vite 6 下 Plotly 的 SSR/tree-shaking 體驗不佳。

## 2. 考量的選項

### 選項一：照 spec 用 Plotly.js
- **描述**：`plotly.js-finance-dist` 或 partial bundle + `react-plotly.js`。
- **優點**：spec 一致；互動（zoom/pan/hover）開箱即用。
- **缺點**：bundle ~1MB+ 級（見 §1），為單頁需求付通用庫稅；與現有輕量 bundle 哲學衝突。**拒絕。**

### 選項二（★採納）：TradingView lightweight-charts v5
- **描述**：專為金融 K 線設計的 canvas 圖表庫（npm `lightweight-charts`），v5 API：`addSeries(CandlestickSeries, …)` + `createSeriesMarkers` plugin。
- **優點**：
  - **bundle ~45KB gzipped**（約 Plotly 的 1/20），與現有 app 量級相稱。
  - **專為 K 線而生**：candlestick series、marker、price line、zoom/pan/crosshair 皆一級公民；漲跌雙色、business-day 時間軸原生支援。
  - MIT 授權、TradingView 官方維護、活躍。
- **缺點**：v5 API 與 v4 不相容（`addCandlestickSeries` → `addSeries(CandlestickSeries)`；marker 從 `series.setMarkers` 移到獨立 `createSeriesMarkers` plugin）——需針對「實際安裝版本」寫，不可照舊教學。已對 `node_modules` 型別確認後撰寫。
- **採納。**

### 選項三：手刻 SVG/canvas K 線
- **描述**：自繪 candlestick。
- **缺點**：zoom/pan/crosshair/marker 全部自理，重造輪子且易錯；無收益。**拒絕。**

## 3. 決策

**採納選項二。** 逐筆覆盤 K 線以 **lightweight-charts v5** 實作，明文偏離 spec 的 Plotly.js 指定。偏離僅限「圖表庫選型」——spec 的視覺語義（漲跌 gain/loss 雙色、entry ▲ belowBar / exit ▼ aboveBar、marker 圖例）完全遵循。

### 3.1 前端結構
- `features/research/lib/candleTransform.ts`：純轉換（`toCandlestickData` / `toSeriesMarkers`），**無 DOM/canvas**，jsdom 可單元測試；lightweight-charts 僅 `import type`（編譯期抹除）。
- `features/research/components/CandlestickChart.tsx`：只管 chart 生命週期 + 由 CSS token 解析主題色（canvas 無法吃 `var()`）。jsdom 無 canvas → 測試 mock `'lightweight-charts'`，不在單元測試渲染真圖（真圖驗證留 Playwright e2e）。

### 3.2 後端契約（`GET /runs/{id}/candles`）
- 讀 run record 取 `stocks` + IS window → 讀 parquet OHLC 快取（`daily_bars__<sid>.parquet`）→ 疊 marker。
- **查詢參數 `?symbol=`**（選填，缺省=run 首檔）：對齊 sibling `/runs/{id}/trades?symbol=` 的既有慣例（#166 review finding，2026-07-02 —— 初版用 `?stock=`，與 sibling 不一致，改 `?symbol=`）。回應欄位同步為 `{symbol, symbols[]}`（HTTP 層一律 `symbol`；`run_candles.py` 內部與 data 層仍用 `stock`，對映 `stock_id` / `daily_bars__<stock_id>` / ledger `stocks` 欄位）。
- **marker 來源**：per-run trades sidecar 只存 `{ret, hold, entry_structure}`（無日期/價/個股），無法定位 marker；故**由 run 的訊號管線就該股重推** entry/exit（`four_layer.sim.signaled_window` 的 `buy`→`stoploss`/`exit` 成對）。只有 per-stock event-driven 的 four_layer 有 per-bar 進出場；cross-sectional panel 策略（momentum/inst_flow）誠實回空 marker（非假造）。
- **typed-empty**：該股無 parquet → `meta.data_source="pending"` 空殼（非 500、非假數字，對齊 `frontend/GOAL.md` #8 與 system.py 慣例）；未知 run → 404 envelope-error。

### 3.3 停損線暫略
spec `StopLossLine` 為 optional。逐筆 trade 未攜帶停損價欄位，**不憑空推算**（不假造資料）；停損線待 trade schema 帶停損欄位後再補。

## 4. 影響與後果

### 4.1 受影響模組
- **新增**：`research/run_candles.py`（candles + marker 組裝）、`api/routers/runs_series.py` 新增 `/candles` 端點、前端 `api/candles.ts` / `hooks/useRunCandles.ts` / `lib/candleTransform.ts` / `components/CandlestickChart.tsx`，`TradeReviewPage.tsx` 接線（取代 candles PendingNote）。
- **新依賴**：`lightweight-charts`（frontend dependencies）。
- **契約漂移**：`frontend/openapi.json` + `src/types/api.gen.ts` 重生（新端點入 spec，`check_openapi_drift.py` 綠）。

### 4.2 破壞性變更
無。純新增端點 + 新前端元件；既有 `/equity`·`/trades` 與其他頁面零改動。

### 4.3 後續動作
- [ ] attribution（因子歸因）/ context_drawer / hover 回跳 / trade_list row→marker 高亮：待後端 `/attribution`·`/day-context` 與訊號分數留存（仍 deferred，spec 保留 PendingNote）。
- [ ] 停損線：待逐筆 trade schema 帶停損欄位。
- [ ] panel 策略（momentum/inst_flow）的 per-bar 進出場 marker：需 panel 訊號留存 per-stock 事件後再補（現誠實回空）。
