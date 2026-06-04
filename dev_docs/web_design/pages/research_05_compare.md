# Page Layer Spec — Compare 多 run 比較 (Research · Compare)

> 來源：`03_uiux_benchmark_and_reinforcement_plan.md` §4.3 路徑 A（多選比較）+ §6.2 CompareChart + 附錄 A §1.6 Compare/Optimize + §5.1 roadmap（M3）。
> 把 ADR-017 M0 進場重設從「CLI 手敲 + 散落 ADR + 人腦記憶」升格為有護欄的視覺工作台。
> 繼承 Global v2.0（Grok 單色 dark / Geist Mono 數值 / 白環 focus / 漲跌 ↑↓ 雙編碼）。

---

## [PAGE META]

- **page_name**: Compare 多 run 比較 (Compare)
- **route_path**: /research/compare
- **page_type**: dashboard (comparison workspace)
- **primary_goal**: 讓研究者把多個 run 並排比較——equity 疊圖（明度+線型）、指標表 baseline delta、parallel coordinates brushing——在參數空間找穩健高原而非單點尖峰。
- **secondary_goal**: 防 cherry-pick：試驗次數→DSR deflate 常駐、高原 vs 尖峰視覺語言、brush 框選即時教育「選寬廣高原不選尖峰」。
- **target_users**:
  - 主要：量化研究者（多 run 迭代比較）
  - 次要：風控（審計比較次數對 DSR 的扣減）
- **entry_point**: Runs Table 多選 ≥2 run → CompareButton；Run Report「多 run 比較」；Cmd-K「開比較」。
- **expected_time_on_page**: 5–15 分鐘（疊圖 → 讀 delta → brush parcoords → 選候選）

---

## [STRUCTURE: SECTIONS]

> 由上至下，共 5 個功能區塊。

1. **compare_toolbar**
   - section_type: toolbar
   - section_purpose: 顯示參與比較的 run chips、切換 baseline、加減 run、跳掃描（Sweep）。

2. **guardrail_bar**
   - section_type: stats / power gauge
   - section_purpose: 常駐累計試驗數 + DSR + power gauge（每多比一次代價入帳，護欄 1）。

3. **equity_overlay**
   - section_type: chart (multi-series overlay)
   - section_purpose: 多 run equity 疊圖，**單色明度階 + 線型**區分；baseline 高亮。

4. **metric_diff_table**
   - section_type: table (baseline delta)
   - section_purpose: 各 run 指標表 + 相對 baseline 的 delta（漲跌 ↑↓ 雙編碼）。

5. **parallel_coordinates**
   - section_type: chart (CompareChart parcoords)
   - section_purpose: 軸=參數×指標、每線一 run，brushing 框選，判讀穩健一片 vs 單點尖峰。

---

## [SECTION COMPONENT SPEC]

### Section: compare_toolbar

- **layout**: 1-row toolbar，run chips 可橫向捲動。
- **elements**:
  - RunChips: Chip row / required / 參與比較的 run（可移除）；baseline chip 高亮 pin icon。
  - SetBaselineSelect: Select / required / 指定哪個 run 為 baseline（delta 基準）。
  - AddRunButton: Button Ghost / optional / 回 Runs Table 加選；**帶當前 run_ids 回填** → `/research/runs?compare=<run_ids>`（Runs Table 預選現有比較集，續加不重選，避免 compare 脈絡丟失）。
  - GoSweepButton: Button Ghost / optional / 「改掃描參數」→ `/research/sweep?from=<baseline_run_id>`（帶 baseline run 的參數空間進 Sweep，保留比較脈絡）。
- **states**:
  - default: 顯示 ≥2 run chips + baseline。
  - empty: <2 run → 「請至少選 2 個 run 比較」+ 回 Runs Table CTA。
  - error: run 載入失敗 → inline error + 重試。
- **copy_constraints**: 按鈕 ≤ 6 字；chip 顯 run_id 尾碼。

### Section: guardrail_bar

- **layout**: 全寬細列（與 Runs Table guardrail 一致）。
- **elements**:
  - TrialsCounter: Metric (Geist Mono) / required / 累計試驗 N（比較動作遞增）。
  - DsrValue: Metric / required / 當前 DSR（< 1.0 warning + 符號）。
  - PowerGauge: 三軸量表 / required / 紅黃綠 + 文字分級。
- **states**:
  - default: 計數 + gauge。
  - loading: skeleton。
  - error: inline error（不阻塞圖表）。
- **copy_constraints**: 標籤 ≤ 12 字。

### Section: equity_overlay

- **layout**: 全寬圖表卡；高度 320–400px；legend 右上（runs + baseline）。
- **elements**:
  - EquityLines: Multi-line / required / 每 run 一線，**白→灰明度階 + 線型（實/虛/點）**區分（單色優先）；baseline 最亮實線。
  - CategoricalFallback: Note / optional / run 數 > 可明度區分上限時，啟用 §6.1 **Categorical 8-色盤**（低飽和、dark 底 WCAG 達標）。
  - ChartTooltip: Tooltip / required / hover 顯示日期 + 各 run 值 + 相對 baseline delta。
  - ZoomPan: 互動 / required / 框選 zoom / 拖曳 pan / 雙擊 reset。
- **states**:
  - default: 疊圖 + legend；baseline 高亮。
  - loading: skeleton。
  - empty: 區間無 equity → 置中提示。
  - error: 「疊圖載入失敗」+ 重試。
- **copy_constraints**: legend 標籤 ≤ 12 字。

### Section: metric_diff_table

