# Refactor WBS — 現況程式碼 → Golden 七層架構

> 版本: v1.1 | 日期: 2026-07-06 | 狀態: **W0–W6 完成 + W7 scaffold 落地**（僅剩 W7.1 物理 big-bang 搬移，需 quiet repo）
>
> 來源: Sonnet-5 全碼掃描 (10 模組) + Opus 架構綜合。以 `dev_docs/product_repositioning` 為 golden。
>
> **進度快照（2026-07-06）**：W0–W2、W3.1、W4.1（research 三層 clean-arch）、W5.1（execution/risk 物理抽離 + fitness 強制 research⊄services + 真 daemon e2e）、W5.2（db_writer 拆 5 服務純 shim）、W6.1a（api monolith 拆 + OpenAPI 零 drift）、W7.1 scaffold（`quant_platform/` 骨架 + 遷移映射）**全數 merged 到 origin/main**（PR #196/#197/#199/#200/#202）。`services/` 現有 5 golden service，golden 最重要 anti-decision「Research 永不 import broker/execution」由 import-linter 物理強制。**唯一剩餘**：W7.1 物理 big-bang（frontend→apps/web_console 等全樹平移），ADR-R05 標 session_actionable=false、需 quiet repo（codex 靜止窗口）逐 service PR。W6.1b/c scoped-out（domain 早在層）。

## 1. 決策摘要

| 項目 | 結論 |
| :--- | :--- |
| 範圍策略 | **Option B — 重定位**，非綠地重建。詳見 [ADR-R01](adrs/ADR-R01-backtest-platform-as-research-layer.md)。 |
| 核心不變式 | Research 層永不下單 / 永不 import broker（golden 最重要 Anti-Decision）。 |
| 交付手段 | 先刪死碼 → import fitness function 鎖邊界 → 逐叢集物理抽離。 |
| 執行節奏 | Session-actionable 波次現在做；XL 機械式搬移（monorepo）延後至 M1–M6，一 service 一 PR。 |

## 2. 現況 vs Golden 落差

`backtest_platform`（163 py，80% cov gate，UI 已接）**已是可運作的第 2 層 Research & Validation**，但含真實越層 bleed：

- **第 3 層 Governance** 混在 `research/`：`promotion_service/store`、`watch_registry`、`live_oos_*`。
- **第 4/5/6 層 Execution/Risk/Monitoring** 混在同 package：`orchestration/`、`runtime/`、`adapters/brokers/paper_broker`、`risk/`、`monitoring/`。
- **硬違規**：`orchestration/collaborators.py` + `after_close.py` 在 research package 內經 PaperBroker **實際下單**。
- Frontend 為乾淨 SPA，僅需目錄搬移。

## 3. WBS 波次

