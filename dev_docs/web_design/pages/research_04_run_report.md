# Page Layer Spec — Run Report (Research · Single Run Report)

> 來源：`03_uiux_benchmark_and_reinforcement_plan.md` §4.2 REPORT 子圖 + 附錄 A §1.5 Analyze tear sheet 慣例順序 + §5.1 roadmap（M3，**複用 Panel A**）。
> 把「一支已部署策略」的 equity/drawdown/turnover/cost 四象限視角，複製一份給「一個 backtest run」。
> 繼承 Global v2.0（Grok 單色 dark / Geist Mono 數值 / bg-code #161616 / 白環 focus / 漲跌 ↑↓ 雙編碼）。

---

## [PAGE META]

- **page_name**: Run Report (Single Run Report)
- **route_path**: /research/runs/:id
- **page_type**: detail (report)
- **primary_goal**: 讓研究者對單一 run 先看形狀秒判要不要深入，再下鑽歸因——頂部 KPI banner → 業界慣例 tear sheet → 事前承諾 vs 實際對照 → Reproduce 卡，並承接 queued/running/error 等執行態。
- **secondary_goal**: 提供最便宜的 reproducibility（git/bundle/engine/params/cost 快照）與下一步分流（再迭代 / 多 run 比較 / 送驗證）。
- **target_users**:
  - 主要：量化研究者（判讀單次回測結果）
  - 次要：風控（核對 run 來源與成本假設）
- **entry_point**: Runs Table 點 run_id / 列 Enter；New Run 提交後跳轉；Compare 下鑽單 run；Cmd-K type-to-run by id。
- **expected_time_on_page**: 3–10 分鐘（掃 KPI banner → tear sheet → 承諾對照 → 決定下一步）

---

## [STRUCTURE: SECTIONS]

> 由上至下，共 6 個功能區塊（含執行態 banner）。

1. **run_status_banner**
   - section_type: status / progress
   - section_purpose: 承接 queued / running / validating / error 態（execution log + 進度），done 後收起。

2. **kpi_banner + reproduce_card**
   - section_type: stats + meta card
   - section_purpose: 頂部 runtime statistics KPI（複用 Panel A 6 卡）+ Reproduce 卡（git-sha / bundle / engine / params / cost 一鍵還原）。

3. **tear_sheet**
   - section_type: charts（慣例順序）
   - section_purpose: cumulative returns 疊 benchmark → drawdown underwater + worst-N DD 表 → rolling Sharpe → monthly heatmap → **return distribution histogram**（§8 補件）。

4. **boundary_markers**
   - section_type: chart overlay
   - section_purpose: 同一 equity 曲線標 IS / OOS / paper / live 邊界（live_start_date）+ 預期 cone（pyfolio 式）。

5. **hypothesis_check**
   - section_type: comparison
   - section_purpose: 事前承諾（預期 Sharpe/勝率/MDD）vs 實際 OOS 自動紅/綠對照，移除事後編故事。

6. **next_step_bar**
   - section_type: action
   - section_purpose: 分流 再迭代 / 多 run 比較 / 送驗證；含逐筆 trade 表入口（疊 K 線核對進場）。

---

## [SECTION COMPONENT SPEC]

### Section: run_status_banner

- **layout**: 全寬 banner（非 done 時顯示）。
- **elements**:
  - StatusBadge: StatusBadge / required / queued/running/validating/error（色+文字雙編碼）。
  - ProgressBar: ProgressBar / required（running 時）/ 進度 + 已用時。
  - ExecutionLog: Code block（bg-code #161616 / Geist Mono / 可滾動）/ required（error 時攤開）/ 失敗原因定位。
  - CrossCheckNote: Inline / optional / 雙引擎對拍 zipline vs vectorbt 差異段（超容差標分歧、阻擋落地）。
  - RetryButton: Button / optional（error 時）/ 回 New Run 改 config 重試。
- **states**:
  - default(done): banner 收起。
  - loading(queued/running/validating): 顯示進度 + log。
  - error: 攤開 execution log + 重試。
- **copy_constraints**: 狀態文案 ≤ 12 字；log 等寬不換行截斷。

### Section: kpi_banner + reproduce_card

