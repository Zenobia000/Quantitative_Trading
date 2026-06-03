# Page Layer Spec — Runs Table 研究主頁 (Research · Runs Table)

> 來源：`03_uiux_benchmark_and_reinforcement_plan.md` §4.3 多 run 比較 flowchart + §6.2 ResearchTable + 附錄 A §2「Runs Table 核心剛需」+ §5.1 roadmap（M3）。
> 研究者每日真正的工作台（single source of truth）。對應後端：`runs` 主表。
> 繼承 Global v2.0（Grok 單色 dark / Geist Mono 數值 / 白環 focus / 漲跌 ↑↓ 雙編碼）。

---

## [PAGE META]

- **page_name**: Runs Table 研究主頁 (Runs Table)
- **route_path**: /research/runs
- **page_type**: list (research data table)
- **primary_goal**: 以一列一 run 的研究級表格承載所有回測歷史（參數 × 指標 × tag × 狀態），支援排序/篩選/group-by/pin baseline/多選，作為研究迴圈的工作台與所有下游（比較/驗證/晉升）入口。
- **secondary_goal**: 常駐顯示此參數空間累計試驗次數 + 當前 DSR（防 cherry-pick 護欄 1）；以 saved views 把深度檢視進入成本降到一鍵。
- **target_users**:
  - 主要：量化研究者（管理數十至數千 run）
  - 次要：風控（審計試驗次數與晉升候選來源）
- **entry_point**: 側邊導覽「Research → Runs」；New Run 提交後返回；Cmd-K「跳 run」；策略庫「查看此版本所有 run」。
- **expected_time_on_page**: 3–10 分鐘（篩選 → pin baseline → 多選 → 跳 Compare / Run Report）

---

## [STRUCTURE: SECTIONS]

> 由上至下，共 5 個功能區塊。

1. **research_toolbar**
   - section_type: toolbar / filter
   - section_purpose: New Run CTA、saved views 切換、欄位選擇器、group-by、密度切換、篩選/搜尋。

2. **guardrail_bar**
   - section_type: stats / power gauge
   - section_purpose: 常駐顯示此參數空間累計試驗數 N、當前 DSR、過擬合 power gauge（回測次數/參數數/研究天數三軸紅黃綠）。

3. **runs_table**
   - section_type: ResearchTable（virtualized）
   - section_purpose: 一列一 run，欄=參數×指標×tag×狀態；virtualization / frozen first column / pin baseline / multi-select / inline sparkline cell。

4. **multi_select_actions**
   - section_type: action bar（多選時浮現）
   - section_purpose: 勾選 2+ run 後浮現「比較 / 加 tag / 釘選候選」動作列。

5. **empty_state**
   - section_type: empty (FirstRunEmptyState)
   - section_purpose: 零 run 時 monospace CLI 指令 + 單一 CTA，橋接既有 CLI。

---

## [SECTION COMPONENT SPEC]

### Section: research_toolbar

- **layout**: 1-row horizontal toolbar，sticky top；溢出收進 overflow menu。
- **elements**:
  - NewRunButton: Button Primary（白 pill）/ required / 跳 `/research/runs/new`。
  - SavedViewSelect: Select / required / 「策略×期間×欄位組態」具名 view，含「另存目前檢視」。
  - ColumnSelector: Popover checklist / required / 自選顯示欄位（參數/指標/tag/狀態）。
  - GroupBySelect: Select / optional / 依 strategy / version / engine / tag 分組（nested parent-child：母 run=WFA、子 run=fold）。
  - DensityToggle: SegmentedControl / optional / 緊湊 / 標準列高。
  - FilterChips: Filter / optional / status / engine / 日期 / Sharpe 範圍。
- **states**:
  - default: 套用 saved view 或預設欄位。
  - loading: toolbar 可見，table 進 skeleton。
  - empty: filter 命中 0 → table 顯示「無符合條件的 run」（與全空 empty_state 區分）。
  - error: saved view 載入失敗 → 回預設 + inline error。
- **copy_constraints**: 按鈕 ≤ 6 字；view 名稱 ≤ 20 字。

### Section: guardrail_bar

