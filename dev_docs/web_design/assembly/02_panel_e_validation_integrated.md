# Integrated Prompt: 面板 E — 統計驗證 (M5)

> 將 backtest_platform 壓縮版 Global Tokens 與 `pages/02_panel_e_validation.md` 組合的最終 Master Prompt。
> 直接整段貼給 Lovable / Claude。對應 `lovable_組裝.md` SOP Step 2。

---

## === GLOBAL PROJECT GUIDELINE (DO NOT OVERRIDE) ===

你是 backtest_platform 量化回測平台的資深前端架構師。下方為整個專案的設計系統，是**最高準則**：所有元件必須繼承此處定義的配色、字級、間距、圓角與斷點，除 EXCEPTION RULES 明列者外不得違反。

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

最高準則聲明：**dark-first、flat（1px border #243044、無陰影）、所有數值用 Geist Mono tabular-nums、風險/漲跌一律「色 + 文字」雙編碼、即時數據無進場動畫。此區段優先於任何後續描述。**

---

## === CURRENT TASK: BUILD 面板 E — 統計驗證 (Statistical Validation) ===

本次任務：依上方 Global Guideline，實作策略統計驗證面板（route `/dashboard/validation`，主要資料表 `validation_runs`）。此面板讓研究員判斷策略樣本外 (OOS) 是否穩健、是否過擬合。完整規格見 `pages/02_panel_e_validation.md`，以下為要點摘要（勿重貼整份 spec）：

**Sections（由上至下 4 個）：**

1. **summary_bar**（摘要列）— 一行三欄：Latest WFA Run 日期 / Windows 數 / IS-OOS 配置「24m / 6m」。資料取 `validation_runs WHERE method='WFA'` 最新 run。
2. **wfa_scatter**（散點圖）— IS Sharpe (X) vs OOS Sharpe (Y) 散點，每點一個 window；含 y=x 對角線參考（dashed benchmark 色），對角線**上方=OOS≥IS=穩健（gain 綠）**、下方=衰退（loss 紅）。hover tooltip 顯示 window 編號 / IS·OOS Sharpe / 期間。穩健與衰退需色+形狀/文字雙編碼。
3. **risk_kpi**（KPI 卡 x3）— PBO（例 0.18，註「低過擬合」）/ DSR（例 0.82，註「顯著」）/ Min Track Record Length (months)。**PBO 高 → 卡片轉 warning/error 色並附文字標記（雙編碼）**；DSR 達門檻用 success 綠。數值 Metric 字級、Geist Mono、AAA 對比。
4. **rolling_trend**（雙折線）— Rolling 30D 的 PBO 與 DSR 兩條折線（PBO 用 #F59E0B、DSR 用 accent #22D3EE），圖例色+文字雙編碼，hover 同步 cursor tooltip。

**互動與資料：**
- 並行打三支 API：`GET /api/validation/wfa/latest`、`GET /api/validation/metrics/latest`（`method IN ('PBO','DSR') ORDER BY run_time DESC`）、`GET /api/validation/rolling?window=30`。
- 快取 **TTL = 300 秒**；refresh 按鈕強制刷新。離線批次產物，非即時。
- 四態必備：default / loading(skeleton) / empty / error(重試按鈕)，empty 與 error 明確區分，各 section 獨立錯誤不整頁崩潰。

**RWD：** Desktop ≥1280 完整 4 欄/全寬圖；Tablet 768-1024 KPI 維持或 2+1、@<1024 sidebar→drawer；Mobile <768 全單欄堆疊、table→card、圖例移圖下、觸控 tooltip。

**Streamlit → React 對應：** st.metric → KPI Card；st.dataframe → DataTable；Plotly 圖 → Recharts（`<ScatterChart>`/`<LineChart>`/`<ReferenceLine>`）或 Plotly.js。保留原互動（drill-down hover、filter、refresh TTL）。

---

## === EXCEPTION RULES ===

無。完全遵循 Global Guideline。

---

## === OUTPUT REQUIREMENTS ===

1. **結構確認**：先列出本面板 4 個 sections（summary_bar / wfa_scatter / risk_kpi / rolling_trend）及各自關鍵元件清單。
2. **一致性說明**：簡述如何落實 Global System — 配色僅取自上方 Tokens、KPI 數值用 Geist Mono tabular-nums 達 AAA、風險/穩健用色+文字雙編碼、flat 1px border 無陰影、即時數據無動畫、focus ring 用 accent #22D3EE。
3. **程式碼**：產出完整可運行的 **React + Tailwind + Recharts（或 Plotly.js）** 代碼，須包含：
   - 四個 section 元件與 KPI 警示色切換邏輯（PBO 高 → warning/error + 文字標記）
   - WFA scatter 的 y=x 對角線 ReferenceLine 與穩健/衰退雙編碼
   - Rolling 30D 雙折線
   - 每個 section 的 **default / loading(skeleton) / empty / error(重試)** 四態
   - 三斷點 **RWD**（@<1024 sidebar→drawer、table→card；Mobile 單欄堆疊）
   - 資料 fetch 以 TTL=300s 快取 + 手動 refresh

---

*組裝日期: 2026-06-01 | 使用 backtest_platform Global System (dark-first) | 對應 pages/02_panel_e_validation.md*
