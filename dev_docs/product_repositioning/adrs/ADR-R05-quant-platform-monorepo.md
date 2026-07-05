# ADR-R05: 採用 quant_platform monorepo 結構（apps/packages/services）

> 狀態: Proposed | 日期: 2026-07-05 | 決策者: refactor 任務

## 背景

Golden 08 定義目標頂層結構 `quant_platform/{apps,packages,services}`。現況為單一 `backtest_platform` package + 平行的 `frontend/`、`scripts/`、`deploy/`、散落的 research-note markdown。

## 決策

逐步收斂到 golden 頂層結構：

- `apps/{api,web_console,workers}` — `frontend/` 成為 `apps/web_console`。
- `packages/{domain,application,adapters,infrastructure,contracts}`。
- 八個 `services/`：data_platform、research_validation、governance_release、strategy_runtime、portfolio_engine、risk_gate、execution_gateway、monitoring_ops。

## 落地策略（W7，延後 M1–M6）

先建 scaffold（空 service 目錄 + README），讓最終物理搬移**機械化、可 review**，並在綠色 fitness-function wall + backup tag 之後執行；**一 service 一 PR**，不做單一 mega-commit（163 py + ~250 fe 檔會違反 PR size 規則）。

## 後果

- 短期維持 `backtest_platform` import path，避免 big-bang 破壞。
- monorepo 搬移為 XL、worktree 隔離波次，`session_actionable=false`。
- 狀態 Proposed，待 scaffold（W7.1 前置）落地後逐服務轉 Accepted。
