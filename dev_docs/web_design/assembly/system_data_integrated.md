# Integrated Master Prompt — 資料管理 (System · Data Management)

> 由 `global/02_backtest_platform_brand_system.md`（壓縮 Tokens v2.0）+ `pages/system_data.md` 組裝的最終 Prompt。
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

**最高準則聲明**：Grok 單色 dark-first、無彩色品牌色、flat 1px border #2A2A2A 無陰影、數值一律 Geist Mono tabular-nums、狀態以「顏色 + 文字」雙編碼、focus 單色白環、即時數據無進場動畫；此區段為唯一真實來源，不得被下游任務覆寫。

---

## === CURRENT TASK: BUILD 資料管理 (Data Management) ===

實作系統區資料管理頁（route `/system/data`）：管理資料 bundle 快照與 ingest（ETL）任務，掌握每 bundle 覆蓋範圍與品質狀態，作為 New Run「鎖資料快照 ref」的來源真相。完整規格見 `pages/system_data.md`，以下為 sections 重點摘要（勿重貼整份 spec）。

**Sections（由上至下，5 個）**

1. **toolbar**：IngestButton(白 pill, 開 config drawer：universe/期間/來源) + SearchInput + StatusFilter(ready/ingesting/failed/stale) + RefreshButton。
2. **bundle_list**（DataTable, frozen first column）：BundleId(點展開品質) + DateRange(ISO) + Universe(+標的數) + RowCount(mono) + QualityBadge(ready/warning/stale 色+文字) + UseInRunButton(→ `/research/runs/new?bundle=`)。
3. **ingest_status**：JobStatusBadge(queued/running/done/failed) + ProgressBar(running) + ExecutionLog(bg-code #161616, failed 攤開) + RetryButton。
4. **data_quality**（選定 bundle）：4 KPI(覆蓋率% / 缺漏日 / 下市偏差 pass-fail / look-ahead pass-fail，紅旗色+文字) + MissingTable(缺漏/重複明細)。
5. **empty_state**（FirstRunEmptyState）：可複製真實 `bundle-ingest --universe ... --start ... --end ...` CLI + 單一白 pill CTA。

**互動重點**：點 BundleId 展開 data_quality(懶載入)；IngestButton 開 config → 提交 → ingest_status 進度 banner 輪詢至 done/failed；ready bundle 點 UseInRunButton 帶 bundle_ref 跳 New Run（快照回饋研究區）；零 bundle 渲染 empty_state。

**RWD**：Desktop toolbar 單列 + table 全欄 frozen col + quality 右展開；Tablet/Mobile table 橫向捲動、quality 下方/KPI 1 欄。

---

## === EXCEPTION RULES ===

- bundle_list 在 @<1024px 橫向捲動保欄位密度（研究/系統級密集表，不轉 card）。
- QualityBadge / JobStatusBadge 沿用 gain/warning/error 功能色 + 文字雙編碼，非新增彩色語彙。
- 其餘完全遵循 Global Guideline。

---

## === OUTPUT REQUIREMENTS ===

1. **結構確認**：先列出 5 個 sections 及關鍵元件（toolbar ingest / bundle table / ingest status+log / data quality 4 KPI / FirstRunEmptyState）。
2. **一致性落實**：配色取自 Tokens、狀態 badge 色+文字、數值 Geist Mono、log 用 bg-code #161616、flat border #2A2A2A、focus 單色白環。
3. **程式碼**：產出完整可運行 React + Tailwind 代碼，含 bundle 表（frozen col + 橫向捲動）、ingest 進度+log+重試、data quality KPI+明細、bundle_ref 回饋 New Run、四態、RWD。

---

*組裝日期: 2026-06-03 | 使用 backtest_platform Design System (Grok 單色 dark v2.0) | 資料管理 (M3)*