- **layout**: 全寬細列，左試驗數/DSR、右 power gauge 三軸。
- **elements**:
  - TrialsCounter: Metric (Geist Mono) / required / 「累計試驗 N 次」（隨比較/掃描遞增）。
  - DsrValue: Metric / required / 當前 DSR（< 1.0 以 warning 文字 + 符號標警示）。
  - PowerGauge: 三軸量表 / required / 回測次數 / 有效參數數 / 研究天數，紅黃綠閾值 + 文字分級（Likely/Possibly/Probably overfit）。
- **states**:
  - default: 顯示計數 + gauge。
  - loading: skeleton bar。
  - empty: 零 run → 「尚未累計試驗」。
  - error: inline error（不阻塞 table）。
- **copy_constraints**: 標籤 ≤ 12 字；分級文字 ≤ 10 字。

### Section: runs_table（ResearchTable）

- **layout**: virtualized 表格；frozen first column（run_id / 策略）；橫向捲動保欄位密度（**不 table→card**）。
- **elements**:
  - RowCheckbox: Checkbox / required / 多選；含全選/反選。
  - PinBaselineToggle: IconButton per row / required / 釘選 baseline 列（置頂 + 後續 delta 對照基準）。
  - RunIdCell: Mono link / required / 點跳 Run Report `/research/runs/:id`（穩定深連結）。
  - StatusBadgeCell: StatusBadge / required / queued/running/validating/done/error（色 + 文字雙編碼）。
  - MetricCells: Mono number / required / Sharpe / CAGR / MDD / WinRate / Trades（tabular-nums，漲跌雙編碼）。
  - ParamCells: Mono / optional / 由 ColumnSelector 控制顯示哪些參數。
  - SparklineCell: inline sparkline / optional / 該 run equity 縮圖（單色）。
  - TagCell: Tag chips / optional / 候選/baseline/is-pass 等。
  - RowKeyboardDrill: 互動 / required / 列可 focus + Enter 進 Run Report。
- **states**:
  - default: virtualized 渲染千列無卡頓；baseline 釘選置頂。
  - loading: 列 skeleton（保留欄位骨架）。
  - empty: 交由 empty_state（全空）。
  - error: 「run 清單載入失敗」+ 重試（保留 toolbar）。
- **copy_constraints**: 欄位標題 ≤ 12 字；比率指標 2 位小數、% 1 位小數。

### Section: multi_select_actions

- **layout**: 選取 ≥1 列時自底部浮現的 action bar。
- **elements**:
  - SelectedCount: Text / required / 「已選 N 個 run」。
  - CompareButton: Button / required / ≥2 選時啟用 → 跳 `/research/compare?run_ids=`。
  - TagButton: Button Ghost / optional / 批次加 tag。
  - PinCandidateButton: Button Ghost / optional / 標記候選（需 IS-pass，否則 disabled + tooltip）。
- **states**:
  - default: 未選時隱藏。
  - disabled: Compare 在 <2 選時 disabled；PinCandidate 在未過 IS gate 時 disabled。
- **copy_constraints**: 按鈕 ≤ 6 字。

### Section: empty_state（FirstRunEmptyState）

- **layout**: 置中大圓角卡 + 1px border 無陰影。
- **elements**:
  - Headline: H2 / required / 「尚無 run，跑第一次回測」。
  - CliBox: Code block（Geist Mono / bg-code #161616 / 可複製）/ required / 真實 `backtest-run` / `sweep` 指令。
  - PrimaryCta: Button Primary（白 pill）/ required / 「New Run」→ `/research/runs/new`。
- **states**:
  - default: 引導卡 + CLI + 單一 CTA（無 loading/error）。
- **copy_constraints**: Headline ≤ 18 字；CLI 為真實可執行指令。

---

## [INTERACTION & STATE FLOW]

### 主要互動流程

