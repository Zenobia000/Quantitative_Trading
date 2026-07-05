# API 設計規範 - 個人級 EOD 量化交易平台

> 版本: v1.0 | 日期: 2026-07-05 | 狀態: Golden baseline

## 1. 設計約定

| 項目 | 規範 |
| :--- | :--- |
| 風格 | REST for control plane；append-only events for trading/audit |
| Base URL | `/api/v1` |
| 格式 | JSON UTF-8；large artifacts 使用 object store reference |
| 欄位命名 | `snake_case` |
| 時間 | ISO 8601 UTC；交易日另用 `trade_date` |
| 認證 | local session / bearer token；broker credential 不經前端 |
| 冪等 | mutation 必須支援 `Idempotency-Key` |

## 2. 通用錯誤

```json
{
  "error": {
    "type": "invalid_request_error",
    "code": "risk_gate_blocked",
    "message": "order intent blocked by concentration_limit",
    "param": "order_intent_id",
    "request_id": "req_..."
  }
}
```

| code | HTTP | 說明 |
| :--- | :--- | :--- |
| `resource_not_found` | 404 | 資源不存在 |
| `validation_failed` | 400 | schema 或 business validation 失敗 |
| `release_not_approved` | 409 | 未通過 Governance |
| `risk_gate_blocked` | 409 | Risk 決策阻擋 |
| `reconciliation_required` | 423 | 對帳未解除，交易鎖定 |
| `external_service_failed` | 502 | 外部資料/券商/推送失敗 |

## 3. 核心 REST 資源

### Data Bundles

| Method | Path | 說明 |
| :--- | :--- | :--- |
| POST | `/data-bundles/build` | 建立 EOD bundle |
| GET | `/data-bundles/{bundle_ref}` | 取得 bundle manifest |
| GET | `/data-bundles` | 列表與 coverage |

### Named Universes（ADR-007，實作路徑 `/system/*`）

具名股票池 = 可被 New Run 選用、可被策略以 N:1 引用的 survivorship-clean 母體。真相源 `specs/SPEC-01`。

| Method | Path | 說明 |
| :--- | :--- | :--- |
| GET | `/system/universes` | 列出具名 universe（掃 `universe_manifest.json` 投影；degrade→typed-empty，`data_source=parquet_scan`）|
| POST | `/system/universe/build` | 觸發 survivorship-clean universe build（async job，ADR-032）|

`UniverseRow`：`id` / `name` / `symbols_count` / `span_start` / `span_end` / `top_n` / `min_turnover` / `strategies[]`（N:1 讀相容舊 `strategy: str`）/ `cache_dir` / `generated_at`。

### Research Runs

| Method | Path | 說明 |
| :--- | :--- | :--- |
| POST | `/research-runs` | 建立 research/backtest run |
| GET | `/research-runs/{run_id}` | 取得 run 狀態與結果 |
| GET | `/research-runs/{run_id}/report` | 取得 report pack |

> **股票池選擇（ADR-007 Slice 2，實作 `POST /runs`）**：body 的 `stocks` 改選填，新增 `universe`（具名池 id）。伺服端解析精度序 `stocks` > `universe` > 系統 `DEFAULT_UNIVERSE`；未知 universe → 422。策略**不必**手打股票池——省略即用預設。

### Strategy Definitions

| Method | Path | 說明 |
| :--- | :--- | :--- |
| POST | `/strategy-definitions` | 建立策略定義草稿 |
| GET | `/strategy-definitions/{strategy_id}` | 取得策略定義 |
| POST | `/strategy-definitions/{strategy_id}/freeze` | 凍結版本 |

### Governance

| Method | Path | 說明 |
| :--- | :--- | :--- |
| POST | `/release-candidates` | 建立發布候選 |
| POST | `/release-candidates/{id}/approve` | 自我核准 |
| POST | `/release-candidates/{id}/reject` | 拒絕並記錄原因 |
| GET | `/approved-packages/{package_id}` | 取得 approved package |

### Trading / Risk / Execution

| Method | Path | 說明 |
| :--- | :--- | :--- |
| POST | `/order-intents/preview` | 根據 target portfolio 預覽 order intent |
| POST | `/risk-decisions/evaluate` | 評估 order intent |
| POST | `/execution/submit` | 提交 risk-approved order intent |
| POST | `/execution/kill-switch` | 停用策略或全域交易 |
| GET | `/fills` | 查詢 fill |
| POST | `/reconciliation/run` | 執行對帳 |

## 4. Event Contracts

| Event | Producer | Consumer |
| :--- | :--- | :--- |
| `DataBundleBuilt` | Data Worker | Research |
| `ResearchRunCompleted` | Research Worker | Governance |
| `StrategyApproved` | Governance | Strategy Runtime |
| `OrderIntentCreated` | Portfolio | Risk |
| `RiskDecisionMade` | Risk | Execution / Audit |
| `BrokerFillReceived` | Execution | Position / Monitoring |
| `ReconciliationFailed` | Monitoring | Risk / Governance / Alert |

## 5. 核心資料模型

### `StrategyDefinition`

```json
{
  "strategy_id": "str_revenue_momentum",
  "version": "1.0.0",
  "universe": {"market": "TW", "filters": []},
  "entry_rules": [],
  "exit_rules": [],
  "rebalance": {"frequency": "monthly"},
  "cost_model": {"commission_bps": 14.25, "slippage_bps": 30},
  "risk_assumptions": {},
  "created_at": "2026-07-05T00:00:00Z"
}
```

### `TargetPortfolio`

```json
{
  "strategy_id": "str_revenue_momentum",
  "as_of": "2026-07-05",
  "cash_weight": 0.2,
  "positions": [
    {"symbol": "2330.TW", "target_weight": 0.15, "reason": "rank_1"}
  ]
}
```

### `RiskDecision`

```json
{
  "order_intent_id": "oi_...",
  "decision": "Pass",
  "rule_results": [
    {"rule_id": "single_position_limit", "result": "pass"}
  ],
  "created_at": "2026-07-05T00:00:00Z"
}
```

