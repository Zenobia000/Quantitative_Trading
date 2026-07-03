# ADR-041: 分支實驗血統 — 策略迭代作為 parent→child 顯式分支，禁止靜默覆蓋

> **狀態：** 已接受 | **日期：** 2026-07-03 | **決策者：** Self
> **建立於（builds on）：** [ADR-039](./ADR-039-evaluation-profile-orchestration-layer.md)（evaluation orchestrator + 候選池 — 本 ADR 以其 `EvaluationResult` 為 parent、`evaluate()` 為分支再跑引擎）、Goal 8 what-if 模擬（`research/simulation.py` 的 `branch_suggestion` — 本 ADR 接上其「fork」出口）
> **相關：** `research/run_config.py`（`run_id` = config hash — 分支靠改 config 取得 distinct id）、`strategies/protocol.py`（`config_schema` — delta key 合法性真相源）
> **產品依據：** `rebuild_goal_spec_ai_requirements_2026-07-03.md` Goal 9（每分支連 parent run/strategy、compare 顯示 delta 指標 + 決策、分支不可靜默覆蓋 parent）；`dev_docs/contracts/README.md` §14

---

## 1. 背景與問題

研究者需要迭代策略（「lookback 改 90 會怎樣？」）。若直接改 config 原地重跑，parent 的判決就被靜默覆蓋、血統斷裂——無法回答「這版比上一版好在哪」。Goal 8 的 what-if 模擬已經給出「建議分支」（`branch_suggestion.config_delta`），但當時 `actionable=false`（fork 按鈕 disabled），因為沒有承接分支的機件。

Goal 9 要的是把「策略迭代」變成**顯式的 parent→child 分支**：每個分支釘死 parent、套一個 `config_delta`、可獨立評測、可與 parent 並排比較，且**永不靜默蓋掉 parent 記錄**。

---

## 2. 決策

### 2.1 新增 `research/branch_store.py` — append-only 分支血統簿

沿用 evaluation/candidate store 的 append-only 折疊哲學（`reports/branch_experiments.jsonl`）：`create` append 一筆 `draft`；`evaluate` append 一筆帶回填 `evaluation_id` 的 `evaluated`（draft 那行永不 in-place 改）。分支記錄釘死 `parent_evaluation_id` / `parent_run_id` / `strategy`（血統）。

`create_branch` 是**純血統操作**：讀 parent 的 `lineage.params`，把 `config_delta` 套到一個**新** config dict（parent config 零改動），驗 parent 存在（→404）與 delta key 合法（→422）。

### 2.2 分支再跑靠「distinct config hash」保證不覆蓋 parent（驗收 #3）

`evaluate_branch` 呼叫既有 `evaluate(strategy, profile, param_overrides=…, branch_lineage=…)`：config-key delta 以 `param_overrides` 疊在解析出的 params 之上。因為 `run_id = RunConfig.run_id`（strategy|params|… 的 sha1），**只要有一個 config 值變了，`run_id` 就變**，`evaluation_id` 隨之變——分支的評測記錄**在物理上不可能折疊蓋掉 parent 的**。這是「禁止靜默覆蓋」的結構性保證，而非約定。

`evaluate()` 為此加兩個可選 kwarg（加法、不破壞既有呼叫）：`param_overrides`（分支 config delta）與 `branch_lineage`（寫進 `result["branch"]`，供候選池 badge 分支出身）。

### 2.3 兩種 delta key 詞彙 — create 時 422 守門

delta key 必為二者之一，否則 422：

- **config keys**：策略 `config_model` 真欄位（`lookback_days`…）——套進再跑，產生真的不同回測。
- **execution-overlay knobs**：模擬固定詞彙（`cost_multiplier` / `slippage_bps` / `capacity_scale` / `stop_loss_pct` / `take_profit_pct`）——`simulation` fork 記錄為血統，但現行 runner **不消費**它們（contract §11 的 P1 blocker，模擬模組早已誠實揭露）。overlay-only 分支 `applies_to_rerun=false`，evaluate 回 409（拒絕捏造一個與 parent 相同的再跑），而非假裝有效果。

### 2.4 compare 複用兩邊 `EvaluationResult`，不重跑

`compare_branch` 讀 parent 與 branch 兩邊已持久化的 `headline_metrics` → 逐指標 delta 表 + 一個確定性 `decision`（Sharpe tie-break，可手算的 reasons）。分支未評測時回「parent 欄填、branch/delta 為 null、`branch_evaluated=false`」的提示態，而非報錯。

---

## 3. 為何不這樣做（被否決的替代）

- **原地改 config 重跑**：直接違反驗收 #3（靜默覆蓋 parent、血統斷裂）。否決。
- **把 overlay 模擬旋鈕硬映射成 config 欄位再跑**：映射是 strategy-specific 且脆弱（`slippage_bps`→哪個欄位？需 base 值），且會捏造 runner 根本不讀的效果。改以「overlay-only 分支誠實不可評測（409）」對齊 `simulation.py` 既有的降級哲學。
- **分支開獨立 route/頁**（IA spec 列為 deferred）：MVP 讓分支實驗住既有頁 section（策略資產詳情），不動 nav/router。
- **evaluate 重寫成收 params override 的新入口**：改以在既有 `evaluate()` 加可選 kwarg（加法、既有測試全綠），維持單一評測入口。

---

## 4. 影響

- **行為**：策略迭代現為顯式分支——每分支連 parent、可評測、可 compare；parent run/evaluation/candidate 記錄零 in-place 修改（不可變斷言測試）。
- **模組**：新增 `research/branch_store.py`、`api/routers/research_branches.py`；`evaluation/orchestrator.py::evaluate` 加 `param_overrides` / `branch_lineage`（加法）；`candidate_store.ingest_evaluation` 加 `branch_origin` 欄（讀 `result["branch"]`）；`research/cli.py` 加 `branches` group。
- **API**：+5 ops（`POST/GET /research/branches`、`GET /research/branches/{id}`、`POST …/{id}/evaluate`、`GET …/{id}/compare`）——openapi.gen + drift 四檢綠。
- **前端**：SimulationPanel fork 按鈕點亮（origin=simulation）；策略資產詳情頁新增分支實驗 section（config delta chips / evaluate / compare delta 表）；手動建分支 dialog；候選卡分支出身 badge。
- **無 AI**：suggestion 來源是 simulation / manual / report finding，**不是 LLM**（Goal 9 不建真 AI agent）。
- **相容**：Goal 8 模擬 / 候選池 / 評測 orchestrator 行為不變（加法擴充）。