- **layout**: 左 6-up KPI（複用 Panel A），右 Reproduce 卡（Desktop 2 欄 / Mobile 堆疊）。
- **elements**:
  - KpiCards ×6: KPI Card / required / Total Return / CAGR / Sharpe / MDD / WinRate / Trades（複用 Panel A，Geist Mono，漲跌雙編碼）。
  - ReproduceCard: Meta card / required / git-sha + bundle ref + engine + 13 參數 + 成本假設，**一鍵複製 reproduce 指令**（CLI）。
  - LineageLink: Link / optional / 父/子 run（WFA 母→fold）與 baseline 衍生關係。
- **states**:
  - default: KPI + reproduce 完整。
  - loading: KPI skeleton（done 前不算）。
  - empty: 區間無交易 → KPI「—」。
  - error: 單卡 inline 失敗不阻塞。
- **copy_constraints**: KPI label ≤ 12 字；reproduce 欄位 Geist Mono 對齊。

### Section: tear_sheet

- **layout**: 全寬圖表堆疊（慣例順序，不可亂序）。
- **elements**:
  - CumulativeReturns: Line dual-series / required / strategy #F5F5F5 實線 + benchmark rgba(255,255,255,.40) 虛線（normalize 同起點）。
  - DrawdownUnderwater: Area / required / loss #F87171 填色 + 透明度；time axis 連動。
  - WorstNDdTable: DataTable / required（§8 補件）/ 最深 N 段回撤（起訖/深度/恢復天數，Geist Mono）。
  - RollingSharpe: Line + WindowToggle / required / 30/60/90D（default 60D）。
  - MonthlyHeatmap: Heatmap / required / year×month，**diverging 色階**（gain ↔ 中性灰 ↔ loss）。
  - ReturnDistribution: Histogram / required（§8 補件）/ 報酬分布 + 常態對照，**sequential 灰階**。
- **states**:
  - default: 依序渲染六圖。
  - loading: 各圖 skeleton。
  - empty: 對應圖「資料不足」（如 <1 月無 heatmap）。
  - error: 單圖 inline error + 重試，不整段崩潰。
- **copy_constraints**: 軸標籤 ≤ 8 字；報酬率 2 位小數。

### Section: boundary_markers

- **layout**: 疊加於 CumulativeReturns 之上的參考線層。
- **elements**:
  - BoundaryLines: ReferenceLine ×N / required / IS/OOS/paper/live 邊界（dashed + 文字標籤，非純色）。
  - ExpectedCone: Band / optional / live_start_date 後預期報酬 cone（退化一眼可見）。
- **states**:
  - default: 邊界線 + 標籤。
  - empty: 無 OOS/paper/live 段 → 僅顯 IS。
- **copy_constraints**: 邊界標籤 ≤ 8 字（IS/OOS/Paper/Live）。

### Section: hypothesis_check

- **layout**: 3-up 對照卡（預期 vs 實際 vs 差距）。
- **elements**:
  - ExpectedVsActual ×3: Comparison row / required / Sharpe / 勝率 / MDD：預期門檻 vs 實際 OOS，達標 gain / 未達 loss + 文字（雙編碼）。
  - PreRegNote: Caption / required / 「門檻為提交前鎖定值，本對照自動產生」。
- **states**:
  - default: 三組紅/綠對照。
  - empty: OOS 未跑 → 「待 OOS 完成後對照」。
- **copy_constraints**: 標籤 ≤ 12 字；差距含正負號。

### Section: next_step_bar

- **layout**: sticky bottom action bar。
- **elements**:
  - IterateButton: Button / required / 「再迭代」→ New Run 帶本 run 為 baseline。
  - CompareButton: Button / required / 「多 run 比較」→ Compare 帶本 run。
  - ValidateButton: Button Primary（白 pill）/ required / 「送驗證」→ Validate gate（需 done 態）。
  - TradeListLink: Link / optional / 逐筆 trade 表（疊 K 線 + hover 回跳市場狀態）。
- **states**:
  - default: 三動作可點（done 態）。
  - disabled: 非 done 態時 Validate disabled + tooltip。
- **copy_constraints**: 按鈕 ≤ 6 字。

---

## [INTERACTION & STATE FLOW]

### 主要互動流程

