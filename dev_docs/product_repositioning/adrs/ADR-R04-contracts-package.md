# ADR-R04: 建立 packages/contracts 作為跨 service published language

> 狀態: Proposed | 日期: 2026-07-05 | 決策者: refactor 任務

## 背景

Golden 08/09 要求 contract-as-truth 與 inward-only import 方向。但今日 `EvaluationResult`、`TargetPortfolio`、`DataBundle` schema 困在 `api/response_models`，`DataFeed` Protocol（ADR-035 seam）困在 `adapters/data_feed/base.py`——跨 service 溝通被迫走內部 module import。

## 決策

建 `packages/contracts/{schemas,events,openapi,examples}`，把 DataFeed port、EvaluationResult、TargetPortfolio、DataBundle 等跨層 published-language 移入。跨 service 溝通走 contracts，不走內部 module import。

## 落地（W1.2）

1. 建 `packages/contracts` scaffold。
2. 搬 `DataFeed` Protocol → `contracts/`（port 屬 shared contract）。
3. 搬 `EvaluationResult`/`TargetPortfolio` schema 出 `api/response_models` → `contracts/schemas`。
4. 保留舊路徑 re-export 一段過渡期，避免破壞既有 import。

## 後果

- 消除 cross-service 對內部實作的耦合。
- 為 W6（api 拆解）與 W7（monorepo）鋪路。
- 狀態暫定 Proposed，待 W1.2 執行後轉 Accepted。
