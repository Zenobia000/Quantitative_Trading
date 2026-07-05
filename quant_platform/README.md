# quant_platform — Golden Monorepo Scaffold (W7.1)

> 狀態: **Scaffold only**（空骨架 + 遷移映射）。物理搬移是 W7.1 的 big-bang 步驟，
> 需 quiet repo（ADR-R05 標 `session_actionable=false`），一 service 一 PR 執行。

## 目的

ADR-R05 定義 golden 頂層結構 `quant_platform/{apps,packages,services}`。此 scaffold
先建**空目錄骨架 + 逐目錄遷移映射**，讓最終物理搬移**機械化、可 review**，並在綠色
fitness-function wall + backup tag 之後執行。**此 scaffold 不搬任何既有檔**——`backtest_platform/`
與 `frontend/` 維持原地運作，直到 big-bang PR 一次性平移。

## 前置完成度（W0–W6，本 scaffold 建立時）

已完成的邏輯抽離讓 W7 的物理搬移**幾近純機械**（來源已就定位）：
- ✅ research 已拆 `backtest_platform/research/{domain,application,adapters}`（W4.1）。
- ✅ 5 個 service 已建於 `backtest_platform/services/{risk_gate,execution_gateway,strategy_runtime,data_platform,monitoring_ops}`（W5.1+W5.2）。
- ✅ api 已拆 per-service router（W6.1a），`app.py` 為薄 composition root。
- ✅ import-linter 契約物理強制 research ⊄ services。

## 遷移映射（current `backtest_platform/` → W7 target）

| W7 目標 | 現況來源（backtest_platform/） | 狀態 |
| :--- | :--- | :--- |
| `apps/api/` | `src/backtest_platform/api/`（app.py composition root + routers/） | 需搬 + 留 `backtest_platform.api.app:app` re-export shim（uvicorn/drift 錨） |
| `apps/web_console/` | `frontend/`（整個 SPA） | **big-bang，與 codex 前端全碰撞——最後搬、需 quiet repo** |
| `apps/workers/` | `src/backtest_platform/services/strategy_runtime/{cli,after_close,paper_daemon}` 的 daemon 入口 | daemon 進程入口；deploy unit 已指 canonical `services.strategy_runtime.cli` |
| `packages/domain/` | `src/backtest_platform/research/domain/`（+ strategies 純因子） | research.domain 已純（import-linter 強制） |
| `packages/application/` | `src/backtest_platform/research/application/` | W4.1d 已抽 |
| `packages/adapters/` | `src/backtest_platform/research/adapters/` + `data/db_kernel.py`（共享 DB kernel） | |
| `packages/infrastructure/` | `src/backtest_platform/config/{settings,universe}`（W5.2 遞延至此）、`data/{db_kernel,runs_writer,parquet_writer}` | config/ 遞延主因：被 strategies/api module-level import，需與 packages 同波搬 |
| `packages/contracts/` | `packages/contracts/`（已在 golden 位置，W1.2a） | ✅ 已就位，僅需併入 quant_platform/ |
| `services/data_platform/` | `src/backtest_platform/services/data_platform/`（bundle_writer） + `data/{finmind_etl,finlab_source,bundle_registry,universe_registry,...}` | service 殼已建，data/ ETL 待併 |
| `services/research_validation/` | `src/backtest_platform/research/` + `validation/` | 第 2 層主體 |
| `services/governance_release/` | `src/backtest_platform/governance/`（W2.1 已抽） | ✅ package 已成形 |
| `services/strategy_runtime/` | `src/backtest_platform/services/strategy_runtime/` | ✅ W5.1c 已建 |
| `services/portfolio_engine/` | （尚未拆出——SizingGate/portfolio 邏輯目前散在 risk_gate/collaborators） | 未來波次 |
| `services/risk_gate/` | `src/backtest_platform/services/risk_gate/` | ✅ W5.1a 已建 |
| `services/execution_gateway/` | `src/backtest_platform/services/execution_gateway/` | ✅ W5.1b 已建 |
| `services/monitoring_ops/` | `src/backtest_platform/services/monitoring_ops/`（+ jobs/、telemetry_writer/reader） | ✅ W5.2 已建 |
| `tests/` | `backtest_platform/tests/` | 隨各 package/service 搬 |
| `deploy/` | `backtest_platform/deploy/` | systemd/cron unit（已指 canonical 路徑） |
| `docs/` | `dev_docs/`（product/architecture/adrs/runbooks/api/operations） | research-note md 併入 |

## Big-bang 執行紀律（W7.1 物理搬移，需 quiet repo）

1. **quiet repo 前提**：codex 前端/api 工作暫停（`ps aux | grep codex` 確認、三 worktree symbolic-ref 皆非活躍前端 branch）。
2. `git tag -a backup/w7.1-<date>` 破壞性移動前快照。
3. **一 service 一 PR**（163 py + ~250 fe 檔，禁單一 mega-commit）：先搬 leaf packages/services，最後搬 `apps/web_console`（frontend）與 `apps/api`。
4. 每 PR 後：`pytest` + `lint-imports`（契約 root_package 改 `quant_platform`）+ `check_openapi_drift.py`（更新 BACKEND_DIR 路徑）全綠。
5. `backtest_platform.*` import path 留 re-export shim 一段過渡期，尤其 `backtest_platform.api.app:app`（uvicorn entrypoint）。
6. `pyproject.toml` packaging 改指 `quant_platform/`。

見 `dev_docs/product_repositioning/18_refactor_wbs.md` W7.1 + ADR-R05。
