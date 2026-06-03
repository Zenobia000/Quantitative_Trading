# Integrated Master Prompt — Run Report (Research · Single Run Report)

> 由 `global/02_backtest_platform_brand_system.md`（壓縮 Tokens v2.0）+ `pages/research_04_run_report.md` 組裝的最終 Prompt。
> 可直接貼給 Lovable / Claude。對應 `guides/lovable_組裝.md` SOP，格式同 `assembly/monitor_a_performance_integrated.md`。
> **複用 Panel A** 的 equity/drawdown/rolling/heatmap 元件（design token 一致）。

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

## === CURRENT TASK: BUILD Run Report (Single Run Report) ===

實作單一 run 結果頁（route `/research/runs/:id`）：先看形狀秒判再下鑽歸因——KPI banner（複用 Panel A）→ 業界慣例 tear sheet → 事前承諾 vs 實際對照 → Reproduce 卡，並承接 queued/running/error 執行態。完整規格見 `pages/research_04_run_report.md`，以下為 sections 重點摘要（勿重貼整份 spec）。

**Sections（由上至下，6 個）**

1. **run_status_banner**（非 done 時）：StatusBadge(queued/running/validating/error) + ProgressBar + ExecutionLog(bg-code #161616, error 攤開) + CrossCheckNote(雙引擎對拍 zipline vs vectorbt 超容差標分歧、阻擋落地) + RetryButton。
2. **kpi_banner + reproduce_card**：6 KPI（**複用 Panel A**：Total Return/CAGR/Sharpe/MDD/WinRate/Trades）+ ReproduceCard(git-sha+bundle+engine+13 參數+成本，一鍵複製 CLI) + LineageLink(父/子 run)。
3. **tear_sheet**（慣例順序，不可亂序）：cumulative returns(白實線+benchmark 灰虛線) → drawdown underwater(loss 填色)+worst-N DD 表 → rolling Sharpe(30/60/90D) → monthly heatmap(**diverging 色階**) → **return distribution histogram**(**sequential 灰階**)。
4. **boundary_markers**：equity 疊 IS/OOS/paper/live 邊界 ReferenceLine（dashed+文字標籤）+ 預期 cone。
5. **hypothesis_check**：3-up 預期 vs 實際 OOS 自動紅/綠對照。
6. **next_step_bar**（sticky bottom）：再迭代 / 多 run 比較 / 送驗證(白 pill, 需 done) + 逐筆 trade 表入口。

**互動重點**：非終態輪詢至 done/error；對拍超容差轉 error 標分歧；rolling window 本地重算；done 後報表為快照；next_step 分流（New Run baseline / Compare / Validate gate）。

**RWD**：Desktop KPI 1×6 + reproduce 右欄；Tablet KPI 2×3；Mobile 1×6 + 圖表縮高 + worst-N DD 表橫向捲動。

---

## === EXCEPTION RULES ===

- **monthly heatmap 用 Diverging 色階**（gain ↔ 中性灰 ↔ loss）、**return distribution 用 Sequential 灰階** — 屬 §6.1「chrome 單色、資料區受控彩色」例外，沿用既有漲跌語義零新增語彙，僅限圖表內容區。
- worst-N DD 表在 @<1024px 橫向捲動（研究級表，不轉 card）。
- 其餘完全遵循 Global Guideline。

---

## === OUTPUT REQUIREMENTS ===

1. **結構確認**：先列出 6 個 sections 及關鍵元件（status banner / KPI+reproduce / tear sheet 六圖 / boundary / hypothesis check / next step）。
2. **一致性落實**：複用 Panel A equity/drawdown/rolling/heatmap 元件、配色取自 Tokens、heatmap diverging / distribution sequential 僅限資料區、數值 Geist Mono、flat border #2A2A2A、focus 單色白環。
3. **程式碼**：產出完整可運行 React + Tailwind + Recharts/Plotly.js 代碼，含執行態 banner（輪詢 + log）、tear sheet 慣例順序（含 distribution/worst-N/邊界線三補件）、承諾對照、Reproduce 複製、RWD 三斷點。

---

*組裝日期: 2026-06-03 | 使用 backtest_platform Design System (Grok 單色 dark v2.0) | Run Report (M3, 複用 Panel A)*
