# ADR-R02: 將 Governance & Release 抽出 research package

> 狀態: Accepted | 日期: 2026-07-05 | 決策者: refactor 任務

## 背景

`research/` 內含 `promotion_service.py`、`promotion_store.py`、`watch_registry.py`、`live_oos_queue.py`、`live_oos_consumer.py`——這是 draft→paper→live 發布階梯、Paper-Watch 准入、live-OOS 人工閘。它們 gate 部署/准入，**不是** alpha research，屬 golden 第 3 層 Governance & Release（05/07/09）。雖無 broker import，其位置違反目標 service 分工。

## 決策

將上述模組從 `research/` 抽到新的 `backtest_platform/governance/` package（未來 `services/governance_release`）。research 經 contract（StrategyDefinition/TargetPortfolio）餵給 governance，governance 決定 release；**方向單一**：research 不得 import governance。

## 落地（W2.1–W2.3）

1. 建 `governance/` package，搬 5 模組；`orchestration/after_close.py` 對 `watch_registry` 的引用改走 re-export shim 或 governance port，保住 daemon。
2. 重指 `api/routers/research_promote.py` + `watch.py` 及測試到 governance；驗 OpenAPI URL 不變（既有 frontend redirect 保路徑）。
3. 加 import-linter 契約：research ⊄ governance。

## 後果

- research_validation 不再擁有准入控制狀態。
- `watch_registry` 抽離後，research⊄runtime 亦可補上（其唯一 runtime import 隨之離開 research）。
- 相關風險：daemon 為 load-bearing，搬移前打 backup tag、端到端驗證。
