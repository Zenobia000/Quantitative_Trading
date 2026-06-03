# Integrated Prompt: 面板 B — 部位狀態 (Positions)

> 由 `global/02_backtest_platform_brand_system.md`（壓縮 Tokens）+ `pages/monitor_b_positions.md` 組裝。
> 可直接整段貼給 Lovable / Claude。對應 `lovable_組裝.md` SOP Step 2。

---

## === GLOBAL PROJECT GUIDELINE (DO NOT OVERRIDE) ===

你是 backtest_platform 的資深前端產品架構師。以下設計系統為**整個專案的最高準則**，所有元件必須繼承此處定義的配色、字級、間距、圓角與斷點；除非下方 EXCEPTION RULES 明確說明，否則一律不得違反。

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

最高準則聲明：**Grok 單色 dark-first、無彩色品牌色、flat 1px border #2A2A2A 無陰影、Geist Mono 數值、漲跌色+↑↓雙編碼、focus 單色白環、即時數據無動畫。任何輸出不得偏離上述 Tokens。**

---

## === CURRENT TASK: BUILD 面板 B — 部位狀態 (Positions) ===

本次任務：依上方 Global Guideline，實作 backtest_platform M3 的「部位狀態」儀表板頁面（route `/monitor/positions`）。資料來源：positions + universe + daily_bars。這是 React 版（自 Streamlit 升級）：`st.metric` → KPI Card、`st.dataframe` → DataTable、Plotly 圖 → Recharts/Plotly.js。

需實作 5 個 Section（細節摘要，完整規格見 `pages/monitor_b_positions.md`）：

1. **header_bar**（page_header）：H1「部位狀態」+ 資料時間戳 `as of YYYY-MM-DD HH:mm:ss TWT`（mono）+ Snapshot/Live badge（live = M5 WebSocket）。
2. **kpi_row**（stats_cards，1x4 → 2x2 → 1欄）：
   - Portfolio Heat 4.2% / 上限 6%（≥80% 上限轉 warning 並標「接近上限」，達標轉 error；色+文字雙編碼）
   - Cash NT$ + %、Open 12/15、Equity NT$。
   - Metric 用 Geist Mono tabular-nums 右對齊。
3. **positions_table**（DataTable）：欄 Symbol / Industry / Qty / Entry / Current / P&L% / Days / StopLoss；支援排序、欄過濾、column resize；數值欄 mono 右對齊；`P&L% = (current-entry)/entry`，漲 gain 跌 loss + ▲/▼ 符號雙編碼；點列 → 下鑽面板 C（帶 Symbol filter）。
4. **industry_allocation**（go.Pie / Recharts Pie）：產業別市值佔比，色盤用 §6.1 受控 Categorical 8-色盤（低飽和 WCAG，非 v1 虹色）；hover 顯示金額(NT$)+佔比；點扇區 → cross-filter positions_table。
5. **concentration_risk**（KPI Card x4 ≈ st.metric x3+）：Top1/Top3/Top5 %、HHI 0.18「低集中」（`HHI = Σ(mv_i/total)^2`，<0.15 低 / 0.15-0.25 中 / >0.25 高）。

關鍵互動與資料：
- 刷新 TTL 60s 自動重抓並就地更新數值（無進場動畫）；live mode 預留 WebSocket（M5）。
- `industry` 由 universe join 取得；current_price 來自 daily_bars / live。
- RWD：Desktop 圖表與集中度 2 欄並排；< 1024px table→card、sidebar→drawer；Mobile 全單欄堆疊。
- 四態完備（default / loading=skeleton / empty / error+重試），table 另含 hover 提示可下鑽。

---

## === EXCEPTION RULES ===

無。完全遵循 Global Guideline。

---

## === OUTPUT REQUIREMENTS ===

1. **結構確認**：先列出 5 個 Section 與其關鍵元件清單（KPI x4 欄位、DataTable 8 欄、Pie、集中度 4 metric）。
2. **一致性說明**：簡述如何落實設計一致性 — 配色僅取自上方 Tokens（Grok 單色）、數值一律 Geist Mono tabular-nums 右對齊、漲跌與 Heat 警示採色+文字雙編碼、flat 1px border #2A2A2A 無陰影、即時刷新無進場動畫、focus-visible 單色白環 rgba(245,245,245,.7)。
3. **程式碼**：產出完整可運行的 **React + Tailwind + Recharts/Plotly.js** 代碼，涵蓋 5 個 Section、四態（default/loading/empty/error）與 RWD 三斷點（含 table→card @<1024px）；KPI 與集中度用 Card，表格用可排序/過濾/resize 的 DataTable，圓餅圖用 Recharts Pie 或 Plotly.js go.Pie，並接上點列下鑽與扇區 cross-filter 的互動。

---

*組裝日期: 2026-06-01 | 使用 backtest_platform Design System (Grok 單色 dark v2.0) | 面板 B — M3 Positions*