1. 載入 run → 若非終態：run_status_banner 顯示進度/log，輪詢至 done/error；done → 收 banner、渲染報表。
2. 雙引擎對拍超容差 → validating 轉 error，banner 標 zipline vs vectorbt 分歧段，阻擋進下游。
3. done → KPI banner + reproduce + tear sheet（慣例順序）+ boundary + hypothesis_check 渲染。
4. RollingSharpe window 切換 → 本地重算重繪。
5. next_step_bar 分流：再迭代（→New Run baseline）/ 比較（→Compare）/ 送驗證（→Validate gate）。
6. 點 ReproduceCard 複製 → 取得可貼 CLI 還原指令。

### RWD 行為差異

| 斷點 | 佈局 | 差異說明 |
|------|------|---------|
| Desktop (≥1280px) | KPI 1×6 + reproduce 右欄；tear sheet 全寬堆疊 | sidebar 展開；equity/drawdown 連動 zoom |
| Tablet (768–1279px) | KPI 2×3；reproduce 移上方 | sidebar→drawer（@<1024px） |
| Mobile (≤767px) | KPI 1×6 單欄；圖表縮高；worst-N DD 表橫向捲動 | heatmap 橫向捲動；next_step_bar 固定底部 |

### 資料更新策略

- 非終態 run 輪詢/SSE 更新 status + 進度（done/error 停止）。
- done 後報表為快照不再變動；快取 TTL 300s。
- RollingSharpe window 切換本地重算（已有日序列）。

---

## [DATA & API]

- **uses_api**: true
- **主要資料表**: `runs` + `run_configs` + `equity_snapshots`（run-scoped）+ `validation_runs`。
- **endpoints**:
  - GET `/api/research/runs/:id` — run meta + status + KPI + reproduce（git/bundle/engine/params/cost）。
  - GET `/api/research/runs/:id/equity` — equity/drawdown/monthly/distribution 日序列。
  - GET `/api/research/runs/:id/log` — execution log（loading/error 態）。
  - GET `/api/research/runs/:id/trades` — 逐筆 trade（trade list 下鑽）。
- **error_cases**:
  - run 不存在（404）：整頁「找不到此 run」+ 返回 Runs Table。
  - 執行失敗（status=error）：banner 攤 log + 重試，非整頁 error。
  - 對拍分歧（cross-check fail）：banner 標分歧段，阻擋送驗證。
  - 網路錯誤：section 級 inline error + 重試。

---

## [EXCEPTION TO GLOBAL RULES]

- tear_sheet 的 monthly heatmap 用 **diverging 色階**（gain ↔ 中性灰 ↔ loss）、return distribution 用 **sequential 灰階** — 屬 §6.1「chrome 單色、資料區受控彩色」例外，沿用既有漲跌語義零新增語彙，僅限圖表內容區。
- 其餘完全遵循 Global v2.0。

---

## [ACCEPTANCE CRITERIA]

- [ ] 6 個 section（status_banner / kpi+reproduce / tear_sheet / boundary / hypothesis_check / next_step_bar）功能正常。
- [ ] run_status_banner 正確承接 queued/running/validating/error，error 攤開 execution log 可重試。
- [ ] 雙引擎對拍超容差時標分歧段並阻擋送驗證。
- [ ] KPI banner 複用 Panel A 六卡；Reproduce 卡含 git/bundle/engine/params/cost 且可一鍵複製。
- [ ] tear_sheet 依業界慣例順序（returns→drawdown→worst-N→rolling→heatmap→distribution），含 §8 三補件（distribution / worst-N DD / 邊界線）。
- [ ] boundary_markers 在 equity 標 IS/OOS/paper/live 邊界（色+文字雙編碼）+ 預期 cone。
- [ ] hypothesis_check 自動紅/綠對照預期 vs 實際 OOS。
- [ ] heatmap diverging / distribution sequential 色階僅限資料區，不汙染 chrome 單色。
- [ ] RWD 三斷點正確（@<1024px sidebar→drawer；表格橫向捲動）。
- [ ] 數值 Geist Mono tabular-nums；文字 AA、KPI 數值 AAA；focus 白環。
- [ ] dark-first、flat 1px border #2A2A2A 無陰影。
