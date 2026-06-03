# Integrated Master Prompt — Sweep 參數掃描 (Research · Parameter Sweep)

> 由 `global/02_backtest_platform_brand_system.md`（壓縮 Tokens v2.0）+ `pages/research_06_sweep.md` 組裝的最終 Prompt。
> 可直接貼給 Lovable / Claude。對應 `guides/lovable_組裝.md` SOP，格式同 `assembly/monitor_a_performance_integrated.md`。

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

## === CURRENT TASK: BUILD Sweep 參數掃描 (Parameter Sweep) ===

實作參數掃描頁（route `/research/sweep`）：設定 range/step、選 vectorbt、提交前估算 N configs/est M min，掃描後以 optimization heatmap 讀「穩定區 robust vs 單點尖峰過擬合」。完整規格見 `pages/research_06_sweep.md`，以下為 sections 重點摘要（勿重貼整份 spec）。

**Sections（由上至下，5 個）**

1. **sweep_config**：SweepParamRows(1–2 參數 start/stop/step) + FixedParams(唯讀其餘固定) + EngineLock(vectorbt 唯讀) + PeriodCostRef(沿用 New Run IS 期間+成本+bundle)。
2. **estimate_guard**：EstimateLabel「will run N configs, est M min」+ SizeWarning(N 過大 warning「收窄 range」) + SubmitButton(白 pill, 超硬上限 disabled)。
3. **guardrail_bar**：TrialsCounter(掃描後 +=N) + DsrValue(deflate, <1.0 warning) + PowerGauge(三軸)。
4. **optimization_heatmap**（CompareChart）：x/y=兩掃描參數、cell=目標指標、**Diverging 色階**(gain↔灰↔loss)；StabilityReadout「顏色一致片區=robust / 孤立亮格=尖峰過擬合」；僅 1 參數時退 scatter/line。
5. **cell_drilldown**（選 cell）：CellRunSummary(Sharpe/CAGR/MDD) + PeakWarning(孤立尖峰引導相鄰穩定區) + OpenReportLink(→ Run Report) + PinCandidateButton(需 IS gate)。

**互動重點**：估算即時算 N（笛卡爾積）；N 過大警示/超上限 disabled；掃描每組寫一筆 run、trials_count+=N、DSR deflate（護欄 1）；掃完渲染 heatmap → StabilityReadout 判讀高原 vs 尖峰；穩健高原 drill → Run Report → 送 Validate gate。

**RWD**：Desktop config 2 欄 + heatmap 全寬 + drilldown 右 drawer；Tablet/Mobile 單欄、heatmap 橫向捲動保格密度。

---

## === EXCEPTION RULES ===

- **optimization_heatmap 用 §6.1 Diverging 色階**（gain ↔ 中性灰 ↔ loss）— 沿用既有漲跌語義零新增語彙，屬「chrome 單色、資料區受控發散色階」例外，僅限圖表內容區。
- heatmap 在 @<1024px 橫向捲動保格密度（不轉 card）。
- 其餘完全遵循 Global Guideline。

---

## === OUTPUT REQUIREMENTS ===

1. **結構確認**：先列出 5 個 sections 及關鍵元件（sweep config range/step / estimate guard / guardrail / diverging heatmap / cell drilldown）。
2. **一致性落實**：heatmap diverging 僅限資料區、估算/數值 Geist Mono、N 過大警示、trials deflate、flat border #2A2A2A、focus 單色白環。
3. **程式碼**：產出完整可運行 React + Tailwind + Recharts/Plotly.js 代碼，含 range/step 設定+驗證、提交前估算、異步掃描進度、diverging heatmap + 高原/尖峰判讀、cell drilldown、trials/DSR 更新、橫向捲動 RWD。

---

*組裝日期: 2026-06-03 | 使用 backtest_platform Design System (Grok 單色 dark v2.0) | Sweep 參數掃描 (M3)*
