# Integrated Master Prompt — Compare 多 run 比較 (Research · Compare)

> 由 `global/02_backtest_platform_brand_system.md`（壓縮 Tokens v2.0）+ `pages/research_05_compare.md` 組裝的最終 Prompt。
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

## === CURRENT TASK: BUILD Compare 多 run 比較 (Compare) ===

實作多 run 比較工作台（route `/research/compare`）：equity 疊圖 + 指標表 baseline delta + parallel coordinates brushing，在參數空間找穩健高原而非單點尖峰，含防 cherry-pick 護欄。完整規格見 `pages/research_05_compare.md`，以下為 sections 重點摘要（勿重貼整份 spec）。

**Sections（由上至下，5 個）**

1. **compare_toolbar**：RunChips(可移除, baseline pin 高亮) + SetBaselineSelect + AddRunButton + GoSweepButton(→ `/research/sweep`)。
2. **guardrail_bar**：TrialsCounter(比較動作遞增) + DsrValue(<1.0 warning+符號) + PowerGauge(三軸紅黃綠)。
3. **equity_overlay**：多 run equity 疊圖，**預設白→灰明度階 + 線型(實/虛/點)** 區分、baseline 最亮實線；run 數超單色可區分上限才啟用 §6.1 Categorical 8-色盤。
4. **metric_diff_table**：DataTable 列=run 欄=指標 + 相對 baseline DeltaCells(漲跌 ↑↓ 雙編碼)，baseline 置頂；點列 → Run Report。
5. **parallel_coordinates**（CompareChart）：軸=參數×指標、每線一 run、BrushControl 框選；HighlandReadout 判讀穩健一片 vs 單點尖峰；命中孤立尖峰 PeakWarning「likely overfit, 勿選尖峰」引導相鄰穩定區。

**互動重點**：SetBaseline 重算 delta 與高亮；brush 命中即時 highland readout；比較動作使 TrialsCounter 遞增、guardrail DSR/gauge 更新（護欄 1）；選穩健高原 drill → Run Report → 送 Validate gate。

**RWD**：Desktop overlay + table 並排或上下、parcoords 全寬；Tablet/Mobile 全寬堆疊、table/parcoords 橫向捲動。

---

## === EXCEPTION RULES ===

- **equity_overlay 在 run 數超過單色明度可區分上限時啟用 §6.1 Categorical 8-色盤**（低飽和、dark 底 WCAG 達標）；屬「chrome 單色、資料區受控離散色盤」例外，僅限圖表內容區。補強動機：Panel C 5 軌已證單色在 ≥5 類別破功（§10 GAP-1）。
- metric/parcoords 表在 @<1024px 橫向捲動（研究級表，不轉 card）。
- 其餘完全遵循 Global Guideline。

---

## === OUTPUT REQUIREMENTS ===

1. **結構確認**：先列出 5 個 sections 及關鍵元件（toolbar run chips / guardrail / equity overlay / metric delta table / parcoords brushing）。
2. **一致性落實**：equity 預設單色明度階 + 線型、超限才用 Categorical 受控色盤、baseline delta 漲跌雙編碼、數值 Geist Mono、flat border #2A2A2A、focus 單色白環。
3. **程式碼**：產出完整可運行 React + Tailwind + Recharts/Plotly.js 代碼，含多 run equity overlay、baseline delta 表、parallel coordinates + brushing + highland/peak 判讀、TrialsCounter/DSR 更新、四態、橫向捲動 RWD。

---

*組裝日期: 2026-06-03 | 使用 backtest_platform Design System (Grok 單色 dark v2.0) | Compare 多 run 比較 (M3)*
