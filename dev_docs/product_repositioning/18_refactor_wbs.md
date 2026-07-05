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
| W1.2 | 1-fitness | 建 `packages/contracts` scaffold + 搬 DataFeed Protocol、EvaluationResult/TargetPortfolio schema 出 api/response_models | W1.1 | feature-branch | M | ⏳ 下一波 |
| W1.3 | 1-fitness | **新增**（§3.1 發現）：carve `live_oos_queue` port，研究端（candidate_store/live_oos_consumer）改經介面消費，解 research→governance 反向邊 | W1.1 | feature-branch | M | ⏳ W2.1 前置 |
| W2.1 | 2-governance | 抽第 3 層出 research/：`promotion_*`、`watch_registry`、`live_oos_*` → 新 `governance/` package；留 re-export shim 保住 daemon | **W1.3** | worktree | L | ⏳ 需 DB 驗證環境 |
| W2.2 | 2-governance | 重指 `api/routers/research_promote.py`+`watch.py` 及測試到 governance；驗 OpenAPI 不變 | W2.1 | worktree | M | ⏳ |
| W2.3 | 2-governance | 加契約：research 禁 import governance（單向 research→governance via contract）；watch_registry 抽離後補 research⊄runtime | W2.1 | worktree | S | ⏳ |
| W3.1 | 3-purify | 拆 `strategies/inst_flow/signal_fn.py`：純 flow_intensity ranking 留 research；qty-sizing/stop_loss/priority 移 strategy_runtime/risk_gate（唯一消費者 market_reader 為 W5 刪除標的，**併入 W5.1**） | **W5.1** | worktree | M | ⏳ 併 W5.1 |
| W4.1 | 4-clean-arch | research_validation 內 domain/application/adapters/infrastructure 拆分；run_persist mapper 出 DB mirror | W2.1 | worktree | XL | ✗ M1-M2 |
| W5.1 | 5-execution | 物理搬 orchestration/runtime/adapters.brokers/risk → services/{strategy_runtime,execution_gateway,risk_gate}；刪 market_reader.py | W4.1 | worktree | XL | ✗ M3-M5 |
| W5.2 | 5-execution | 拆 db_writer（bundle→data_platform；signals/fills/equity→monitoring_ops）；搬 db_reader、monitoring、jobs、config/settings | W5.1 | worktree | L | ✗ |
| W6.1 | 6-api | 拆 api monolith：system.py→三 service router；抽 router 內 domain 邏輯進 application service；apps/api 變薄 composition root | W5.1 | worktree | XL | ✗ |
| W7.1 | 7-monorepo | 建 `quant_platform/{apps,packages,services}`；frontend→apps/web_console；deploy/ 與 research-note md 進 docs/ | W6.1 | worktree | XL | ✗ |
| W8.1 | 8-docs | 同步 dev_docs 08/09、撰 repositioning ADR、維護本 WBS 狀態欄 | W2.1 | direct-commit | M | ✅ |

## 3.1 執行發現：隱性耦合（2026-07-05，Opus 執行 W0/W1 後探查）

W0（清死碼）與 W1.1（import-linter 鎖邊界）已完成並驗證綠燈、開 PR #196。續探 W2.1/W3.1 時發現兩者**並非純機械搬移**，與延後的 XL 波次隱性耦合，需設計決策 + 完整測試基建（DB）才能安全落地：

- **W2.1 反向邊阻擋乾淨抽離**：`research/candidate_store.py`（留在 research）import `research/live_oos_queue.py`（要搬 governance）。直接搬會製造 research→governance 反向依賴，正是 W2.3 要禁止的方向。**前置**：先把 `live_oos_queue` 的 research 端消費（candidate_store、live_oos_consumer）反轉為 port/介面，或重新判定 queue 的歸屬層，再搬。另 `promotion_service`→`validation_store`/`runners`、`live_oos_consumer`→`research.workflows` 為 governance→research 合法方向，可隨搬。daemon 端 `orchestration/after_close.py`→`watch_registry` 需 re-export shim 保命。
- **W3.1 與 W5 綁定**：`strategies/inst_flow/signal_fn.py` 的 sizing（`per_name_cap`、`STOP_LOSS_FRAC=0.04`、`qty`）確為 layer-4/5 越層，但其**唯一 src 消費者是 `runtime/market_reader.py`**——而該檔本身是 W5 要刪的 broker-driving helper。拆出的 sizing 需落到尚不存在的 strategy_runtime seam，故 W3.1 應與 W5.1 併波，不宜單獨提前。

**修正建議**：W2.1 前插入 **W1.3「carve live_oos_queue port（研究端經介面消費）」**；W3.1 併入 W5.1。兩者皆需可跑完整 pytest（含 DB integration）的環境驗證，列為下一 session 起點。

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
