# SPEC-02：策略資產包（Strategy Package）、動態參數與最佳化 UI

> 狀態: Accepted | 日期: 2026-07-05 | 關聯: ADR-008、ADR-R06、ADR-006、ADR-007、ADR-029
>
> 觸發來源: 「新建回測」頁面把策略參數寫死/退回 raw JSON，無法支援每個策略不同參數，也無法表達「策略不是單一 Python 腳本，而是一個包含設定、研究 workflow、測試與文件的完整資料夾」。

---

## 1. 問題陳述

目前 New Run 的產品邏輯仍偏「對已註冊策略送一包 JSON」，而策略中心也只呈現策略名與 `config_schema`：

- 策略參數主路徑是 raw JSON；使用者必須知道 Python config 欄位名。
- 每個策略的 `config_model` 不同，但 UI 沒有依 `GET /strategies` 的 `config_schema` 產生表單。
- 參數最佳化已有後端 `DOEConfig` / `run_doe`，但 UI 不知道每個策略的預設 grid，也不能覆寫 grid 後送 workflow。
- 策略實體其實是一個 folder/package：`strategy.py` 放 alpha 邏輯、`runner.py` 做平台 adapter、`research_config.py` 宣告 DOE/GO/Truth/Paper workflow、測試與 README 承載契約；前端沒有一個「策略資產包」read model 可以理解這些互動面。
- 若把策略撰寫做成瀏覽器 IDE，會引入 sandbox、檔案管理、依賴、測試、版本控制與安全成本；對 single-user EOD 平台不是第一優先。

核心決策：**策略邏輯由 repo 內 Strategy Package 承載，可由 AI coding/IDE 協作產生；UI 只透過後端 read model 互動：看 package 結構、填 config、覆寫 DOE grid、啟動 workflow、閱讀報表。**

---

## 2. 目標

1. 定義 Strategy Package folder contract，讓「新增策略」不是貼一段 script，而是新增一個自包含策略資料夾。
2. 新增策略資產包 descriptor：`GET /strategies/{strategy}/asset`，供前端策略中心呈現 package 結構與互動端點。
3. New Run 不寫死策略參數；選策略後由 `config_schema` 動態 render 單次 run 參數表單。
4. raw JSON params 仍保留為 advanced fallback，但不是主要路徑。
5. 新增策略最佳化 schema read model：`GET /strategies/{strategy}/optimization-schema`。
6. 最佳化 UI 讀每個策略 `research_config.py` 的 `DOE.grid`，顯示/覆寫 grid 與 `n_configs`。
7. UI 送 `POST /research/workflows/doe`，body 使用 `{strategy, overrides: {grid}}`，由後端既有 `run_doe` 執行。

---

## 3. 非目標

- 本切片不做瀏覽器 Python IDE / Monaco strategy editor。
- 本切片不讓前端提交任意 Python 程式碼給 backend process 直接執行。
- 本切片不新增完整 DOE leaderboard / heatmap；job result 展示另列後續工作。
- 本切片不改策略契約本身；仍使用 `StrategyRunner.config_model`、`StrategyRunner.run(...) -> StrategyRun`。
- 本切片不要求所有舊策略補 README；descriptor 只呈現 present/missing。

---

## 4. Strategy Package Contract

一個策略是一個 Python package，而不是單檔 script：

```text
strategies/<strategy_pkg>/
├── __init__.py
├── strategy.py          # alpha / signal / portfolio construction 純邏輯；無 UI / broker / DB
├── runner.py            # @register_strategy("<strategy_id>")；平台 adapter；宣告 title/config_model/gate
├── research_config.py   # DOE / GO_GATES / TRUTH_GATE / PAPER_REPLAY / UNIVERSE
├── README.md            # optional：策略假設、資料需求、風險、使用方式
└── tests/...            # package 對應測試（repo tests/strategies/<strategy_pkg>/）
```

前端不讀檔案系統、不理解 Python module；前端只消費 backend descriptor：

| Package 成員 | 後端責任 | 前端互動 |
| :--- | :--- | :--- |
| `runner.py` | 註冊 strategy id，提供 title/config schema/gate | 策略下拉、參數表單、策略資產頁 header |
| `strategy.py` | 實作 alpha 邏輯 | 不直接編輯；顯示為 package file present |
| `research_config.py` | 宣告 DOE/GO/Truth/Paper workflows | 最佳化 grid、workflow availability |
| tests | conformance / unit tests | 顯示 authoring checklist；未來可接測試 job |
| README | human-readable premise | 策略資產頁 authoring hint |

