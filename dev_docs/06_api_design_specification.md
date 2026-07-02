# API 設計規範 — backtest_platform

> **範圍：本文是 CLI + Python API 規範。** HTTP/REST 契約的唯一真相源是 [25_fe_be_rest_contract.md](./25_fe_be_rest_contract.md) + FastAPI OpenAPI（`/docs`）；§9 僅為已實作 HTTP 端點的便覽，任何歧異以 doc 25 與 OpenAPI 為準。

---

## 1. API 形式

提供三種介面：

1. **CLI（Click）** — 端到端操作：ETL（`finmind_etl`）、zipline 回測（`zipline_adapter`：`ingest` / `backtest-run` / `list-bundles`）、每日管線（`orchestration.cli`）、**研究迴圈與工作流 `research.cli`**（§3.5：`run-is` / `runs` / `sweep` / `compare` / `validate` / `promote-check` / `validate-strategy` / `doe` / `go-gates` / `truth-gate` / `build-universe` / `paper-replay`）
2. **Python API** — 程式內呼叫（pure functions + Pydantic models）
3. **HTTP API（FastAPI）** — 研究迴圈 + 驗證後端的 HTTP 投影（runs ledger / gate 審判庭 / metrics / strategies / research workflows），已實作端點見 §9。

---

## 2. 設計約定

| 項目 | 規範 |
| :--- | :--- |
| **CLI 風格** | `python -m backtest_platform.<module>` + Click subcommands |
| **Python 命名** | `snake_case` 函式 / `PascalCase` 類別 / `UPPER_CASE` 常數 |
| **時間格式** | `date` / `datetime` ISO 8601；CLI 用 `YYYY-MM-DD` |
| **stock_id** | TEXT（如 "2330"），不轉 int（怕 0050 變 50） |
| **金額單位** | NTD 元；張數單位 = 1000 股 |
| **錯誤** | 拋 `ValueError`（業務）/ `RuntimeError`（系統）；CLI 用 Click 的 exit codes |
| **日誌** | Loguru，格式 `loguru.format("{time} {level} {message}")` |
| **idempotency** | ETL / DB writer 必須 idempotent（重跑結果一致） |

---

## 3. CLI 介面

### 3.1 `finmind_etl` — 資料抓取

```bash
python -m backtest_platform.data.finmind_etl \
    --stock-id 2330 \
    --start 2024-01-01 \
    --end 2024-12-31 \
    --output data/parquet \
    [--db | --no-db] \
    [--token <FINMIND_TOKEN>]
```

**選項**：

| 選項 | 必需 | 型別 | 預設 | 描述 |
| :--- | :---: | :--- | :--- | :--- |
| `--stock-id` | ✅ | str | — | 股票代號，如 "2330" |
| `--start` | ✅ | YYYY-MM-DD | — | 起始日 |
| `--end` | ✅ | YYYY-MM-DD | — | 結束日 |
| `--output` | ❌ | Path | None | parquet 輸出目錄；省略則 dry-run |
| `--db` | ❌ | bool | False | 同時 upsert TimescaleDB |
| `--token` | ❌ | str | env FINMIND_TOKEN | FinMind API token |

**輸出**：
- `--output` 提供時：三個 parquet（`daily_bars__<id>.parquet`、`institutional__<id>.parquet`、`broker_chips__<id>.parquet`）
- `--db` 提供時：寫入 TimescaleDB
- stdout: loguru log 含 rows 數

**退出碼**：
- 0：成功
- 1：FinMind API 失敗
- 2：DB 連線失敗（僅 --db 時）

### 3.2 `pipeline run` — 端到端 smoke

```bash
python -m backtest_platform.pipeline run \
    --stock-id 2330 \
    --start 2023-01-01 \
    --end 2024-12-31 \
    [--parquet-dir data/parquet] \
    [--report-dir reports]
```

