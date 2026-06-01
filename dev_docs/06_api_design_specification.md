# API 設計規範 — backtest_platform

> **版本：** v1.0 | **更新：** 2026-05-26 | **狀態：** M1 / CLI + Python API（無 HTTP API）

---

## 1. API 形式

本專案不暴露 HTTP API（M5 才考慮）。當前提供：

1. **CLI（Click）** — 端到端操作
2. **Python API** — 程式內呼叫（pure functions + Pydantic models）

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

### 3.3 後續 CLI（M2+）

| 指令 | 階段 | 用途 |
| :--- | :---: | :--- |
| `python -m backtest_platform.data.universe build` | M2 | 建立 universe snapshot |
| `python -m backtest_platform.engines.rqalpha_runner run` | M2 | rqalpha portfolio 回測 |
| `python -m backtest_platform.engines.vectorbt_runner sweep` | M3 | 參數網格 |
| `python -m backtest_platform.validation.pbo compute` | M3 | PBO/DSR 計算 |
| `python -m backtest_platform.validation.wfa walk` | M3 | Walk-Forward |
| `python -m backtest_platform.live.paper_trader run` | M4 | 紙上交易 |

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
