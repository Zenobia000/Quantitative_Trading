# ADR-R04: 建立 packages/contracts 作為跨 service published language

> 狀態: Accepted (partial — JSON 契約已落地；Python schema 搬移待續) | 日期: 2026-07-05 | 決策者: refactor 任務

## 背景

Golden 08/09 要求 contract-as-truth 與 inward-only import 方向。但今日 `EvaluationResult`、`TargetPortfolio`、`DataBundle` schema 困在 `api/response_models`，`DataFeed` Protocol（ADR-035 seam）困在 `adapters/data_feed/base.py`——跨 service 溝通被迫走內部 module import。

## 決策

建 `packages/contracts/{schemas,events,openapi,examples}`，把 DataFeed port、EvaluationResult、TargetPortfolio、DataBundle 等跨層 published-language 移入。跨 service 溝通走 contracts，不走內部 module import。

## 落地（W1.2）

1. 建 `packages/contracts` scaffold。
2. 搬 `DataFeed` Protocol → `contracts/`（port 屬 shared contract）。
3. 搬 `EvaluationResult`/`TargetPortfolio` schema 出 `api/response_models` → `contracts/schemas`。
4. 保留舊路徑 re-export 一段過渡期，避免破壞既有 import。

## 已落地（W1.2a，2026-07-05）

- 建 `packages/contracts/{schemas,examples}`，還原 `077431f` 文件重建時誤刪的 8 個契約檔（evaluation_profile.schema.json + 6 example + README）至 golden 位置。
- repoint `test_profiles.py` 的 contract-as-truth 測試到新路徑——修復自 `077431f` 起的 pre-existing 紅燈（now 585 passed / 0 failed）。

## 待續（W1.2b）

- 搬 `DataFeed` Protocol（`adapters/data_feed/base.py`）+ `EvaluationResult`/`TargetPortfolio`（`api/response_models`）Python schema 進 contracts。**注意 OpenAPI drift**：搬 response_models 需同步 regenerate `frontend/openapi.json` + `api.gen.ts`（走 `scripts/check_openapi_drift.py` gate）。

## 後果

- 消除 cross-service 對內部實作的耦合。
- 為 W6（api 拆解）與 W7（monorepo）鋪路——`packages/contracts` 位置已就定位。