**輸出**：
- `reports/calendar__<id>__<start>__<end>.csv` — 每日 scores + states + action
- stdout：last 20 rows + summary stats

### 3.3 `engines.zipline_adapter.cli` — zipline-reloaded 回測引擎（M2，ADR-013）

Click group，子命令 `ingest` / `backtest-run` / `list-bundles`。執行需帶 extra：
`uv run --extra sprint1 --extra dev python -m backtest_platform.engines.zipline_adapter.cli <cmd>`。

| 子命令 | 用途 | 主要 options |
| :--- | :--- | :--- |
| `ingest` | 批次抓 universe 進 parquet cache（FinMind → `data/parquet/`） | `--start` / `--end`（必填）、`--stocks`（逗號覆蓋，預設 `DEFAULT_UNIVERSE` 10 檔）、`--cache-dir`、`--dry-run` |
| `backtest-run` | 跑四層共振 Algorithm 回測 | `--stocks`（必填）、`--start` / `--end`、`--capital-base`、`--tearsheet`、`--discord-notify` |
| `list-bundles` | 列出已註冊 zipline bundle（`register()` side-effect sanity check） | — |

`ingest` exit code：全 symbol 失敗 → 1；部分失敗 → 0 + 警告（partial-universe 回測仍可進行，per `ingest_universe` 契約）。
完整流程見 [runbooks/m2_universe_ingest_runbook.md](./runbooks/m2_universe_ingest_runbook.md)。

### 3.4 後續 CLI（M2+）

| 指令 | 階段 | 用途 |
| :--- | :---: | :--- |
| `python -m backtest_platform.data.universe build` | M2 | 建立 universe snapshot |
| `python -m backtest_platform.engines.vectorbt_runner sweep` | M3 | 參數網格 |
| `python -m backtest_platform.validation.pbo compute` | M3 | PBO/DSR 計算 |
| `python -m backtest_platform.validation.wfa walk` | M3 | Walk-Forward |
| `python -m backtest_platform.live.paper_trader run` | M4 | 紙上交易 |

---

### 3.5 `research.cli` — 研究迴圈 CLI（v0.1–v0.6）

把「手寫 script 半天」收成「一行 run + gate 自動逐條綠紅 + 落 runs ledger」的研究迴圈入口。

```bash
# 跑一次 IS run（強制 hypothesis 預登記）→ 判 gate → 落 runs ledger
uv run python -m backtest_platform.research.cli run-is \
    --strategy four_layer --params '{}' --hypothesis "雙窗是否同號為正" \
    --stocks 2330,1101,1303 --start 2020-01-01 --end 2024-12-31 \
    [--tearsheet] [--tearsheet-dir reports/tearsheets]   # 額外輸出 quantstats HTML

uv run python -m backtest_platform.research.cli runs                       # 列出 ledger
uv run python -m backtest_platform.research.cli sweep --strategy four_layer --base-params '{}' \
    --grid "entry_min_layers=3,4;entry_confirm_days=1,2" \
    --stocks 2330,1101 --start 2020-01-01 --end 2024-12-31                 # 全網格 CSV
uv run python -m backtest_platform.research.cli compare --baseline <run_id>  # 多 run delta
uv run python -m backtest_platform.research.cli validate --run-id <run_id>   # 工作流 gate
uv run python -m backtest_platform.research.cli promote-check --run-id <run_id>  # 晉升資格（唯讀）
```