- **layout**: DataTable，列=run、欄=指標；baseline 列置頂。
- **elements**:
  - MetricColumns: Mono number / required / Sharpe/CAGR/MDD/WinRate/Trades（tabular-nums）。
  - DeltaCells: Mono ±value / required / 相對 baseline 差值，漲跌 ↑↓ + 色雙編碼。
  - BestHighlight: Cell style / optional / 每欄最佳值輕標（非鮮豔色，邊框/明度）。
  - DrillRow: 互動 / required / 點 run 列 → Run Report。
- **states**:
  - default: delta 表 + baseline 置頂。
  - loading: 列 skeleton。
  - empty: 無共同指標 → 提示。
  - error: inline error + 重試。
- **copy_constraints**: 欄標 ≤ 12 字；delta 含正負號。

### Section: parallel_coordinates（CompareChart）

- **layout**: 全寬圖表卡；軸=參數×指標、每線一 run。
- **elements**:
  - ParcoordsAxes: Axes / required / 可選參與軸（參數 + 指標）。
  - RunPolylines: Polyline / required / 每 run 一線（明度階 / categorical token）。
  - BrushControl: 互動 / required / 各軸框選，命中 run 高亮、其餘淡化。
  - HighlandReadout: Decision hint / required / brush 命中「穩健一片」vs「單點尖峰」即時提示。
  - PeakWarning: Inline warning / required / 命中孤立尖峰 → 「likely overfit, 勿選尖峰」引導看相鄰穩定區。
- **states**:
  - default: 全 run polyline。
  - brushing: 命中高亮 + highland readout。
  - empty: 參數維度不足 → 「需 ≥2 參數軸」。
  - error: inline error + 重試。
- **copy_constraints**: 軸標 ≤ 12 字；提示 ≤ 20 字。

---

## [INTERACTION & STATE FLOW]

### 主要互動流程

1. 自 Runs Table 帶 run_ids 載入 → equity_overlay / metric_diff_table / parcoords 並行渲染。
2. SetBaseline → metric delta 與 equity 高亮以新 baseline 重算。
3. brush parcoords 任一軸 → 命中 run 高亮、highland readout 判讀；命中尖峰 → PeakWarning。
4. 比較動作（換 baseline / 重組 run）使 TrialsCounter 遞增 → guardrail DSR/gauge 更新（護欄 1）。
5. 選定穩健高原 run → 點列 drill 到 Run Report → 送 Validate gate（IS gate 守門接續 §4.4）。

### RWD 行為差異

| 斷點 | 佈局 | 差異說明 |
|------|------|---------|
| Desktop (≥1280px) | overlay + table 並排或上下；parcoords 全寬 | sidebar 展開 |
| Tablet (768–1279px) | 全寬堆疊；table 橫向捲動 | sidebar→drawer（@<1024px） |
| Mobile (≤767px) | 單欄堆疊；parcoords 橫向捲動 | run chips 橫捲；圖例移圖下方 |

### 資料更新策略

- 比較資料依 run_ids 一次撈，快取 TTL 300s。
- baseline 切換 / brush 為本地重算，不重打 API。
- 試驗次數遞增寫回後端（POST），DSR 由後端回算後更新 guardrail。

---

## [DATA & API]

- **uses_api**: true
- **主要資料表**: `runs` + `equity_snapshots`（run-scoped）。
- **endpoints**:
  - GET `/api/research/compare?run_ids=a,b,c` — 各 run KPI + equity 序列 + 參數，供疊圖/表/parcoords。
  - GET `/api/research/runs/trials?param_space=` — 累計試驗數 + DSR + power gauge。
  - POST `/api/research/trials/increment` — 比較動作計次（餵 DSR deflate）。
- **error_cases**:
  - run_ids < 2：compare_toolbar empty 態 + 回 Runs Table。
  - 部分 run 載入失敗：該 run chip 標 error，其餘照常比較。
  - 網路錯誤：section 級 inline error + 重試。
  - 參數維度不足 parcoords：該 section empty。

---

## [EXCEPTION TO GLOBAL RULES]

- equity_overlay 在 run 數超過單色明度可區分上限時，啟用 §6.1 **Categorical 8-色盤**（低飽和、dark 底 WCAG 達標）；metric/parcoords 沿用既有漲跌語義。屬「chrome 單色、資料區受控離散色盤」例外，僅限圖表內容區。
- 其餘完全遵循 Global v2.0。
- 補強動機：Panel C 5 軌訊號已證單色在 ≥5 類別破功（§10 GAP-1），多 run 比較需受控色盤。

---

## [ACCEPTANCE CRITERIA]

- [ ] 5 個 section（toolbar / guardrail / equity_overlay / metric_diff_table / parcoords）功能正常。
- [ ] equity_overlay 預設單色明度階 + 線型區分；run 數超限才啟用 Categorical 8-色盤（受控例外）。
- [ ] metric_diff_table 以 baseline delta + 漲跌 ↑↓ 雙編碼呈現。
- [ ] parcoords brushing 命中即時判讀穩健高原 vs 單點尖峰；尖峰觸發 PeakWarning。
- [ ] 比較動作使試驗數遞增、DSR/power gauge 即時更新（防 cherry-pick 護欄 1）。
- [ ] <2 run 正確顯示 toolbar empty 態並導回 Runs Table。
- [ ] 選定候選可 drill 到 Run Report 並接續送 Validate gate。
- [ ] RWD 三斷點正確（@<1024px sidebar→drawer；圖表橫向捲動）。
- [ ] 數值 Geist Mono tabular-nums；文字 AA、KPI 數值 AAA；focus 白環。
- [ ] dark-first、flat 1px border #2A2A2A 無陰影；Categorical 色盤達 WCAG。