### 4.1 Strategy asset descriptor

新增：

`GET /strategies/{strategy}/asset`

```json
{
  "strategy": "momentum",
  "package": "backtest_platform.strategies.momentum",
  "package_path": "src/backtest_platform/strategies/momentum",
  "files": [
    {"path": "strategy.py", "role": "alpha_logic", "present": true},
    {"path": "runner.py", "role": "platform_adapter", "present": true},
    {"path": "research_config.py", "role": "research_workflows", "present": true},
    {"path": "README.md", "role": "human_docs", "present": false}
  ],
  "workflows": ["doe", "go_gates", "truth_gate"],
  "endpoints": {
    "run": "/runs",
    "optimization_schema": "/strategies/momentum/optimization-schema",
    "workflow_submit": "/research/workflows/doe"
  }
}
```

未知策略 → 404。

---

## 5. 互動契約

### 5.1 Strategy catalog

既有 `GET /strategies` 保持：

```json
{
  "name": "momentum",
  "title": "12-1 Cross-sectional Momentum",
  "description": "...",
  "config_schema": {
    "properties": {
      "lookback_days": {"type": "integer", "default": 252, "minimum": 40}
    }
  }
}
```

前端表單規則：

| JSON Schema | UI |
| :--- | :--- |
| `type=integer/number` | number input |
| `enum` / `anyOf const` | select |
| `type=boolean` | checkbox |
| `type=string` | text input |
| `anyOf: [T, null]` | optional control |

### 5.2 Optimization schema

新增：

`GET /strategies/{strategy}/optimization-schema`

成功：

```json
{
  "strategy": "momentum",
  "config_schema": {},
  "optimization": {
    "workflow": "doe",
    "grid": {"lookback_days": [126, 252], "skip_days": [0, 21]},
    "n_configs": 4,
    "is_start": "2020-01-01",
    "is_end": "2024-12-31",
    "symbols_count": 3,
    "symbols_preview": ["2330", "2317", "2454"]
  }
}
```

沒有 DOE 宣告時仍 200：

```json
{
  "strategy": "template",
  "config_schema": {},
  "optimization": null
}
```

未知策略 → 404。

### 5.3 DOE submission

沿用既有：

`POST /research/workflows/doe`

```json
{
  "strategy": "momentum",
  "overrides": {
    "grid": {"lookback_days": [126, 252], "skip_days": [0, 21]}
  }
}
```

後端在 HTTP edge 用 `revalidate_with_overrides` 驗證；未知欄位、錯誤型別、非法 window → 422。

---

## 6. 典型互動流程

### 6.1 AI coding / 外部 IDE 新增策略

1. 使用者用 Claude Code/Codex/IDE 複製 `_template` 或建立 `strategies/<pkg>/`。
2. 實作 `strategy.py`、`runner.py`、`research_config.py` 與測試。
3. 後端啟動/重新載入後，`GET /strategies` 出現新策略。
4. 前端策略中心呼叫 `/strategies/{strategy}/asset` 顯示 package 結構與 workflow readiness。
5. New Run 依 `config_schema` 產生表單；Optimization 依 `DOE.grid` 產生 grid editor。

### 6.2 前端回測/最佳化

```text
GET /strategies
  → user selects strategy
GET /strategies/{strategy}/asset
  → Strategy Hub shows package readiness
GET /strategies/{strategy}/optimization-schema
  → Optimization grid editor
POST /runs
  → single backtest
POST /research/workflows/doe
  → DOE optimization job
```

---

## 7. 落地切片

### Slice 1 — Read model + docs

- [x] SPEC-02
- [x] ADR-008
- [x] API design / WBS / IA 文件同步
- [x] `GET /strategies/{strategy}/asset`
- [x] `GET /strategies/{strategy}/optimization-schema`

### Slice 2 — New Run dynamic params

- [x] 前端依 `config_schema` 產生單次回測 params。
- [x] 提交 body 的 `params` 由 guided form 產生；advanced JSON 可覆寫/補充。
- [x] 測試 dynamic integer 欄位送出正確型別；enum/boolean 由同一 renderer 分支支援。

### Slice 3 — Optimization UI

- [x] 前端讀 optimization schema，顯示 DOE grid。
- [x] 使用者可改逗號值，UI 顯示 grid cardinality。
- [x] 提交 `POST /research/workflows/doe` 並顯示 job id。

### Slice 4 — Result UX（後續）

- [ ] workflow job status/result 統一查詢端點。
- [ ] DOE leaderboard / heatmap / run drilldown。