| 子命令 | 用途 | 後端 |
| :--- | :--- | :--- |
| `run-is` | 跑 IS sim → 判 gate → 落 ledger；`--tearsheet` 額外出 quantstats HTML（需 `validation` extra） | `is_harness.run_and_judge_with_returns` + `tearsheet.write_tearsheet` |
| `runs` | 列出 runs ledger（run_id / strategy / gate / hypothesis） | `runs_store.read_runs` |
| `sweep` | 參數網格展開 → 跑每個 → 輸出**全網格** CSV（防 cherry-pick） | `sweep.run_sweep` |
| `compare` | 多 run baseline delta + 排名 + 同號一致性 | `compare.compare_runs` |
| `validate` | 把 ledger 內某 run 推進 IS→WFA→OOS **工作流 gate**（IS 階段）：PASS→IS_PASS 解鎖 WFA，並回報 OOS sealed-vault 狀態（IS+WFA 通過前 OOS 封存，防 look-ahead leak） | `validation.gate_machine.ValidationGate` |
| `promote-check` | **唯讀晉升閘**：讀某 run 的 `validation_status`（顯式欄優先，否則由 metrics 推導 IS 狀態）→ 僅 `APPROVED`（IS→WFA→OOS→approve 全通過）才 ELIGIBLE，否則列出待完成階段。防未驗證策略上線 | `validation.gate_machine.GateState` + `ValidationGate` |
| `validate-strategy` | conformance gate：驗任一已註冊策略 runner 是否符合契約（`--list` 列全部，ADR-028）| `strategies.conformance.check_strategy` |
| `doe` | DOE 參數網格掃描（讀 `research_config.DOE`）；`--dry-run`/`--is-start`/`--is-end`/`--out-csv`（ADR-029）| `research.workflows.doe.run_doe` |
| `go-gates` | WFA + PBO GO 閘（讀 `research_config.GO_GATES`）| `research.workflows.go_gates.run_go_gates` |
| `truth-gate` | ADR-025 兩段式真偽閘（讀 `research_config.TRUTH_GATE`）| `research.workflows.truth_gate.run_truth_gate` |
| `build-universe` | survivorship-clean FinLab universe 建構（讀 `research_config.UNIVERSE`，ADR-032）；`--dry-run` | `research.workflows.universe.run_build_universe` |
| `paper-replay` | paper 重放 sim（讀 `research_config.PAPER_REPLAY`）| `research.workflows.paper_replay.run_paper_replay_workflow` |

> `run-is`／`validate`／`promote-check` 區別：`run-is` 是**唯讀審判庭**（`evaluate_gate` 逐條綠紅）；`validate` 是**有狀態工作流 gate**（`ValidationGate`，強制 IS→WFA→OOS 不可逆推進 + OOS 封存）；`promote-check` 是**唯讀晉升資格查詢**（不推進狀態，只回報距 APPROVED 還缺哪些階段）。

---

### 3.6 `orchestration.cli` — 每日管線排程（v0.7，WBS 7.D）

把跨波次建的模組（ETL → signals → risk gate → orders → log）串成一次可操作的每日 run 的 staged-flow 引擎。**fail-fast**（任一 stage 失敗即停並留完整 audit trail）、collaborator 經 `FlowContext.config` 注入（可單元測試）、**Prefect-optional**（裝了 prefect 走 `@flow` 排程，沒裝則 inline 跑，prefect 非硬依賴）。

```bash
uv run python -m backtest_platform.orchestration.cli run --dry-run   # no-op demo 管線（安全）
uv run python -m backtest_platform.orchestration.cli run --real      # 套 build_daily_stages（需注入 collaborators）
uv run python -m backtest_platform.orchestration.cli list-stages     # 列出 ETL→signals→risk→orders→log
```

| 子命令 | 用途 | 後端 |
| :--- | :--- | :--- |
| `run --dry-run` | 跑 no-op demo 管線（不碰資料/broker/網路）→ flow engine smoke test | `daily_flow.run_flow` + `demo_stages` |
| `run --real` | 跑 ETL→signals→risk→orders→log 正式管線；collaborator 未注入時乾淨回報缺哪個（不 crash），real 接線見 7.D.3 | `daily_flow.build_daily_stages` |
| `list-stages` | 列出每日管線 stage 順序 | `daily_flow.build_daily_stages` |

---

## 4. Python API

### 4.1 `config.strategy_config`