| ID | 波次 | 工作 | 依賴 | 分支策略 | 規模 | 狀態 |
| :-- | :-- | :--- | :-- | :-- | :-- | :-: |
| W0.1 | 0-cleanup | 刪除 `backtest_platform/legacy/`（archive、不打包、不收集、0 引用） | — | feature-branch | S | ✅ done (PR#196) |
| W0.2 | 0-cleanup | 刪死碼與 stale bytecode：`engines/`、`adapters/data_bundle/__init__.py`、influx_writer.pyc、`tests/engines/`、frontend `stores|utils/.gitkeep` | — | feature-branch | S | ✅ done (PR#196) |
| W1.1 | 1-fitness | 加 import-linter，契約：research/strategies/validation **禁 import** adapters.brokers / risk / orchestration / runtime / monitoring；純碼禁 import sqlalchemy/fastapi/shioaji/requests。接 CI。 | W0.2 | feature-branch | M | ✅ done (PR#196) |
| W1.2a | 1-fitness | 建 `packages/contracts/{schemas,examples}`，還原 077431f 誤刪的 8 契約檔到 golden 位置，repoint test_profiles（修 pre-existing 紅燈） | W1.1 | feature-branch | S | ✅ done (PR#196) |
| W1.2b | 1-fitness | 搬 DataFeed Protocol + EvaluationResult/TargetPortfolio Python schema 進 contracts（**注意 OpenAPI drift**，需 regen frontend/openapi.json） | W1.2a | feature-branch | M | 🟡 rescoped（見 §3.1）— 物理搬移前置未就緒，併 W4·W5 |
| W1.3 | 1-fitness | carve `live_oos_queue` enqueue port（依賴反轉，consumer 擁有介面），candidate_store 改經注入消費，解 research→governance 反向邊 | W1.1 | feature-branch | M | ✅ done (PR#196) |
| W2.1a | 2-governance | 抽 `promotion_service`+`promotion_store` → `governance/`（無反向邊，乾淨） | W1.1 | feature-branch | L | ✅ done (PR#196) |
| W2.1b | 2-governance | 抽 `watch_registry`+`live_oos_queue`+`live_oos_consumer` → `governance/`；daemon（after_close/orchestration cli）import 重指 | **W1.3** | feature-branch | L | ✅ done (PR#196) |
| W2.2 | 2-governance | 重指 `api/routers/{research_promote,research_validate,watch,runs_report,research_candidates}` 及測試到 governance；endpoint 不變（無 OpenAPI drift） | W2.1 | feature-branch | M | ✅ done (PR#196) |
| W2.3 | 2-governance | 契約 research/strategies/validation ⊄ governance（單向）；watch_registry 抽離後 research ⊄ runtime 無條件成立 | W2.1 | feature-branch | S | ✅ done (PR#196) |
| W3.1 | 3-purify | 拆 `strategies/inst_flow/signal_fn.py`：純 flow_intensity ranking 留 research；qty-sizing/stop_loss/priority 移 strategy_runtime/risk_gate（唯一消費者 market_reader 為 W5 刪除標的，**併入 W5.1**） | **W5.1** | worktree | M | ⏳ 併 W5.1 |
| W4.1 | 4-clean-arch | research_validation 內 domain/application/adapters/infrastructure 拆分；run_persist mapper 出 DB mirror | W2.1 | worktree | XL | ✅ done（見 §3.1）：W4.1a(domain)+W4.1b(adapters/stores)+W4.1c(run_persist mapper)+W4.1d(application) 全落地；workflows dispatch/runners/cli 依 pin 原地保留 |
| W5.1 | 5-execution | 物理搬 orchestration/runtime/adapters.brokers/risk → services/{strategy_runtime,execution_gateway,risk_gate}；刪 market_reader.py | W4.1 | worktree | XL | ✅ done（見 §3.1）：a risk_gate/b execution_gateway/c strategy_runtime+daemon/d market_reader→live_session+刪/W3.1 sizing 拆出+契約收緊 research⊄services；真 daemon e2e 通過 |
| W5.2 | 5-execution | 拆 db_writer（bundle→data_platform；signals/fills/equity→monitoring_ops）；搬 db_reader、monitoring、jobs、config/settings | W5.1 | worktree | L | ✅ done（見 §3.1）：monitoring/jobs→monitoring_ops、db_writer 拆 db_kernel/runs_writer(留 data/)+bundle(data_platform)+telemetry(monitoring_ops) 純 shim、db_reader→monitoring_ops、c-2 抽 parquet_writer 斷第二條 research→db_writer 鏈；config 遞延 W7 |
| W6.1 | 6-api | 拆 api monolith：system.py→三 service router；抽 router 內 domain 邏輯進 application service；apps/api 變薄 composition root | W5.1 | worktree | XL | ✅ done（見 §3.1）：W6.1a 拆 system.py→system_{risk,alerts,data}，OpenAPI 零 drift；app.py 已是薄 composition root；W6.1b/c domain 邏輯早在 data/services 層（W4.1/W5.x）、router 已薄、剩餘觸 codex 活躍 WP10，scoped-out |
| W7.1 | 7-monorepo | 建 `quant_platform/{apps,packages,services}`；frontend→apps/web_console；deploy/ 與 research-note md 進 docs/ | W6.1 | worktree | XL | 🟡 scaffold done（`quant_platform/` golden 骨架 + 遷移映射 README，見 §3.1）；物理 big-bang 搬移（含 frontend）待 quiet repo，一 service 一 PR，ADR-R05 session_actionable=false |
| W8.1 | 8-docs | 同步 dev_docs 08/09、撰 repositioning ADR、維護本 WBS 狀態欄 | W2.1 | direct-commit | M | ✅ |
| FE-R0 | frontend-reset | 前端重設計 WBS/北極星：廢止舊 Grok/web_design 真相源，改採 Codex-style operations console，以 golden 七層為 IA | — | feature-branch | S | ✅ done |
| FE-R1 | frontend-reset | 重寫全局 tokens、AppShell、nav、首頁 Command Center；建立交易/風控/營運密集系統視覺基線 | FE-R0 | feature-branch | M | ✅ done |
| FE-R2 | frontend-reset | 全頁 IA 重排：Data / Research / Governance / Trading / Risk / Operations / System；舊 Live OOS/Deployment 只作 Governance 子流程 | FE-R1 | feature-branch | L | ✅ done |
| FE-R3 | frontend-reset | 重做 Research 工作台：策略庫、候選池、runs、report、compare、sweep 全改成研究 terminal + evidence ledger | FE-R2 | feature-branch | XL | ✅ done |
| FE-R4 | frontend-reset | 重做 Governance/Risk/Trading：release gate、paper、target portfolio、order intent、risk decision、fill/reconciliation | FE-R2 | feature-branch | XL | ✅ done |
| FE-R5 | frontend-reset | 重做 Operations：PnL、positions、alerts、incidents、jobs、audit，補 Playwright screenshot audit | FE-R3/4 | feature-branch | L | ✅ done（screenshot audit 見 §7.5 + review sign-off） |
| FE-R6 | frontend-reset | 前端「待後端」全面盤點（A doc-drift／B 合理 pending／C 死碼）：清 C 類死鷹架（WiredPage/ENDPOINT/pageSections + 孤兒 getHomeFleet/getSystemHealth/monitor useStrategies），router 塌縮為純 REAL map 迭代；修 A 類過時註解；A′ 靜態 PendingNote→wired hook（HomePage 假狀態、monitor 10 端點）；接 validate 13 指標 health 表（run metrics 真投影，非 pending） | FE-R5 | worktree | M | ✅ done（5 commits；typecheck 綠、235 fe tests）|

## 3.1 執行發現與解決（2026-07-05）

W0/W1.1 完成後續探 W2.1/W3.1，發現兩者**非純機械搬移**、與延後波次隱性耦合。Wave 2 已**全數解決並完成**（PR #196）：

- **W2.1 反向邊 → 已用依賴反轉解決（W1.3）**：`candidate_store`(research) 曾 import `live_oos_queue`(governance-bound)。解法：`select_live_oos` 宣告 `EnqueuePort`（consumer 擁有介面），由 composition root（API router / research CLI）注入具體 `governance.live_oos_queue.enqueue`。research domain/application 遂與 governance 零耦合。
- **composition-root 豁免**：`research/cli.py` 的 `candidates select-live-oos` 命令是 research CLI 的 composition root，需 wiring 具體 governance queue。import-linter 契約用 scoped `ignore_imports` 豁免這**唯一** entry-point 邊（clean-arch 允許 composition root 跨層），domain 純度不受影響。
- **測試環境**：integration 測試在 `POSTGRES_INTEGRATION` 未設時自動 skip，故本地 `pytest -o addopts=""` 即可驗證（unit 全跑）。「無 DB 不能驗」的顧慮解除。
- **W3.1 與 W5 綁定（維持延後）**：`strategies/inst_flow/signal_fn.py` sizing 為 layer-4/5 越層，但唯一 src 消費者 `runtime/market_reader.py` 是 W5 刪除標的；拆出的 sizing 需尚不存在的 strategy_runtime seam。**維持併入 W5.1**。
- **W1.2b 字面標的與現況不符 → rescoped**：全碼掃描發現要「搬進 contracts」的三個 Python schema 中，`EvaluationResult` **不是類別**（API 由 `result_builder` 組 dict 回傳，無 response_model）、`TargetPortfolio` **不存在**（屬 W4/W5 執行層才誕生的型別）、`DataFeed` Protocol 存在但**零 production 消費者**（唯一 import 是自身測試，ADR-035 預留 seam）。故：(1) 為單一無人用 Protocol 現在新建 Python `contracts` 套件屬過度設計，**不做**；(2) 因無任何 endpoint 以這些型別為 response_model，`frontend/openapi.json` **無 drift**（`check_openapi_drift.py` 驗 `[OK] live spec matches`），原「regen openapi」顧慮不成立；(3) 真正的對外契約 `EvaluationProfile`（Pydantic）之 JSON schema 已於 **W1.2a** 落地 `packages/contracts/schemas/`，並由 `test_profiles.py` 鎖住 examples↔builtins 不 drift。**物理搬移併入 W4·W5**（型別/消費者屆時就位）。本波 actionable 部分：修正 `profiles.py` 兩處指向舊 `dev_docs/contracts/` 的 stale 註解 → `packages/contracts/schemas/`（W1.2a 移動遺留，commit `c683257`）。

### ~~已知 pre-existing 失敗~~ → 已解決（W1.2a repoint）

`tests/research/evaluation/test_profiles.py::test_builtins_match_contract_examples_exactly` 曾自 commit `077431f` 刪除 `dev_docs/contracts/evaluation_profile.schema.json` 起失敗。**W1.2a 已 repoint 至 `packages/contracts/schemas/evaluation_profile.schema.json`，測試現通過**（全後端 `pytest -o addopts=""`：1443 passed / 3 skipped / 0 failed；`lint-imports` 3 kept / 0 broken）。

- **W4.1 拆 4 子波執行（架構分析，`.claude/context/decisions/`）**：39 檔 + ~25 shim 遠超 PR size 準則，故切 W4.1a(domain 抽出)/W4.1b(stores→adapters)/W4.1c(run_persist mapper)/W4.1d(application+infra)，各自獨立可 review、tests+lint 綠。**W4.1 全數落地 main**（每子波獨立驗證 1427 passed（codex `6546083` prune 掉 grafana/daily_flow 測試後基線由 1443→1430）/ 3 skipped / 0 failed、lint 3 kept、動態 dispatch 專項測試綠）：
  - **W4.1a**（`f1567c6`+`62af838`）：6 純檔 → `research/domain/`（run_config/candidate_state/compare/simulation/run_candles/notebook_export）+ `research.domain` 純度加入 import-linter 契約 3。
  - **W4.1b**（`de89900`+`9b74083`）：11 file-backed stores → `research/adapters/`（8 純 IO + branch_store/candidate_store/finlab_universe 整檔搬，domain 滲漏留待後續內部拆分）。3 個測試因 monkeypatch-on-shim/私有符號存取改指 `research.adapters.*`。
  - **W4.1c**（`a384eb8`）：`run_persist` 拆 `adapters/{run_db_mapper,run_writer}`。
  - **W4.1d**（`08289c0`）：is_harness/sweep/batch/orchestrator/loader → `research/application/`。
  - **依 pin 原地保留**（物理不動、非漏做）：`workflows/{doe,go_gates,truth_gate,paper_replay,universe}`（被 `research_workflows.py` importlib 字串 dispatch + `system.py` monkeypatch pin 路徑）、`runners.py`（registry 副作用 import）、`cli.py`（composition root + import-linter ignore_imports 引用）。移動它們是純 churn + silent-break 風險。
  - 所有外部消費者（api/strategies/governance/cli）靠舊路徑 `__all__` re-export shim **零改動**（ADR-R05 維持 import path）。

- **W5.1 execution 物理抽離（2026-07-06，架構分析 `.claude/context/decisions/architect-2026-07-05-2315-*`）**：切 4 子波 leaf 先 daemon 後——a `risk/`→`services/risk_gate/`、b `adapters.brokers`+`orchestration/collaborators`→`services/execution_gateway/`、c `orchestration/{daily_flow,after_close,timer_health,cli}`+`runtime/paper_daemon`→`services/strategy_runtime/`（cli 可執行 shim + deploy unit 改 canonical 路徑）、d `runtime/market_reader`→`services/strategy_runtime/live_session` 再刪 + **W3.1** signal_fn sizing→`inst_flow_signals`（flow_intensity 留 research，不留 shim 避反向邊）。**契約收緊**：import-linter contract 1 加 `backtest_platform.services`，research/strategies/validation ⊄ services 物理強制（golden 最重要 anti-decision）。`runtime/{trading_calendar,market_data_errors}` 留共享 kernel。**真 daemon e2e**（.env FinLab token+pg）：list-stages/after-close --dry-run/live-oos consume exit 0、真 panel 29×3+freshness PASSED。
- **W5.2 db_writer 拆分（架構分析 `architect-2026-07-06-0035-*`）**：a `monitoring/`→`services/monitoring_ops/`、b `jobs/`→`services/monitoring_ops/jobs/`、c 抽 `data/db_kernel.py`（DBConfig/_connection/_serialize_cell）+ `data/runs_writer.py`（_RUNS_COLS/upsert_runs，**留 data/ 不進 service**，repoint research/adapters/run_writer 脫離 db_writer——契約閘門）、**c-2** 抽純 `data/parquet_writer.py`（斷架構分析漏掉的第二條 research→finlab_source→finmind_etl→db_writer 鏈，Linus 式消除特殊情況非加豁免）、d bundle→`services/data_platform/bundle_writer`、e telemetry→`services/monitoring_ops/telemetry_writer`、f db_reader→`services/monitoring_ops/telemetry_reader`。db_writer 收斂為**零 live code 純 re-export shim**。config/ **遞延 W7**（config/universe 被 strategies module-level import，搬則違約）。
- **W6.1 api monolith 拆（架構分析 `architect-2026-07-06-*`）**：`app.py` 早已是薄 composition root，唯一真 monolith `system.py`（428 行/18 endpoints/3 領域）由 **W6.1a** 純機械拆成 `system_{risk,alerts,data}.py`（路徑/method/response_model/Pydantic class 名逐字不變 → **OpenAPI 零 drift**）。W6.1b/c（router domain 下沉）**scoped-out**：業務邏輯早在 data/services 層（W4.1/W5.x），router 已薄委派，剩餘 datasets/ingest/universe_build 觸 codex 活躍 WP10 surface，下沉為 speculative 抽象稅 + 高碰撞風險，不做。順修 W5.2c 遺留：`check_openapi_drift.py` 的 `_RUNS_COLS` 指向改 runs_writer（code-doc-sync）。
- **本波 baseline**：`POSTGRES_PASSWORD=change_me_in_production uv run pytest -o addopts=""`（本機 codex pg 需此前綴強制 placeholder，否則「無 DB 降級」單元測試假失敗）→ 1457 passed / 3 skipped / 0 failed（另 1 pre-existing 失敗 test_ingest_universe_resolves_symbols 屬 codex WP10 symbols_for/data_root，非本波）；lint-imports 3 kept；drift All contract checks passed。**已落地 origin/main：PR #202 merged（merge commit `32e217e`，2026-07-06）**——含 W5.1+W5.2+W6.1a+W7.1 scaffold + drift 腳本 _RUNS_COLS 修正。**多 session 落地教訓**：初期試 local-main CAS（`git update-ref`）逐波推進，但 codex 反覆 checkout main，即使 CAS 成功也會在其 dirty worktree 腳下移 ref → services/ 在 codex index 顯示為 staged deletion，一 commit 即 revert（已即時偵測並回退修復）。**正解＝走 PR 到 origin/main**（codex 既定模式 #196/#197/#199/#200），branch 累積全波次、rebased 於最新 origin、綠燈後開 PR。CI backend 唯一紅 `test_ingest_universe_resolves_symbols`（422!=202）屬 codex WP10 `symbols_for` 讀真 data/ 而非測試 tmp fixture，1 failed / 1453 passed，非本 PR 回歸（stash 對照證實），CI 非 hard-block（mergeable）故經使用者授權 merge。

- **W7.1 scaffold（2026-07-06）**：依 ADR-R05「先建 scaffold 讓物理搬移機械化」，落地 `quant_platform/` golden 骨架（apps/{api,web_console,workers} + packages/{domain,application,adapters,infrastructure,contracts} + services/8 + tests/deploy/docs）+ 每層 README 記錄 current backtest_platform/ → W7 target 逐目錄遷移映射 + big-bang 紀律（`quant_platform/README.md`）。純新增零既有改動、lint 3 kept。**物理搬移未做**：163 py + ~250 fe 含 frontend→apps/web_console 是 big-bang，與 codex 活躍前端全碰撞，ADR-R05 標 session_actionable=false，需 quiet repo（codex 靜止窗口）逐 service PR 執行。前置完成度高（W4.1/W5.x/W6.1 已把 research 三層 + 5 service + 薄 api 就定位），big-bang 幾近純機械。

### 分支策略實務註記

WBS 原標 W2.x 為 worktree，實際採 **feature-branch**：本次為單一 sequential session、無並行 session，逐波依序 commit。worktree 保留給並行/多 session/tree-wide 衝突場景（見 memory `branch-strategy-judgment`）。

## 4. Kill-list（依安全度，低風險先）

| 路徑 | 理由 | 風險 |
| :--- | :--- | :-- |
| `src/backtest_platform/engines/` | ADR-037 已刪 source，僅剩 stale `__pycache__` + 空 zipline_adapter 目錄 | low |
| `src/backtest_platform/adapters/data_bundle/__init__.py` | 0-byte 空 stub，0 引用 | low |
| `monitoring/__pycache__/influx_writer.cpython-311.pyc` | 無對應 .py source 的殘留 bytecode | low |
| `tests/engines/`（pyc 殘留） | ADR-037 移除 engine 後未清 | low |
| `frontend/src/stores/.gitkeep`、`frontend/src/utils/.gitkeep` | 空 scaffold 目錄，狀態走 TanStack Query / features/*/lib | low |
| `backtest_platform/legacy/` | 自述 archive；不打包、不收集、0 live 引用；含 broker SDK / UI-reads-DB 反模式範本 | low |
| `frontend/src/app/redirects.tsx` shims | 保舊 URL 的 client redirect，確認無外部連結後可刪 | low |
| `api/routers/home.py`、`monitor.py` 部分 stub | 永久 PENDING stub，M4 producer 落地後退役 | medium |
| `runtime/market_reader.py` | broker-driving config disguised as research helper；relocate-then-delete | high |
| `orchestration/{after_close,collaborators}.py` | research package 內實際下單；**relocate** 到 strategy_runtime 非刪除（撐著 daemon） | high |

## 5. 邊界違規（fitness function 標的）

見 [ADR-R03](adrs/ADR-R03-execution-risk-monitoring-separation.md)。核心：`orchestration/collaborators.py`+`after_close.py`+`runtime/market_reader.py` 在 research package 內下單，違反 golden「Research 不直連 Broker」。W1.1 先用 import-linter 鎖住 research/strategies/validation 不得 import 這些叢集，物理搬移於 M3–M5。

## 6. 風險與緩解

- **daemon 是 load-bearing userspace**：搬 orchestration/adapters.brokers 前用 re-export shim，端到端跑過 after-close daemon 再刪舊路徑；破壞性移動前打 `backup/<branch>-<date>` tag。
- **OpenAPI drift 破 SPA**：每次 router 搬移後跑 `scripts/check_openapi_drift.py` + openapi-typescript regen。
- **import-linter 立即 RED**：research→governance（watch_registry→runtime）今日存在；W1.1 只鎖已綠規則，runtime/governance 子規則於 W2.1 抽離後補。
- **monorepo big-bang PR 過大**（163 py + ~250 fe）：維持 deferred worktree 波次，一 service 一 PR，不做單一 mega-commit。
- **多 session 併發**：重 worktree 波次用 git worktree 隔離，勿共用 HEAD。

## 7. Frontend Reset — Codex-Style Operations Console

### 7.1 問題

現有前端仍保護舊 IA 與舊視覺真相源：

- `frontend/GOAL.md` 指向已刪除的 `dev_docs/web_design/*`。
- `tokens.css` 仍是 Grok 單色 token，與 golden 七層產品定位不一致。
- `nav.ts` 仍以 Research / Live OOS / Deployment / Monitor / System 分區，沒有把 Data / Governance / Strategy/Portfolio / Risk / Execution / Operations 作為產品內一等區域。
- 多數頁面像舊研究後台，而不是交易/風控/營運操作台。

上述前三項已於 FE-R0/FE-R1 修正；目前剩餘風險集中在頁面層仍有舊卡片牆、舊註解與舊分區語義。

### 7.2 新方向

前端重設計為 **Codex-style operations console**：

| 原則 | 說明 |
| :--- | :--- |
| Dense first | 以表格、狀態列、ticker、ledger、risk blotter 為主，不做行銷式 hero。 |
| Seven-layer IA | Data / Research / Governance / Trading / Risk / Operations / System 都是一等區域。 |
| Evidence over decoration | 每個指標都要有來源、as-of、trace id；pending 不造假。 |
| Risk visible everywhere | CRIT / HALT / reconciliation lock 全站可見。 |
| Keyboard / drill-down | Cmd-K、表格鍵盤導覽、audit trail drill-down。 |
| Codex UI color | 中性黑白灰、細格線、單行狀態列、monospace 數字、有限功能色。 |

### 7.3 設計 token

| Token 類 | 方向 |
| :--- | :--- |
| Base | Codex neutral near-black / off-white |
| Surface | panel / raised / table-row / input 用中性灰階分層 |
| Border | 1px hairline grid，降低 card 感 |
| Typography | sans for labels，monospace tabular for numbers/symbols/ids |
| Functional colors | gain/loss/warn/crit/info/halt；不用品牌漸層 |
| Layout | left rail + top market status + dense workspace |

### 7.4 驗收

- [x] `frontend/GOAL.md` 不再依賴舊 `dev_docs/web_design` 作為真相源。
- [x] `NAV` zone 改為七層操作台 IA。
- [x] `AppShell` 有 top market/risk status bar、七層 rail、workspace header。
- [x] 首頁改為 Command Center，優先呈現 readiness、risk、data、research、operations。
- [x] `npm run typecheck` 通過。

### 7.5 FE-R2/FE-R3 進度

- [x] `frontend/src/router.tsx` 註解與 fallback route title 改為七層語義；舊 Live OOS / Deployment / Monitor 只作相容 URL 或子流程。
- [x] `frontend/src/features/research/pages/StrategyHubListPage.tsx` 由策略卡片牆改為 strategy ledger。
- [x] `frontend/src/features/research/pages/CandidatePoolPage.tsx` 由卡片牆改為 Research evidence blotter。
- [x] `frontend/src/features/research/components/candidates/CandidateCard.tsx` 由候選卡改為單列決策單元，保持 strategy / scorecard / return-risk / governance / action 同列掃描。
- [x] `frontend/src/features/research/pages/RunsTablePage.tsx` 由舊表格頁改為 run ledger，加入 gate 分布與 dense 操作列。
- [x] `frontend/src/features/research/pages/ComparePage.tsx` 由鬆散比較頁改為 comparison ledger，集中 baseline/run/gate 分布與 pending evidence queue。
- [x] `frontend/src/features/research/pages/SweepPage.tsx` 由表單式掃描頁改為 sweep terminal，集中 grid/estimate/job 與 pending evidence queue。
- [x] `frontend/src/features/research/pages/RunReportPage.tsx` 外殼由報告卡片頁改為 run evidence ledger，KPI/reproduce/cost/action 改為 dense terminal layout。
- [x] `frontend/src/features/research/pages/ReportViewerPage.tsx` 首屏外殼改為 evaluation evidence ledger；headline banner 與 scorecard summary 已去卡片化。
- [x] `frontend/src/features/research/components/reportviewer/{ScorecardTabs,GateChecksSection}` 改為 Codex-style evidence ledger；去除卡片式外框，沿用全域中性色票。
- [x] `frontend/src/features/research/components/reportviewer/{SimulationPanel,DecisionActionBar}` 改為 Codex-style evidence ledger / sticky command strip。
- [x] Live OOS Queue / Release Gate / Promote 改為 Governance operations queue / gate ledger / promotion state-machine ledger。
- [x] Data Platform 入口改為 Codex-style data ledger；dataset catalog 由卡片牆改為資料字典 blotter，bundle manifest 沿用 ledger table。
- [x] Risk / Trading / Operations 外觀基線去卡片化：shared KPI/pending/table、Watch rows、Alerts channel 均改為 Codex-style ledger cells。
- [x] Risk / Trading / Operations 共用 QueryState 補 evidence meta strip：source / total / as-of / ttl / trace，缺值明示 `—` 不推測。
- [x] Playwright screenshot audit 完成：23 routes × 3 viewports = 69 screenshots，另驗 3 redirect routes；產物在 `dev_docs/ui_audit/codex_2026-07-05/`。原始截圖捕捉的是 frontend fallback/error state；2026-07-05 已補 `scripts/seed_demo_data.py`，並以 `127.0.0.1:8083` 驗證 Monitor/Research/System 的 TimescaleDB + ledger + parquet populated happy path。
