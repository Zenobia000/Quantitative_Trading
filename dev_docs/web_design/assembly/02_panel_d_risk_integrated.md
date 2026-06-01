# INTEGRATED PROMPT — 面板 D 風控指標 (Risk Metrics)

> 將 Global Design System 與 `pages/02_panel_d_risk.md` 組裝成可直接貼給 Lovable 的最終 Prompt。
> 對應 `guides/lovable_組裝.md` SOP，格式對齊 `assembly/01_dashboard_integrated.md`。

---

## === GLOBAL PROJECT GUIDELINE (DO NOT OVERRIDE) ===

你是 backtest_platform 的資深前端產品架構師。以下設計系統為最高準則，所有元件必須繼承；除非 EXCEPTION RULES 明確說明，否則不得違反。

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

**最高準則聲明**：本區段為唯一視覺真理來源。配色、字體、圓角、間距、無陰影 flat 分層、雙編碼與無動畫規範一律以此為準，下方 TASK 僅描述結構與行為，不得覆寫此處 tokens。

---

## === CURRENT TASK: BUILD 面板 D 風控指標 ===

實作 `/dashboard/risk` 風控指標面板（React 版，自 Streamlit 升級）。目的：即時呈現策略當前風險水位並提供風險事件審計與 drill-down。主要使用者為操盤手 / 風控人員，交易時段高頻巡檢。

詳見 `pages/02_panel_d_risk.md`。以下為 sections 摘要（不重貼整份 spec）：

1. **risk_status_header**（status_badge）
   - 頂部 Status badge 三態：NORMAL(#22C55E) / WARN(#E9A60C) / CRITICAL(#EF4444)，色 + 文字雙編碼
   - 含資料時間戳（Geist Mono）+ 手動 refresh IconButton

2. **risk_water_levels**（3 條 progress bar / KPI Cards）
   - Current DD（-3.2% / Limit -15%，21%）、Daily PnL vs VaR95（38%）、Heat（4.2% / 6%，70%）
   - 水位條顏色：<60 綠 #22C55E / 60-85 琥珀 #E9A60C / >85 紅 #F87171，附文字百分比（雙編碼）

3. **mdd_trend_chart**（折線 + 3 hline）
   - 90 日 MDD 折線（dataviz #22D3EE）+ 3 條熔斷 hline：L1 暫停 -10% / L2 減倉 -15% / L3 全停 -20%
   - hover tooltip 顯示日期 + MDD 值 + 命中熔斷層級

4. **recent_risk_events**（DataTable + drill-down）
   - 近 7 日事件（`event_type IS NOT NULL`）：時間 / event_type(HEAT_WARN / CONCENT) / 說明
   - 列點擊 drill-down 開啟事件 context drawer

互動重點：頁載入並行抓 metrics + events；metrics TTL 30s、events TTL 60s 輪詢；手動 refresh 忽略 TTL；事件列 drill-down drawer。RWD：Desktop 水位 3 欄、Mobile 單欄堆疊 + table→card + drawer→全螢幕 sheet。

資料來源：`risk_metrics`(current_dd / var_95 / heat / concentration)；events = where event_type IS NOT NULL。API：GET `/api/risk/metrics`、`/api/risk/mdd-trend?window=90d`、`/api/risk/events?window=7d`、`/api/risk/events/{id}`。

---

## === EXCEPTION RULES ===

無特殊例外，完全遵循 Global Guideline。即時數據區嚴格無進場動畫；唯一動態回饋為手動 refresh 的 spinner。

---

## === OUTPUT REQUIREMENTS ===

1. **結構確認**：先列出 4 個 sections 及其關鍵元件（StatusBadge / 3× ProgressBar KPI Card / MDD LineChart + 3 ReferenceLine / Events DataTable + drill-down drawer）。

2. **一致性落實**：說明如何繼承 Global tokens——dark-first bg-base #0B1220 / bg-surface #131C2B、flat 1px border #243044 無陰影、所有數值 Geist Mono tabular-nums、Status badge 與 event tag 與水位條皆色 + 文字雙編碼、KPI 數值對比 AAA / 文字 AA、focus-visible ring 用 accent #22D3EE、即時數據無進場動畫。

3. **程式碼**：產出完整可運行 React + Tailwind + Recharts（MDD 折線用 LineChart + ReferenceLine；水位條可用自繪 div bar 或 Recharts）程式碼，包含：
   - 四態完備（default / loading skeleton / empty / error + 重試）每個 section 皆具備
   - RWD（Desktop ≥1024 三欄 / Tablet 壓縮 / Mobile <768 單欄 + table→card + drawer→sheet）
   - 水位條顏色門檻函式（<60 / 60-85 / >85）與 MDD hover 熔斷層級判定
   - 模擬資料以對齊規格數值（DD 21% / VaR 38% / Heat 70%）

---

*組裝日期: 2026-06-01 | 使用 backtest_platform Global System (compressed) | 面板 D 風控指標*