```python
from backtest_platform.config.strategy_config import StrategyConfig, DEFAULT_CONFIG

config = StrategyConfig()  # 用 v2.md 預設值
config = StrategyConfig(box_period=90, strong_buy_threshold=6)  # override
config.cost_round_rate  # 衍生屬性 (property)

# 修改：必須建新 instance
new_config = config.model_copy(update={"box_period": 90})

# 序列化（供 audit trail）
config.model_dump_json()
```

**前置條件**：
- `warning_threshold < strong_buy_threshold`
- `add_score_threshold >= strong_buy_threshold`
- 所有費率 ≥ 0

**後置條件**：
- frozen，不可修改 instance
- `extra="forbid"`，未知欄位拋例外

### 4.2 `data.finmind_etl`

```python
from backtest_platform.data.finmind_etl import fetch_bundle, write_parquet
from datetime import date

bundle = fetch_bundle(
    stock_id="2330",
    start=date(2024, 1, 1),
    end=date(2024, 12, 31),
    token=None,  # 從 env 讀
    rate_limit_seconds=0.6,  # FinMind 免費版限速
    apply_adjustment=True,
)

# bundle: ETLBundle
# .daily_bars / .institutional / .broker_chips 都是 pd.DataFrame
# .merged() 返回 join 後的 DataFrame

paths = write_parquet(bundle, Path("data/parquet"))
```

### 4.3 `data.schemas.ETLBundle`

```python
class ETLBundle(BaseModel):
    stock_id: str
    start_date: date
    end_date: date
    daily_bars: pd.DataFrame
    institutional: pd.DataFrame
    broker_chips: pd.DataFrame

    def merged(self) -> pd.DataFrame:
        """Left-join 三表，缺值補 0"""
```

### 4.4 `data.universe`

```python
from backtest_platform.data.universe import apply_filters, survivors, UniverseConfig

config = UniverseConfig(min_market_cap=5e9, min_avg_volume_lots=1000)
filtered = apply_filters(metadata_df, config, snapshot_date=date.today())
pool = survivors(filtered)  # excluded_reason == ""

# 診斷
from backtest_platform.data.universe import rejection_summary
print(rejection_summary(filtered))
# attention_stock      120
# market_cap_too_low    80
# ...
```

### 4.5 `data.db_writer`

```python
from backtest_platform.data.db_writer import upsert_bundle, DBConfig

cfg = DBConfig.from_env()
counts = upsert_bundle(bundle, cfg)
# counts: {"daily_bars": 250, "institutional_flows": 250, "broker_chips": 250}
```

### 4.6 `strategies.four_layer_resonance.scoring`

> **2026-05-31 import path 變更**：原 `backtest_platform.strategy.scoring` 已搬到 `backtest_platform.strategies.four_layer_resonance.scoring`（見 ADR-008 多策略 namespace、`08_project_structure_guide.md` v1.1）。

```python
from backtest_platform.strategies.four_layer_resonance.scoring import compute_scores, REQUIRED_COLUMNS

scored = compute_scores(merged_df, config)
# scored 新增欄位：
#   structure_score, direction_score, chip_score, momentum_score, total_score
#   box_upper, box_lower, box_mid, body_high, body_low
#   k, d, dif_sl, osc_d, rsi_5, rsi_10, ma5, ma10, ma20, ema5, ema10
#   chip_total, net_volume, chip_ratio
```

**前置條件**：
- 輸入 DataFrame 必須含 `REQUIRED_COLUMNS`（14 欄）
- 按 date 升序排列、無重複日期

**後置條件**：
- 暖機期（前 `box_period` 列）的 scores 為 NaN
- 所有 score 欄位落在文件範圍內（0–2 / -1 ~ 2）

### 4.7 `strategies.four_layer_resonance.signals`

