# Integrated Master Prompt — 策略艦隊總控 (Monitor · Fleet)

> 由 `global/02_backtest_platform_brand_system.md`（壓縮 Tokens v2.0）+ `pages/monitor_fleet.md` 組裝的最終 Prompt。
> 可直接貼給 Lovable / Claude。對應 `guides/lovable_組裝.md` SOP，格式同 `assembly/monitor_a_performance_integrated.md`。
> **路徑/契約以 `25_fe_be_rest_contract.md` §6 為準**（裸根 `/monitor/*`）。**範圍註記**：本頁是 `03` §5.3 刻意延後的 champion/challenger 艦隊營運，建議補一則 ADR；live 看板資料 M4-M5（先以 deferred-stub `pending_m4`）。

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

**最高準則聲明**：Grok 單色 dark-first、無彩色品牌色、flat 1px border #2A2A2A 無陰影、數值一律 Geist Mono tabular-nums、漲跌/健康以「顏色 + ↑↓/文字」雙編碼、focus 單色白環、即時數據無進場動畫；此區段為唯一真實來源，不得被下游任務覆寫。

---

## === CURRENT TASK: BUILD 策略艦隊總控 (Monitor · Fleet) ===

實作 Monitor 區 zone home（route `/monitor`）：把所有 live/paper 策略當「一支團隊」並排監控——健康評分、live 績效、退化偵測一覽，退化者示警 + 降級/退役/換掉（晉升 challenger）workflow，並揭露組合層風險與策略間相關性。點列下鑽單策略 Panel A（`/monitor/performance`）。完整規格見 `pages/monitor_fleet.md`，以下為 sections 重點摘要（勿重貼整份 spec）。

**Sections（由上至下，6 個）**

1. **fleet_toolbar**：StageFilter（all/live/paper）+ SortSelect（健康/Sharpe/今日 P&L/退化優先）+ refresh + as-of 時間戳。
2. **portfolio_summary**（4–5 up）：組合 equity（今日變化雙編碼）+ 總曝險 + 組合 Heat（接近上限 warning）+ live 數 + 退化數（>0 標 loss）。
3. **fleet_table**（DataTable，frozen first column，**橫向捲動不轉 card**）：策略名（→ `/monitor/performance?strategy_id=`）+ StageBadge + HealthScore（紅黃綠+文字）+ live KPI（今日/MTD P&L、Sharpe、MDD、部位數、Heat 漲跌雙編碼）+ DegradeFlag + ActionMenu（下鑽/降級/退役/換掉）+ 單色 sparkline。
4. **degradation_panel**（退化專區，無退化收合「全員健康」）：退化原因（退出 cone/勝率退化/DD 超標）+ EvidenceLink→Panel A（標 live_start_date+cone）+ SwapWorkflow（降級回 paper/draft、退役凍結唯讀、晉升 challenger 替補→Promote）+ 寫 promotion_audit。
5. **correlation_matrix**（heatmap）：策略×策略報酬相關性，**Diverging 色階**；self-correlation >0.7 標警示（換湯不換藥/資金過度集中）。
6. **empty_state**：無 live/paper → 引導先完成 Validate → Promote（→ `/research/validate`）。

**互動重點**：退化優先排序；點列下鑽單策略 Panel A；退化 → swap workflow 寫 promotion_audit；高相關 >0.7 引導資金分散；退化偵測由後端推導即時標紅。

**資料/契約**：走 doc 25 裸根 `/monitor/*`（`/monitor/fleet`、`/monitor/portfolio-summary`、`/monitor/correlation`、`POST /monitor/fleet/{id}/action`）。**M4 前為 deferred-stub：回 typed empty + `meta.data_source:"pending_m4"`，渲染 pending 態，絕不假造數字。** TTL：60s；correlation 300s。

**RWD**：Desktop summary 5-up + table frozen col + correlation 全寬；Tablet summary 2-up + table 橫捲 + sidebar→drawer@<1024；Mobile 全單欄、密集表橫向捲動保密度。

---

## === EXCEPTION RULES ===

- correlation_matrix 用 §6.1 **Diverging 色階**（高相關 ↔ 中性 ↔ 負相關，沿用漲跌語義零新增語彙），僅限圖表內容區。
- fleet_table / correlation 在 @<1024px **橫向捲動不轉 card**（艦隊級密集表）。
- 其餘完全遵循 Global Guideline。

---

## === OUTPUT REQUIREMENTS ===

1. **結構確認**：先列出 6 個 sections 與關鍵元件（toolbar / portfolio summary KPI / fleet table / degradation panel + swap / correlation heatmap / empty_state）。
2. **一致性落實**：健康評分/退化/StageBadge 色+文字雙編碼、live KPI Geist Mono、correlation Diverging 僅限資料區、flat border #2A2A2A、focus 單色白環；明確標 table @<1024 橫捲不轉 card。
3. **程式碼**：產出完整可運行 React + Tailwind + Recharts/Plotly.js 代碼，含 fleet table（frozen col + 退化優先 + sparkline）、degradation swap workflow、Diverging correlation heatmap、四態、deferred-stub pending 態（不假造數字）、下鑽單策略 Panel A。

---

*組裝日期: 2026-06-05 | 使用 backtest_platform Design System (Grok 單色 dark v2.0) | 策略艦隊總控 (M4-M5)*
