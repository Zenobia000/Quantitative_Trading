# Page Layer Spec — Sweep 參數掃描 (Research · Parameter Sweep)

> 來源：`03_uiux_benchmark_and_reinforcement_plan.md` §4.3 路徑 B（參數掃描）+ §6.2 CompareChart heatmap + 附錄 A §2「Optimization heatmap 穩定區語言」+ §5.1 roadmap（M3）。
> vectorbt 天生適合向量化掃描；做一張表 + heatmap 即可。提交前估算抑制暴力搜參。
> 繼承 Global v2.0（Grok 單色 dark / Geist Mono 數值 / 白環 focus / 漲跌 ↑↓ 雙編碼）。

---

## [PAGE META]

- **page_name**: Sweep 參數掃描 (Parameter Sweep)
- **route_path**: /research/sweep
- **page_type**: form + dashboard
- **primary_goal**: 讓研究者設定 range/step 參數掃描、選 vectorbt 引擎、提交前估算 N configs/est M min，掃描後以 optimization heatmap 讀「穩定區=robust vs 單點尖峰=過擬合」。
- **secondary_goal**: 每掃一次 trials_count += N、DSR 自動 deflate（護欄 1，代價入帳）；引導看相鄰穩定區而非孤立尖峰。
- **target_users**:
  - 主要：量化研究者（在參數空間找穩健高原）
  - 次要：風控（審計掃描規模對 DSR 的扣減）
- **entry_point**: Compare「改掃描參數」；Runs Table New Run（sweep 模式）；Cmd-K「新建 sweep」。
- **expected_time_on_page**: 5–20 分鐘（設 range → 估算收窄 → 提交 → 讀 heatmap → 下鑽 cell）

---

## [STRUCTURE: SECTIONS]

> 由上至下，共 5 個功能區塊。

1. **sweep_config**
   - section_type: form
   - section_purpose: 設定要掃的參數 range/step、固定其餘參數、選 vectorbt 引擎、universe/期間/成本沿用。

2. **estimate_guard**
   - section_type: estimate / guard
   - section_purpose: 提交前估算「will run N configs, est M min」+ N 過大警示，抑制暴力搜參。

3. **guardrail_bar**
   - section_type: stats / power gauge
   - section_purpose: 掃描後 trials_count += N、DSR deflate、power gauge 更新（護欄 1）。

4. **optimization_heatmap**
   - section_type: chart (CompareChart heatmap)
   - section_purpose: 2 參數熱圖，diverging 色階；顏色一致=穩定區 robust、孤立尖峰=過擬合警訊。

5. **cell_drilldown**
   - section_type: detail（選 cell 後）
   - section_purpose: 點 heatmap cell → 對應 run 摘要 + drill 到 Run Report；尖峰標警示。

---

## [SECTION COMPONENT SPEC]

### Section: sweep_config

- **layout**: 全寬卡，2 欄（左掃描參數 range，右固定參數 + 引擎/期間）。
- **elements**:
  - SweepParamRows: range/step input ×N / required / 選 1–2 參數設 start/stop/step（heatmap 軸）。
  - FixedParams: read-only pill / required / 其餘參數固定值（明示哪些不掃）。
  - EngineLock: Label / required / vectorbt（向量化掃描固定，唯讀說明）。
  - PeriodCostRef: Label / required / 沿用 New Run 的 IS 期間 + 成本 + bundle（一致性）。
- **states**:
  - default: 預填 1 參數掃描。
  - error: range 非法（start>stop / step≤0）逐欄紅框。
- **copy_constraints**: 參數 label ≤ 16 字；range 三欄數值。

### Section: estimate_guard

- **layout**: 全寬列，左估算、右提交。
- **elements**:
  - EstimateLabel: Text (Geist Mono) / required / 「will run N configs, est M min」（笛卡爾積）。
  - SizeWarning: Inline warning / required / N > 閾值 → warning 色 + 文字「config 數過大，建議收窄 range」。
  - SubmitButton: Button Primary（白 pill）/ required / N 可接受才啟用 → 提交 sweep。
- **states**:
  - default: 估算即時更新。
  - loading: Submit 轉 spinner。
  - disabled: N 超硬上限時 disabled + tooltip。
- **copy_constraints**: 估算 ≤ 32 字；按鈕 ≤ 6 字。

### Section: guardrail_bar

- **layout**: 全寬細列。
- **elements**:
  - TrialsCounter: Metric / required / trials_count += N（掃描後遞增）。
  - DsrValue: Metric / required / deflate 後 DSR（< 1.0 warning + 符號）。
  - PowerGauge: 三軸量表 / required / 紅黃綠 + 文字分級。
- **states**:
  - default: 計數 + gauge。
  - loading: skeleton（掃描進行中）。
  - error: inline error。
- **copy_constraints**: 標籤 ≤ 12 字。

### Section: optimization_heatmap

- **layout**: 全寬圖表卡；x/y=兩掃描參數、cell=目標指標。
- **elements**:
  - HeatmapGrid: Heatmap / required / **diverging 色階**（gain ↔ 中性灰 ↔ loss，沿用漲跌語義）。
  - StabilityReadout: Decision hint / required / 「顏色一致片區=robust / 孤立亮格=尖峰過擬合」。
  - ColorLegend: Legend / required / diverging 色階 + 中點。
  - CellTooltip: Tooltip / required / hover 顯示參數組 + 目標指標值。
  - SingleParamFallback: Line / optional / 僅 1 參數時改 scatter/line（非 heatmap）。
