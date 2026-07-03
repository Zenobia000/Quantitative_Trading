# ADR-039: Evaluation Profile 層 — 在 ADR-029 workflow primitives 之上新增高階評估編排層 + 候選池狀態機

> **狀態：** 已接受 | **日期：** 2026-07-03 | **決策者：** Self
> **建立於（builds on）：** [ADR-029](./ADR-029-research-workflow-standardization.md)（研究工作流標準化 — doe/go_gates/truth_gate/paper_replay primitives）— 本 ADR 在其**之上**新增 profile 編排層，**不改動任一 primitive 行為**
> **相關：** [ADR-025](./ADR-025-two-stage-validation-gate-and-paper-promotion.md)（兩段驗證閘 — `deployment_strict` profile 原封包裝其 truth gate，門檻逐字引用不放寬）、[ADR-033](./ADR-033-paper-watch-tier.md)（Paper-Watch 零資本觀察艙 — live-OOS queue 是其人為選取層、非取代其 enforcement）、[ADR-028](./ADR-028-strategy-dispatch-contract.md)（策略 dispatch — profile 一律走 `get_strategy().run()`，不直呼策略函式）
> **產品依據：** `rebuild_goal_spec_ai_requirements_2026-07-03.md` Goal 2/3/4；`dev_docs/contracts/`（契約真相源，PR #183）

---

## 1. 背景與問題

### 1.1 現況：只有「部署級嚴格閘」一條評估路徑

ADR-029 把研究工作流標準化為四個 low-level primitives（`doe`/`go_gates`/`truth_gate`/`paper_replay`），各自讀策略的 `research_config.py` 宣告、走 ADR-028 dispatch。這解決了「每加一支策略要碰 7-12 個檔」的問題，但留下一個**產品層**缺口：

- **唯一面向使用者的評估體驗是 `truth_gate`**（ADR-025 兩段閘），它是部署級、tens-of-minutes、binary（REAL/REJECTED/PAPER_WATCH/INCOMPLETE）的資本保護閘。
- 一個研究者想問「這支策略**值不值得繼續研究**？」（秒級、單段回測、五維體檢）沒有對應入口——只能要嘛跑完整 truth gate（太重、且對尚未定型的假設是錯的問題），要嘛自己拼 primitives。
- 弱/負/資料有問題的策略跑完 truth gate 得到 REJECTED 後**沒有被當作研究資產保存**——binary verdict 丟掉了「為什麼弱、弱在哪一維」的資訊。

### 1.2 產品重定位要求：research triage 與 deployment 分離

`rebuild_goal_spec` 的 Mission 是把平台從「以 runs/gates/promote 為主的工程型介面」重構為「策略研究資產管理工作台」：使用者建資產 → 跑**可配置 evaluation profile** → 立即取得 FinLab-style scorecard report → 保留好壞策略 → 從候選池勾選 Live OOS → **最後才**進部署級嚴格閘。

這要求一個 primitives 之上的編排層：把「跑哪些 primitives、產哪五張 scorecard、套哪些 severity-graded gates、多貴」封裝成**可重用的 recipe（profile）**，並把每次評估的結果（含失敗者）沉澱成**候選資產**供人決策。

---

## 2. 決策

### 2.1 新增 `research/evaluation/` — profile 之上、primitives 不動

新增一個高階層，內含四個內建 profile，各自**編排（wrap）**既有 primitives，永不取代：

| Profile | wraps | 問的問題 | 量級 |
| :--- | :--- | :--- | :--- |
| `quick_triage` | `single_run`（一次 dispatch）| 值不值得研究？（五維 scorecard，無 PBO/DSR/WFA/paper）| 秒 |
| `fixed_hypothesis_oos` | `single_run` + `go_gates` | 事前鎖定假設的 IS/OOS + WFA-lite 廣度 + 成本壓力 | 分 |
| `grid_search_selection` | `doe` + `go_gates` | 從參數地景選出的 config：landscape PBO + trials-deflated DSR | 十分 |
| `deployment_strict` | `truth_gate` | ADR-025/030 兩段閘**原封不動**，僅以 deployment-level profile 曝露 | 十分 |

**硬性邊界（本 ADR 的核心保證）：**

1. **primitives 行為零改動**——`deployment_strict` 呼叫 `run_truth_gate(cfg)` 原封，ADR-025/030 判準與 ADR-016 部署門檻逐字引用、不放寬（spec §8 #5/#8）。~1434 既有測試全綠即證。
2. `severity` 取代單一 binary verdict：`info`（顯示）→ `warn`（可入池的註記）→ `block_live_oos`（不花 live OOS，除非人為 override）→ `block_deploy`（永不配資）。
3. **失敗/弱/負/資料有問題的策略一律完整持久化**（全域驗收 #5）——evaluation 寫 append-only JSONL ledger，候選狀態機保留 negative/weak/data_issue 為可發現的研究資產。
4. 每指標 `pass|warn|fail|missing|not_applicable|not_available`——無法從現有 stores 產出的欄位（benchmark alpha/beta、VaR/CVaR、per-trade pnl 的整張 Win-Rate card、ADV 流動性、git_sha 共 12 族）誠實標 `not_available` + reason，**絕不造假**（spec §8 #6）。門檻定義在 profile 的 `gates[]`（severity-graded，權威）；scorecard 顯示參考檻為 module-level 常數表（data，非邏輯——沿用 `gate_state.DEFAULT_GATE` 的「門檻是資料」慣例）。