```python
from backtest_platform.strategies.four_layer_resonance.signals import (
    compute_states, compute_signals, evaluate_bar, EvaluateBar, SIGNAL_PRIORITY
)

# 雙模式：

# Mode 1: vectorized walk（vectorbt 用）
signaled = compute_signals(scored, config)
# signaled 新增欄位：
#   state_strong_buy, state_hold, state_warning, state_flameout
#   signal_stoploss, signal_exit, signal_takeprofit, signal_reduce,
#   signal_add, signal_buy, signal_hold
#   action ("buy" / "stoploss" / ... / "none")
#   in_position, entry_cost_price

# Mode 2: per-bar（rqalpha 用）
bar = EvaluateBar(
    in_position=1, entry_cost_price=100.0,
    close=105.0, ...
)
action = evaluate_bar(bar, config)
# action: SignalName = Literal["stoploss", "exit", ..., "buy", "hold", "none"]
```

**優先序**：`SIGNAL_PRIORITY = ("stoploss", "exit", "takeprofit", "reduce", "add", "buy", "hold")`

---

## 5. 錯誤處理規範

### 業務錯誤（ValueError）

```python
compute_scores(df_missing_col, config)
# ValueError: compute_scores missing required columns: ['foreign_buy']

StrategyConfig(warning_threshold=5, strong_buy_threshold=3)
# ValidationError: warning_threshold must be < strong_buy_threshold
```

### 系統錯誤（RuntimeError / 第三方例外）

```python
fetch_bundle("INVALID", date(2024, 1, 1), date(2024, 12, 31))
# requests.HTTPError / FinMind 自身 exception
```

### 邊界處理

| 情境 | 行為 |
| :--- | :--- |
| FinMind 回空表 | `_normalize_*` 回 columns 完整的空 DataFrame，不拋例外 |
| `net_volume == 0` | 用 `ffill` 帶前一日值（mirror XScript） |
| `entry_cost_price == 0` | `net_profit_rate` 設 0，不算 ZeroDivisionError |
| 暖機未滿 | 對應 score 為 NaN，下游 `dropna` 處理 |

---

## 6. 資料模型

詳見 `data/schemas.py` 與 `docker/timescaledb/init.sql`。

### Pydantic Models

```python
class DailyBarRow(BaseModel):
    stock_id: str = Field(min_length=1, max_length=10)
    trade_date: date
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: NonNegativeInt
    adj_factor: float = Field(default=1.0, gt=0)

class InstitutionalRow(BaseModel):
    stock_id: str
    trade_date: date
    foreign_buy: int = 0
    trust_buy: int = 0
    dealer_buy: int = 0

class BrokerChipRow(BaseModel):
    stock_id: str
    trade_date: date
    top_broker_buy: int = 0
    key_broker_buy: int = 0
    gov_broker_buy: int = 0
    geo_broker_buy: int = 0
    day_trade_volume: NonNegativeInt = 0
    margin_offset_volume: NonNegativeInt = 0
```

### CLI calendar CSV 欄位

```
trade_date, close, structure_score, direction_score, chip_score, momentum_score,
total_score, state_strong_buy, state_hold, state_warning, state_flameout,
action, in_position
```

---

## 7. 版本控制

當前無 API 版本（內部專案）。M5 對外 HTTP API 時：
- URL 路徑：`/v1/...`
- 重大變更：升 v2，舊版保留 6 個月

---

## 8. 安全性

| 項目 | 處理 |
| :--- | :--- |
| FinMind token | 從 env 讀，不入 git |
| DB password | 從 env 讀；預設值故意設為 `change_me_in_production` |
| CLI 不接收 secrets | 一律從 env 或 `.env` 載入（避免歷史命令外洩） |
| Logging 不印 token | Loguru format 排除 sensitive fields |
| Shioaji credentials（M5） | KMS / 1Password CLI |

---

## 9. HTTP API（FastAPI）

> 本節是已實作 HTTP 端點的便覽（§9.3），**契約真相源是 [`25_fe_be_rest_contract.md`](./25_fe_be_rest_contract.md) + FastAPI OpenAPI（`/docs`）**，歧異以 doc 25 與 OpenAPI 為準。
> 模組：`src/backtest_platform/api/`（app 工廠 + router 群；薄轉接層，零業務邏輯）。