- **states**:
  - default: 完整 heatmap。
  - loading: skeleton grid（掃描中以進度替代）。
  - empty: 掃描 0 結果 → 提示。
  - error: 「heatmap 載入失敗」+ 重試。
- **copy_constraints**: 軸標 ≤ 12 字；指標值 2 位小數。

### Section: cell_drilldown

- **layout**: 選 cell 後右側 drawer / 下方展開。
- **elements**:
  - CellRunSummary: Mini KPI / required / 該參數組 run 的 Sharpe/CAGR/MDD。
  - PeakWarning: Inline warning / required / 孤立尖峰 cell → 「likely overfit, 勿選尖峰」引導相鄰穩定區。
  - OpenReportLink: Link / required / → Run Report `/research/runs/:id`。
  - PinCandidateButton: Button Ghost / optional / 標候選（需 IS gate，否則 disabled）。
- **states**:
  - default: 未選 cell 隱藏。
  - empty: cell 無對應 run → 提示。
- **copy_constraints**: 提示 ≤ 20 字。

---

## [INTERACTION & STATE FLOW]

### 主要互動流程

1. 設定 sweep range/step → estimate_guard 即時算 N configs / est min。
2. N 過大 → SizeWarning + 收窄 range；可接受 → Submit 提交 vectorbt 掃描。
3. 掃描每組參數寫一筆 run；trials_count += N、DSR deflate（護欄 1）。
4. 掃完渲染 optimization_heatmap → StabilityReadout 判讀高原 vs 尖峰。
5. 點 cell → cell_drilldown：穩健高原 drill 到 Run Report；孤立尖峰 PeakWarning。
6. 選定候選（IS gate 過）→ 釘選 → 送 Validate gate（§4.4）。

### RWD 行為差異

| 斷點 | 佈局 | 差異說明 |
|------|------|---------|
| Desktop (≥1280px) | config 2 欄；heatmap 全寬；drilldown 右 drawer | sidebar 展開 |
| Tablet (768–1279px) | config 單欄；heatmap 全寬；drilldown 下展開 | sidebar→drawer（@<1024px） |
| Mobile (≤767px) | 全部單欄；heatmap 橫向捲動保格密度 | estimate_guard 固定底部 |

### 資料更新策略

- 估算為前端本地計算；不打 API。
- 掃描為異步長任務：提交後進度 banner，逐 run 寫 DB，完成後一次撈 heatmap 資料。
- trials_count / DSR 由後端回算後更新 guardrail。

---

## [DATA & API]

- **uses_api**: true
- **主要資料表**: `run_configs`（批次寫）+ `runs`（每組一筆）。
- **endpoints**:
  - POST `/api/research/sweep` — 提交 sweep（body=掃描 range/step + 固定參數 + 期間/成本）→ 回 sweep_id + N。
  - GET `/api/research/sweep/:id/status` — 掃描進度。
  - GET `/api/research/sweep/:id/heatmap` — 掃描結果矩陣（參數×參數×目標指標）。
  - GET `/api/research/runs/trials?param_space=` — trials_count + DSR + power gauge。
- **error_cases**:
  - range 非法（422）：sweep_config 逐欄 inline error。
  - N 超硬上限：estimate_guard disabled，不可提交。
  - 掃描部分失敗：heatmap 對應 cell 標缺漏，不整體崩潰。
  - 網路錯誤：section 級 inline error + 重試。

---

## [EXCEPTION TO GLOBAL RULES]

- optimization_heatmap 用 §6.1 **Diverging 色階**（gain ↔ 中性灰 ↔ loss）— 沿用既有漲跌語義零新增語彙，屬「chrome 單色、資料區受控發散色階」例外，僅限圖表內容區。
- 其餘完全遵循 Global v2.0。

---

## [ACCEPTANCE CRITERIA]

- [ ] 5 個 section（config / estimate_guard / guardrail / heatmap / drilldown）功能正常。
- [ ] sweep_config 支援 1–2 參數 range/step；range 非法即時擋。
- [ ] estimate_guard 提交前估算「will run N configs, est M min」；N 過大警示、超硬上限 disabled。
- [ ] 掃描後 trials_count += N、DSR deflate、power gauge 更新（護欄 1，代價入帳）。
- [ ] optimization_heatmap 用 diverging 色階；StabilityReadout 判讀高原 vs 尖峰。
- [ ] cell drill：穩健高原 → Run Report；孤立尖峰 → PeakWarning 引導相鄰穩定區。
- [ ] 釘選候選需通過 IS gate，否則 disabled。
- [ ] heatmap 在 @<1024px 橫向捲動保格密度（不轉 card）。
- [ ] diverging 色階僅限資料區，不汙染 chrome 單色。
- [ ] 數值 Geist Mono tabular-nums；文字 AA、KPI 數值 AAA；focus 白環。
- [ ] dark-first、flat 1px border #2A2A2A 無陰影。
