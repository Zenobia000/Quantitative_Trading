# Integrated Master Prompt — 面板 A 績效總覽 (Panel A · Performance Overview)

> 將 backtest_platform Global Design System 與 `pages/monitor_a_performance.md` 組合的最終 Prompt。
> 可直接貼給 Lovable / Claude。對應 `guides/lovable_組裝.md` SOP，格式同 `assembly/01_dashboard_integrated.md`。

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

## === CURRENT TASK: BUILD 面板 A 績效總覽 (Panel A · Performance Overview) ===

實作 React 版績效總覽儀表板（route `/monitor/performance`），讓使用者在單一畫面評估某策略相對 benchmark(0050) 的績效，並支援 drill-down 至面板 C。資料來源：`equity_snapshots` + `daily_bars(0050)`。完整規格見 `pages/monitor_a_performance.md`，以下為 sections 重點摘要（勿重貼整份 spec）。

**Sections（由上至下，6 個）**

1. **filter_bar**（sticky toolbar）：StrategySelector(下拉 `strategy_id`) + DateRangePicker(雙日期, default `[end-1y, end]`) + RefreshButton(清快取 rerun) + LastUpdatedLabel。任一變更即重查重繪全頁。
2. **kpi_overview**（6-up KPI Card）：Total Return / CAGR / Sharpe / MDD / Win Rate / Trades。數值 Geist Mono、漲跌雙編碼、hover 顯示同期變化；Sharpe 純數值不上漲跌色。KPI 用 quantstats 計算。
3. **equity_curve**（line, dual-series）：strategy(白實線 #F5F5F5) + benchmark 0050(灰虛線 rgba(255,255,255,.40), normalize 同起點)；zoom/pan/hover tooltip；點某日 drill-down 跳面板 C(帶 `date`+`strategy_id`)。
4. **drawdown_chart**（filled area）：loss 色透明填色，drawdown 已預算；time axis 與 equity_curve 連動 zoom/pan。
5. **rolling_sharpe**（line + SegmentedControl）：window 30/60/90 可調(default 60D)，pandas rolling 重算。
6. **monthly_heatmap**（year×month heatmap）：monthly resample pct_change，gain/loss 漸層，hover 精確報酬率。

**互動重點**：filter change / page load / 手動 refresh 觸發重查；快取 TTL 300s；equity↔drawdown time axis 連動；rolling window 切換優先本地重算；equity drill-down 帶 filter 跳轉 `/monitor/signals`。

**Streamlit→React 映射**：`st.metric`→KPI Card、`st.dataframe`→DataTable、Plotly 圖→Recharts 或 Plotly.js 元件；保留所有原互動。

**RWD**：Desktop(≥1280) KPI 1×6 + sidebar 展開；Tablet(768–1279) KPI 2×3 + sidebar→drawer；Mobile(≤767) 單欄堆疊 + heatmap 橫向捲動。

---

## === EXCEPTION RULES ===

無特殊例外，完全遵循 Global Guideline。
（Sharpe KPI 不套漲跌雙編碼，以 text 主色呈現 — 屬數值判讀慣例，非違反 Global。）

---

## === OUTPUT REQUIREMENTS ===

1. **結構確認**：先列出 6 個 sections 及各自關鍵元件清單（filter_bar / kpi_overview / equity_curve / drawdown_chart / rolling_sharpe / monthly_heatmap）。
2. **一致性落實**：說明如何套用 Global Tokens — Grok 單色 dark 配色、border #2A2A2A flat 無陰影、KPI 數值 Geist Mono tabular-nums 達 AAA 對比、漲跌色+↑↓文字雙編碼、benchmark 灰虛線、即時數據無進場動畫、focus-visible 單色白環。
3. **程式碼**：產出完整可運行的 React + Tailwind + Recharts(或 Plotly.js) 代碼。必須包含：
   - 每個 section 四態（default / loading skeleton / empty / error）。
   - RWD 三斷點行為（table→card、sidebar→drawer @<1024px）。
   - 互動：filter change 即重查、rolling window 切換、refresh 清快取(TTL 300s)、equity drill-down 帶 filter、equity↔drawdown time axis 連動。

---

*組裝日期: 2026-06-01 | 使用 backtest_platform Global System (Compressed Tokens) | 面板 A · 績效總覽 (M3)*