### 9.1 啟動

```bash
# 開發（自動 reload）
uv run uvicorn backtest_platform.api.app:app --reload --port 8000
# 互動式 OpenAPI 文件： http://localhost:8000/docs
```

執行需 `api` extra（`uv sync --extra api`：fastapi / uvicorn / httpx）。

### 9.2 統一回應信封（rules/patterns.md §API 回應格式）

每個端點都回傳相同形狀，連 4xx/5xx 也被 exception handler 重新包成信封（不會出現裸 `{"detail": ...}`）：

```json
{ "success": true, "data": { ... }, "error": null, "meta": { "total": 0, "page": 1, "limit": 50 } }
```

* `success`：布林狀態旗標
* `data`：酬載（錯誤時 `null`）
* `error`：成功時 `null`；錯誤時自 v1.0 起為結構化物件 `{code, message, detail}`（v0.6 為裸字串，向後相容升級，見 25 §2）
* `meta`：分頁等中繼資料（`total` / `page` / `limit`），非列表端點為 `null`

### 9.3 端點

| Method | Path | 用途 | 後端 |
| :--- | :--- | :--- | :--- |
| GET | `/health` | liveness + 版本 | — |
| GET | `/strategies` | 列出所有已註冊策略的 name/title/description/JSON-schema（ADR-028）| `strategies.protocol.describe_strategies` |

| GET | `/runs` | runs ledger 分頁列表（`?page=&limit=`） | `research.runs_store.read_runs` |
| GET | `/runs/compare` | 跨 run 比較（`?baseline=`：delta/rank/sign） | `research.compare.compare_runs` |
| GET | `/runs/{run_id}` | 單一 run 完整紀錄（未知→404） | `read_runs` |
| POST | `/runs` | 觸發一次 IS run（驗 RunConfig→判 gate→append，201） | `research.is_harness.run_and_judge` |
| GET | `/gate/spec` | 審判庭預設準則（ADR-016 K1/K2/K3 + ADR-019 health） | `validation.gate_state.DEFAULT_GATE` |
| POST | `/gate/evaluate` | 對任意 metrics dict 判 PASS/FAIL/INCOMPLETE | `evaluate_gate` |
| POST | `/metrics/summary` | 日報酬序列 → A/B/C 指標 | `validation.metrics` |
| POST | `/metrics/trades` | 交易清單 → E 指標（缺 key→400） | `validation.metrics` |
| GET | `/research/workflows/{strategy}` | 列該策略宣告的研究工作流（ADR-029；未宣告/未知→400） | `research.workflows.loader.list_workflow_configs` |
| POST | `/research/workflows/{workflow}` | 非同步排程研究工作流 job（doe/go_gates/truth_gate/paper_replay），回 202 `{job_id,status}`；未知 workflow→404、未知策略→400 | `jobs.submit` + `research.workflows.*` |

### 9.4 設計約束

* **薄轉接層**：router 只做請求驗證 + 序列化，邏輯全在 `research` / `validation` 純函式。
* **依賴注入**：runs ledger 路徑（`$BACKTEST_RUNS_PATH`）與重量級 executor 透過 FastAPI `Depends` 注入，測試以 temp ledger + stub executor 覆寫（hermetic，不碰 parquet/zipline）。
* **路由順序**：`/runs/compare` 宣告早於 `/runs/{run_id}`，避免 "compare" 被當成 run_id 吞掉。
* **邊界驗證**：所有 POST body 為 `extra="forbid"` 的 Pydantic 模型，未知欄位 422 快速失敗。
* **尚未涵蓋**：監控/風控面板端點（Discord 告警、Risk Gate、熔斷狀態）待 Wave D（risk/monitoring）合入 main 後再補；本批僅研究迴圈 + 驗證讀寫面。
