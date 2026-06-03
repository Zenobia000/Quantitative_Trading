# Page Layer Spec — 策略庫 (Research · Strategy Library)

> 來源：`03_uiux_benchmark_and_reinforcement_plan.md` §4.7 sitemap（`/research/strategies`）+ §5.1 roadmap（M3）。
> 研究工作區頂層第一頁。繼承 Global Design System v2.0（**Grok 單色 dark**：bg-base #0F0F0F / surface #1A1A1A / border #2A2A2A / 白環 focus / Geist Mono 數值 / 漲跌 ↑↓ 雙編碼）。
> 填完後貼入 `assembly/PIPELINE_ORCHESTRATOR.md` 的 PAGE SPECIFICATION 區段。

---

## [PAGE META]

- **page_name**: 策略庫 (Strategy Library)
- **route_path**: /research/strategies
- **page_type**: list
- **primary_goal**: 讓研究者總覽所有策略及其版本沿革（v2 → v3 …），每個策略一眼看到最新 run 績效、validation_status 與晉升階段，作為研究迴圈的進入大廳。
- **secondary_goal**: 以舊版策略為 baseline 衍生新變體（Retired → Draft 回流），並導向 New Run 設定頁開始新一輪迭代。
- **target_users**:
  - 主要：量化策略研究者（單人，管理多策略候選池）
  - 次要：風控（審視哪些策略已晉升、哪些卡在 gate）
- **entry_point**: 側邊導覽「Research → 策略庫」；或 Cmd-K「跳策略」；或 Promote 頁完成後返回。
- **expected_time_on_page**: 1–3 分鐘（掃版本狀態 → 選定策略 → 跳 New Run / Runs Table）

---

## [STRUCTURE: SECTIONS]

> 由上至下，共 4 個功能區塊。

1. **toolbar**
   - section_type: toolbar / filter
   - section_purpose: 新建策略 CTA、關鍵字搜尋、依 validation_status / 晉升階段篩選。

2. **strategy_list**
   - section_type: list (card grid 或 dense table)
   - section_purpose: 每列/卡一個策略，顯示名稱、最新版本、單一論點摘要、最佳 run KPI、validation_status badge、晉升階段。

3. **version_timeline**
   - section_type: detail / timeline（選定策略後展開）
   - section_purpose: 該策略 v2 → v3 版本沿革，逐版顯示假設 diff、IS/OOS gate 結果、試驗次數。

4. **empty_state**
   - section_type: empty (FirstRunEmptyState 變體)
   - section_purpose: 零策略時提供可複製 CLI 指令 + 單一 CTA，消除 first-run 死胡同。

---

## [SECTION COMPONENT SPEC]

### Section: toolbar

- **layout**: 1-row horizontal toolbar，sticky top（左 search + filter，右 new CTA）。
- **elements**:
  - NewStrategyButton: Button Primary（白底 pill）/ required / 跳 `/research/runs/new?new_strategy=1`。
  - SearchInput: Input / optional / 依 strategy_id / name 即時過濾。
  - StatusFilter: SegmentedControl / optional / 全部 / Draft / Validated / Paper / Live / Retired（多選 chip）。
  - SortSelect: Select / optional / 依最新 run 時間 / 最佳 Sharpe / 晉升階段排序。
- **states**:
  - default: 顯示全部策略；filter 全選。
  - loading: toolbar 維持可見，下游 list 進 skeleton。
  - empty: filter 命中 0 → list 顯示「無符合條件的策略」（非全平台空，與 empty_state 區分）。
  - error: 策略清單載入失敗 → inline error + 重試。
- **copy_constraints**: 按鈕文案 ≤ 6 字（「新建策略」）；filter chip ≤ 6 字。

### Section: strategy_list

- **layout**: card grid（Desktop 3 欄 / Tablet 2 欄 / Mobile 1 欄）；卡片 flat 1px border #2A2A2A 無陰影。
- **elements**:
  - StrategyCard.Name: H3 + strategy_id（Geist Mono caption）/ required。
  - StrategyCard.LatestVersion: Badge / required / 「v3」+ 建立日期。
  - StrategyCard.Hypothesis: Text (clamp 2 行) / required / 單一論點摘要。
  - StrategyCard.BestKpi: Mini KPI row / required / 最佳 run 的 Sharpe / CAGR / MDD（Geist Mono，漲跌雙編碼）。
  - StrategyCard.StatusBadge: StatusBadge / required / validation_status（Draft / IS-pass / OOS-pass / approved / live）+ 文字（單色 + 符號，非純色）。
  - StrategyCard.StageBadge: Badge / required / 晉升階段 Draft→…→Retired。
  - DeriveButton: Button Ghost / optional / Retired 策略顯示「衍生新變體」→ New Run 帶 baseline。
- **states**:
  - default: 卡片完整資訊；hover 整卡 focus 白環。
  - loading: skeleton card grid。
  - empty: 交由 empty_state section（全平台零策略）。
  - error: 單卡「載入失敗」inline，不阻塞其他卡。
- **copy_constraints**: 名稱 ≤ 24 字；論點摘要 ≤ 2 行；badge 文字 ≤ 8 字。

### Section: version_timeline

