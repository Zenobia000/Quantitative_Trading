# Integrated Master Prompt — Runs Table 研究主頁 (Research · Runs Table)

> 由 `global/02_backtest_platform_brand_system.md`（壓縮 Tokens v2.0）+ `pages/research_03_runs_table.md` 組裝的最終 Prompt。
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

## === CURRENT TASK: BUILD Runs Table 研究主頁 (Runs Table) ===

實作研究者每日工作台（route `/research/runs`）：一列一 run 的研究級表格承載所有回測歷史，支援排序/篩選/group-by/pin baseline/多選，作為下游（比較/驗證/晉升）入口。對應後端 `runs` 主表（single source of truth）。完整規格見 `pages/research_03_runs_table.md`，以下為 sections 重點摘要（勿重貼整份 spec）。

**Sections（由上至下，5 個）**

1. **research_toolbar**：NewRunButton(白 pill) + SavedViewSelect(策略×期間×欄位組態) + ColumnSelector + GroupBySelect(strategy/version/engine/tag, nested 母 run=WFA 子 run=fold) + DensityToggle + FilterChips。
2. **guardrail_bar**：TrialsCounter(累計試驗 N) + DsrValue(<1.0 warning+符號) + PowerGauge(回測次數/參數數/研究天數 三軸紅黃綠 + 文字分級)。
3. **runs_table**（ResearchTable）：virtualization(千列) + frozen first column + PinBaseline + RowCheckbox 多選 + StatusBadge(queued/running/done/error 色+文字) + 指標 cells(漲跌雙編碼) + 由 ColumnSelector 控制的 param cells + inline sparkline(單色) + 列可 focus + Enter drill。
4. **multi_select_actions**（選 ≥1 浮現）：CompareButton(≥2 啟用 → `/research/compare?run_ids=`) + TagButton + PinCandidateButton(需 IS-pass，否則 disabled)。
5. **empty_state**（FirstRunEmptyState）：可複製 `backtest-run`/`sweep` CLI + 單一白 pill CTA。

**互動重點**：套 saved view/預設欄位；pin baseline 列置頂 + 指標欄顯相對 delta；多選 ≥2 啟用 Compare；比較/掃描使 TrialsCounter 遞增、guardrail DSR/gauge 即時更新（防 cherry-pick 護欄 1）；queued/running 輪詢至終態。

**RWD**：Desktop toolbar 單列 + table 全欄 frozen col；Tablet/Mobile **table 維持橫向捲動保欄位密度，不轉 card**。

---

## === EXCEPTION RULES ===

- **runs_table 在 @<1024px 不套用 Global 的 table→card 規則**，改「橫向捲動保欄位密度」（§6.2 GAP-3：card 化對研究級密集表是反模式）。
- SparklineCell 為單色 equity 縮圖，不引入彩色。
- 其餘完全遵循 Global Guideline。

---

## === OUTPUT REQUIREMENTS ===

1. **結構確認**：先列出 5 個 sections 及關鍵元件（toolbar / guardrail power gauge / ResearchTable / multi-select bar / FirstRunEmptyState）。
2. **一致性落實**：配色僅取自 Tokens（Grok 單色）、數值 Geist Mono、StatusBadge 色+文字、power gauge 紅黃綠+文字分級、flat border #2A2A2A、focus 單色白環；明確標註 table 在 @<1024px 橫向捲動不轉 card。
3. **程式碼**：產出完整可運行 React + Tailwind 代碼，含 ResearchTable（virtualization / frozen col / pin baseline / multi-select / column selector / group-by / density）、guardrail bar、四態、橫向捲動 RWD、saved views 讀寫、輪詢更新。

---

*組裝日期: 2026-06-03 | 使用 backtest_platform Design System (Grok 單色 dark v2.0) | Runs Table 研究主頁 (M3)*