1. 載入 → 套用預設/last saved view → 查 runs → 有資料渲染 ResearchTable；零資料渲染 empty_state。
2. 調 ColumnSelector / GroupBy / Filter / Density → 本地重排重繪（已載入資料）或重查（跨頁）。
3. PinBaseline 某列 → 置頂並成為 delta 對照基準（指標欄顯示相對 baseline 差值）。
4. 勾選 2+ run → multi_select_actions 浮現 → CompareButton 跳 Compare 帶 run_ids。
5. 點 run_id / 列 Enter → 跳 Run Report。
6. 比較/掃描使 TrialsCounter 遞增 → guardrail_bar 的 DSR / power gauge 即時更新（護欄 1）。
7. 另存目前檢視 → 寫 saved view（策略×期間×欄位組態）。

### RWD 行為差異

| 斷點 | 佈局 | 差異說明 |
|------|------|---------|
| Desktop (≥1280px) | toolbar 單列；table 全欄 + frozen col | sidebar 展開；guardrail_bar 單列 |
| Tablet (768–1279px) | toolbar 收 overflow；table 橫向捲動保密度 | sidebar→drawer（@<1024px） |
| Mobile (≤767px) | toolbar 收合；table **維持橫向捲動不轉 card** | guardrail_bar 換行；multi-select bar 固定底部 |

> 注意：runs table **刻意不採 table→card @<1024px**（§6.2 GAP-3），改橫向捲動保欄位密度。

### 資料更新策略

- runs 清單快取 TTL 300s；page load / filter / saved view 切換 / 手動 refresh 觸發。
- queued/running run 以輪詢或 SSE 更新 StatusBadge（done/error 終態停止輪詢）。
- 排序/欄位切換優先本地（已載入頁）；跨頁分頁向後端要。

---

## [DATA & API]

- **uses_api**: true
- **主要資料表**: `runs`（single source of truth）+ `run_configs` + `validation_runs`。
- **endpoints**:
  - GET `/api/research/runs?strategy_id=&version=&status=&engine=&page=&sort=` — runs 清單（分頁 + virtualization）。
  - GET `/api/research/runs/trials?param_space=` — 該參數空間累計試驗數 + DSR + power gauge 三軸。
  - GET `/api/research/saved-views` / POST `/api/research/saved-views` — saved views 讀寫。
  - POST `/api/research/runs/tag` — 批次加 tag / 釘選候選（後端驗 IS-pass）。
- **error_cases**:
  - 網路錯誤：table 級 error + 重試，toolbar 保留。
  - API 錯誤：顯示後端訊息摘要 + 重試。
  - 無資料（全空）：渲染 empty_state（非 error）。
  - 釘選候選未過 IS gate（409）：toast 提示「需先通過 IS gate」。

---

## [EXCEPTION TO GLOBAL RULES]

- runs_table 在 @<1024px **不套用 Global 的 table→card 規則**，改「橫向捲動保欄位密度」（§6.2 GAP-3：card 化對研究級密集表是反模式）。
- SparklineCell 為單色 equity 縮圖，不引入彩色。
- 其餘完全遵循 Global v2.0。

---

## [ACCEPTANCE CRITERIA]

- [ ] 5 個 section（toolbar / guardrail_bar / runs_table / multi_select_actions / empty_state）功能正常。
- [ ] ResearchTable 支援 virtualization（千列不卡）/ frozen first column / pin baseline / multi-select / column selector / group-by / density toggle。
- [ ] guardrail_bar 常駐顯示累計試驗數 + DSR + power gauge 三軸（紅黃綠 + 文字分級）。
- [ ] 比較/掃描使試驗數遞增、DSR/power gauge 即時更新（防 cherry-pick 護欄 1）。
- [ ] runs_table 在 @<1024px 維持橫向捲動，**不轉 card**。
- [ ] 多選 ≥2 啟用 Compare；釘選候選未過 IS gate 時 disabled。
- [ ] 零 run 渲染 empty_state（可複製真實 CLI + 單一 CTA）。
- [ ] StatusBadge 色+文字雙編碼；queued/running 輪詢至終態。
- [ ] saved views 可存可載（策略×期間×欄位組態）。
- [ ] 列可 keyboard focus + Enter drill-down；穩定深連結到 Run Report。
- [ ] 數值 Geist Mono tabular-nums；文字 AA、KPI 數值 AAA；focus 白環。
- [ ] dark-first、flat 1px border #2A2A2A 無陰影。