- **layout**: 選定策略後右側 drawer 或下方展開區；垂直 timeline。
- **elements**:
  - VersionNode: Timeline item / required / 版本號 + 日期 + 假設一句 + gate 結果（IS pass/fail、OOS pass/fail）。
  - HypothesisDiff: Diff view (Geist Mono, bg-code #161616) / optional / 相鄰版本假設與關鍵參數差異。
  - TrialsBadge: Badge / required / 該版本累計試驗次數 + 當前 DSR（餵防過擬合語意）。
  - OpenRunsLink: Link / required / 「查看此版本所有 run」→ `/research/runs?strategy_id=&version=`。
- **states**:
  - default: 由新到舊列出版本節點。
  - loading: timeline skeleton。
  - empty: 「此策略尚無版本紀錄」。
  - error: inline error + 重試。
- **copy_constraints**: 假設一句 ≤ 40 字；diff 每列 ≤ 60 字。

### Section: empty_state（FirstRunEmptyState 變體）

- **layout**: 置中大圓角卡（radius 12px）+ 1px border 無陰影。
- **elements**:
  - Headline: H2 / required / 「尚無策略，從第一次回測開始」。
  - CliBox: Code block（Geist Mono / bg-code #161616 / 可複製）/ required / 真實 `backtest-run --stocks ... --start ... --end ... --bundle ...` 指令。
  - PrimaryCta: Button Primary（白 pill）/ required / 「建立第一個策略」→ `/research/runs/new`。
  - ThreePath: Link row / optional / 跑範例 / 看文件 / 貼 CLI 三路徑（繼承 grok P-G3）。
- **states**:
  - default: 顯示引導卡 + CLI + 單一 CTA。
  - 無 loading / error（純靜態引導）。
- **copy_constraints**: Headline ≤ 18 字；CLI 為真實可執行指令，不可佔位假字串。

---

## [INTERACTION & STATE FLOW]

### 主要互動流程

1. 頁面載入 → 查策略清單 → 有資料渲染 strategy_list；零資料渲染 empty_state。
2. 點 StrategyCard → 展開 version_timeline（同頁 drawer），不跳頁。
3. 點 NewStrategyButton / PrimaryCta → 跳 `/research/runs/new`。
4. Retired 策略點 DeriveButton → 跳 New Run，預填 baseline 參數（version_timeline 最後通過版本）。
5. 點 OpenRunsLink → 跳 Runs Table 並帶 `strategy_id` + `version` filter。

### RWD 行為差異

| 斷點 | 佈局 | 差異說明 |
|------|------|---------|
| Desktop (≥1280px) | toolbar 單列；card 3 欄；timeline 右側 drawer | sidebar 展開 |
| Tablet (768–1279px) | card 2 欄；timeline 改下方展開 | sidebar 收合為 drawer（@<1024px） |
| Mobile (≤767px) | toolbar 換行；card 1 欄堆疊；timeline 全寬 | DeriveButton 收進卡片 overflow |

### 資料更新策略

- 策略清單為低頻變動 → 快取 TTL 300s；page load / filter change / 手動 refresh 觸發。
- version_timeline 點選時懶載入（lazy fetch），不隨清單一次撈。

---

## [DATA & API]

- **uses_api**: true
- **主要資料表**: `runs`（主表，single source of truth）+ `run_configs` + `promotion_audit`。
- **endpoints**:
  - GET `/api/research/strategies` — 策略清單（strategy_id / name / 最新版本 / 最佳 run KPI / validation_status / stage）。
  - GET `/api/research/strategies/{id}/versions` — 版本沿革 + 假設 diff + trials_count + DSR。
  - POST `/api/research/strategies` — 新建策略（亦可由 New Run 隱式建立）。
- **error_cases**:
  - 網路錯誤：section 級 inline error + 重試，不整頁崩潰。
  - API 錯誤：顯示後端訊息摘要 + 重試。
  - 無資料（全平台零策略）：渲染 empty_state（非 error）。
  - 權限不足：導向登入。

---

## [EXCEPTION TO GLOBAL RULES]

無特殊例外，完全遵循 Global v2.0（Grok 單色 dark、flat 1px border、Geist Mono 數值、漲跌雙編碼、focus 白環）。
（badge 狀態色沿用 gain/loss/warning/error 功能色，皆配文字符號雙編碼，非新增彩色語彙。）

---

## [ACCEPTANCE CRITERIA]

- [ ] 4 個 section（toolbar / strategy_list / version_timeline / empty_state）功能正常。
- [ ] strategy_list 四態完備：default / loading(skeleton) / empty(filter 命中 0) / error。
- [ ] 全平台零策略時正確渲染 empty_state（含可複製真實 CLI + 單一 CTA），消除 first-run 死胡同。
- [ ] StatusBadge / StageBadge 以「色 + 文字/符號」雙編碼，不只靠顏色。
- [ ] version_timeline 顯示版本假設 diff + trials_count + DSR。
- [ ] Retired 策略可「衍生新變體」回流 New Run 帶 baseline。
- [ ] RWD 三斷點正確（@<1024px sidebar→drawer；card grid 降欄）。
- [ ] 數值 Geist Mono tabular-nums；文字 AA、KPI 數值 AAA；focus 白環 rgba(245,245,245,.7)。
- [ ] dark-first、flat 1px border #2A2A2A 無陰影、無多餘進場動畫。
