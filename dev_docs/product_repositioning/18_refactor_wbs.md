# Refactor WBS — 現況程式碼 → Golden 七層架構

> 版本: v1.0 | 日期: 2026-07-05 | 狀態: In progress
>
> 來源: Sonnet-5 全碼掃描 (10 模組) + Opus 架構綜合。以 `dev_docs/product_repositioning` 為 golden。

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
| W1.2b | 1-fitness | 搬 DataFeed Protocol + EvaluationResult/TargetPortfolio Python schema 進 contracts（**注意 OpenAPI drift**，需 regen frontend/openapi.json） | W1.2a | feature-branch | M | ⏳ 下一波 |
| W1.3 | 1-fitness | carve `live_oos_queue` enqueue port（依賴反轉，consumer 擁有介面），candidate_store 改經注入消費，解 research→governance 反向邊 | W1.1 | feature-branch | M | ✅ done (PR#196) |
| W2.1a | 2-governance | 抽 `promotion_service`+`promotion_store` → `governance/`（無反向邊，乾淨） | W1.1 | feature-branch | L | ✅ done (PR#196) |
| W2.1b | 2-governance | 抽 `watch_registry`+`live_oos_queue`+`live_oos_consumer` → `governance/`；daemon（after_close/orchestration cli）import 重指 | **W1.3** | feature-branch | L | ✅ done (PR#196) |
| W2.2 | 2-governance | 重指 `api/routers/{research_promote,research_validate,watch,runs_report,research_candidates}` 及測試到 governance；endpoint 不變（無 OpenAPI drift） | W2.1 | feature-branch | M | ✅ done (PR#196) |
| W2.3 | 2-governance | 契約 research/strategies/validation ⊄ governance（單向）；watch_registry 抽離後 research ⊄ runtime 無條件成立 | W2.1 | feature-branch | S | ✅ done (PR#196) |
| W3.1 | 3-purify | 拆 `strategies/inst_flow/signal_fn.py`：純 flow_intensity ranking 留 research；qty-sizing/stop_loss/priority 移 strategy_runtime/risk_gate（唯一消費者 market_reader 為 W5 刪除標的，**併入 W5.1**） | **W5.1** | worktree | M | ⏳ 併 W5.1 |
| W4.1 | 4-clean-arch | research_validation 內 domain/application/adapters/infrastructure 拆分；run_persist mapper 出 DB mirror | W2.1 | worktree | XL | ✗ M1-M2 |
| W5.1 | 5-execution | 物理搬 orchestration/runtime/adapters.brokers/risk → services/{strategy_runtime,execution_gateway,risk_gate}；刪 market_reader.py | W4.1 | worktree | XL | ✗ M3-M5 |
| W5.2 | 5-execution | 拆 db_writer（bundle→data_platform；signals/fills/equity→monitoring_ops）；搬 db_reader、monitoring、jobs、config/settings | W5.1 | worktree | L | ✗ |
| W6.1 | 6-api | 拆 api monolith：system.py→三 service router；抽 router 內 domain 邏輯進 application service；apps/api 變薄 composition root | W5.1 | worktree | XL | ✗ |
| W7.1 | 7-monorepo | 建 `quant_platform/{apps,packages,services}`；frontend→apps/web_console；deploy/ 與 research-note md 進 docs/ | W6.1 | worktree | XL | ✗ |
| W8.1 | 8-docs | 同步 dev_docs 08/09、撰 repositioning ADR、維護本 WBS 狀態欄 | W2.1 | direct-commit | M | ✅ |
| FE-R0 | frontend-reset | 前端重設計 WBS/北極星：廢止舊 Grok/web_design 真相源，改採 Codex-style operations console，以 golden 七層為 IA | — | feature-branch | S | ✅ done |
| FE-R1 | frontend-reset | 重寫全局 tokens、AppShell、nav、首頁 Command Center；建立交易/風控/營運密集系統視覺基線 | FE-R0 | feature-branch | M | ✅ done |
| FE-R2 | frontend-reset | 全頁 IA 重排：Data / Research / Governance / Trading / Risk / Operations / System；舊 Live OOS/Deployment 只作 Governance 子流程 | FE-R1 | feature-branch | L | ⏳ 本波 |
| FE-R3 | frontend-reset | 重做 Research 工作台：策略庫、候選池、runs、report、compare、sweep 全改成研究 terminal + evidence ledger | FE-R2 | feature-branch | XL | ⏳ 本波 |
| FE-R4 | frontend-reset | 重做 Governance/Risk/Trading：release gate、paper、target portfolio、order intent、risk decision、fill/reconciliation | FE-R2 | feature-branch | XL | 下一波 |
| FE-R5 | frontend-reset | 重做 Operations：PnL、positions、alerts、incidents、jobs、audit，補 Playwright screenshot audit | FE-R3/4 | feature-branch | L | 下一波 |

## 3.1 執行發現與解決（2026-07-05）

W0/W1.1 完成後續探 W2.1/W3.1，發現兩者**非純機械搬移**、與延後波次隱性耦合。Wave 2 已**全數解決並完成**（PR #196）：

- **W2.1 反向邊 → 已用依賴反轉解決（W1.3）**：`candidate_store`(research) 曾 import `live_oos_queue`(governance-bound)。解法：`select_live_oos` 宣告 `EnqueuePort`（consumer 擁有介面），由 composition root（API router / research CLI）注入具體 `governance.live_oos_queue.enqueue`。research domain/application 遂與 governance 零耦合。
- **composition-root 豁免**：`research/cli.py` 的 `candidates select-live-oos` 命令是 research CLI 的 composition root，需 wiring 具體 governance queue。import-linter 契約用 scoped `ignore_imports` 豁免這**唯一** entry-point 邊（clean-arch 允許 composition root 跨層），domain 純度不受影響。
- **測試環境**：integration 測試在 `POSTGRES_INTEGRATION` 未設時自動 skip，故本地 `pytest -o addopts=""` 即可驗證（unit 全跑）。「無 DB 不能驗」的顧慮解除。
- **W3.1 與 W5 綁定（維持延後）**：`strategies/inst_flow/signal_fn.py` sizing 為 layer-4/5 越層，但唯一 src 消費者 `runtime/market_reader.py` 是 W5 刪除標的；拆出的 sizing 需尚不存在的 strategy_runtime seam。**維持併入 W5.1**。

### 已知 pre-existing 失敗（非本次重構造成，待 W1.2）

`tests/research/evaluation/test_profiles.py::test_builtins_match_contract_examples_exactly` 自文件重建 commit `077431f` 刪除 `dev_docs/contracts/evaluation_profile.schema.json` 起失敗。屬 W1.2（contracts package）範疇——golden 08 要 contracts 落在 `packages/contracts/`，屆時 repoint 此測試即修復。

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
- [ ] `frontend/src/features/research/components/reportviewer/{SimulationPanel,DecisionActionBar}` 仍需 Codex-style evidence ledger 化。
- [ ] Live OOS Queue / Release Gate 仍需改為 Governance operations queue。
- [ ] Data / Risk / Trading / Operations 頁面仍需去卡片化並加強 source/as-of/trace。