### 2.2 新增候選池狀態機 + live-OOS 人為選取層（Goal 4）

- `candidate_store.py` — 每次 evaluation 建立/更新一個候選（`cand_<strategy>`），狀態機 `draft→triaged→promising/weak/negative/data_issue→live_oos_selected→…→archived`，轉移 deterministic（`candidate_state.py` 純函式全轉移測試）。
- `candidate_decisions.jsonl` — append-only 決策事件（同 `promotion_store`/`watch_registry` 事件溯源哲學）；override 路徑（非 eligible 的 select、archive）**強制 reason**，缺 reason 拒絕（422）。
- `live_oos_queue.jsonl` — **人為選取層**：任何人選中的候選落此 queue，帶 `watch_registry` 不建模的選取稽核（`selected_by`/`selection_reason`/`override`）。這**不取代** ADR-033 的 enforcement——`watch_registry` 仍是 DSR ∈ [0.90, 0.95)、最多 2 艙、90 天、一次性再入的守門者；queue 是其上的一般化人為選取層（Goal 10 才接 paper replay / 折疊觀察時鐘）。

### 2.3 曝露方式：CLI + read-only API + 契約重生

- CLI：`research evaluate --strategy --profile`、`research candidates list/decide/select-live-oos`。
- API（envelope + #176 分頁 + doc 25 §2 錯誤碼）：9 個端點（`/research/profiles`×2、`/research/evaluations/{id}`(+`/report`)、`/research/candidates`×4、`/research/live-oos/queue`）。evaluation 的**執行**走 CLI（保持 API dependency-light、避免在 API 層跑重回測），API 只讀。
- `openapi.json` + `frontend/src/types/api.gen.ts` 同 PR 重生（contract-drift 四檢硬閘綠：92 ops）。

---

## 3. 為何 profile 是 primitives 之上的層、而非改 primitives 或第五個 primitive

| 方案 | 為何否決 |
| :--- | :--- |
| 把 scorecard/severity 塞進各 primitive | 破壞 ADR-029「primitive 是 low-level workflow 宣告」的單一職責；且 `deployment_strict` 一旦要改 `truth_gate` 就違反「不放寬部署閘」的硬邊界 |
| 新增第五個 primitive `evaluate` | primitive 是**同層**的 workflow；profile 需要**編排多個** primitive（grid = doe+go_gates）並疊加 scorecard/severity/report/candidate，職責不同層——放同層會讓 loader/dispatch 語義糊掉 |
| 直接讓前端拼 primitives | 契約邊界會散在前端；且「哪些 primitive、哪些門檻、多貴」是後端知識，應封裝成後端 recipe（Goal 2 契約要求每個 profile 宣告 `wraps_primitives`/`gates`/`runtime_magnitude`）|

profile 層放 primitives **之上**，向下只透過 dispatch（ADR-028）+ 呼叫 primitive 的公開函式，向上產出契約 `EvaluationResult`/`ReportPackManifest`/`Candidate`——與 ADR-029 的分層一致、可獨立測試、且天然守住「不改 primitive」的邊界。

---

## 4. 後果

**正面：** research triage 與 deployment 成為分離的使用者旅程（全域驗收 #4/#8）；弱/負策略成為可比較的研究資產（#5）；初始輸出是五維 scorecard 而非 binary verdict（#6）；候選池讓人手動勾選 Live OOS（#7）；嚴格閘仍在但不再是第一個面向使用者的體驗（#8）。

**負面/技術債：** (1) `deployment_strict` 為取 scorecard 的 returns/trades **多跑一次 IS run**（truth gate 內部已跑一次）——tens-of-minutes profile 可接受，未來可讓 truth_gate 回傳 series 消除。(2) report pack 的 series 目前寫 `series.json`（JSON），契約列的 `equity.parquet`/`trades.parquet` 誠實標 `not_available`（v1 sidecar 為 JSON、parquet writer 延後）。(3) `fixed_hypothesis_oos` 的 `oos_holdout_sharpe` 尚未獨立跑 holdout（標 missing）——後續補。(4) Win-Rate 整張卡對 panel 策略 `not_available`（per-trade pnl schema 是 P1 blocker，契約 §11 已登記）。

**邊界確認（非目標）：** 不改 strategy runner contract；不刪 low-level workflows；不放寬 strict truth gate；不做 AI optimize / 互動模擬；不做 DB migration（JSONL 即可）。
