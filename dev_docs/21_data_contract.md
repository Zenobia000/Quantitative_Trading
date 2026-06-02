# 資料契約 — backtest_platform

> **版本：** v1.2 | **更新：** 2026-06-02
> **適用 M**：M1 既有四表 + M2-5 新增九表（共 13 表）
> **進度**：見 [`16_wbs_development_plan.md §3.D`](./16_wbs_development_plan.md)（單一狀態真相源）
> **適用範圍：** L1 資料層（對應 `05_architecture_and_design_document.md` §4）
> **關聯文件：** `20_dashboard_specification.md`（消費端）、`23_deployment_topology.md`（DB 部署）、ADR-006（FinLab 選型）

---

## 1. 資料層架構

### 1.1 三層資料流總覽

```mermaid
flowchart LR
    subgraph upstream["上游資料源"]
        finlab[("FinLab API<br/>付費，主來源")]
        finmind[("FinMind API<br/>免費，fallback")]
        shioaji[("Shioaji API<br/>live quote")]
        twse[("TWSE 公開資訊<br/>下市清單")]
    end

    subgraph cache["快取與 Bundle"]
        bundle["Zipline data bundle<br/>finmind/finlab"]
        parquet["Parquet Cache<br/>data/parquet/"]
    end

    subgraph storage["持久化儲存"]
        tsdb[("TimescaleDB<br/>13 tables")]
    end

    subgraph consumer["消費端"]
        zipline["Zipline Algorithm"]
        vbt["vectorbt Engine"]
        ui["Streamlit / Grafana"]
        broker["PaperBroker / ShioajiBroker"]
    end

    finlab -->|"finlab_bundle.py<br/>(一次性回填+日增量)"| bundle
    finmind -->|"finmind_bundle.py<br/>(fallback)"| bundle
    bundle --> zipline
    bundle --> vbt
    finlab -->|"finlab_live.py<br/>polling"| tsdb
    shioaji -->|"shioaji_quote.py<br/>websocket"| tsdb
    shioaji -->|"shioaji_broker.py<br/>fills"| tsdb
    twse -->|"M2+ scrape"| parquet
    tsdb --> ui
    tsdb --> broker
    zipline -->|"metrics_emitter"| tsdb
```

### 1.2 三角色定位

| 角色 | 載體 | 適用場景 | RPO |
| :--- | :--- | :--- | :--- |
| **Zipline bundle** | 檔案系統（`.zipline/data/`） | Backtest 歷史回測（讀取效能優先） | 不適用（rebuilt） |
| **TimescaleDB cache** | TimescaleDB hypertables | OLTP（部位/訊號/audit） + dashboard 查詢 | 24h |
| **Live feed buffer** | TimescaleDB regular tables | Paper / Live 即時資料 | 5 分鐘 |

### 1.3 為何 bundle 與 TimescaleDB 並存

| 維度 | Bundle | TimescaleDB |
| :--- | :--- | :--- |
| 讀取模式 | Zipline 順序 scan 全市場 | 點查詢、aggregation |
| 寫入頻率 | 一次性 ingest + 日增量 | 高頻寫入（每訊號/每 fill） |
| 跨機共享 | 否（本機檔案） | 是（DB 連線） |
| 結構 | 固定（OHLCV + adjustment）| 自定義 schema |
| 規模 | 100 檔 10 年 ~ 200MB | 同樣資料 + 全部 metrics ~ 2GB |

---

## 2. 資料源 Schema

### 2.1 FinLab Schema（主來源）

> 來自 `finlab.data.get()` 回傳的 DataFrame；以 stock_id 為 columns、trade_date 為 index 的寬表結構。
> 註：FinLab 預設股價已**前復權**，無需自行 adjustment。

#### 2.1.1 Price endpoint：`price:收盤價` / `price:開盤價` 等

| 欄位 | 型別 | 範例 | 說明 |
| :--- | :--- | :--- | :--- |
| index (date) | `pd.Timestamp` | `2024-05-30` | 交易日 |
| columns | `str (stock_id)` | `'2330'`, `'2454'` | 個股代號 |
| values | `float` | `542.0` | 前復權後價格 |

**完整 price 集合**：
| FinLab key | 對應 OHLCV |
| :--- | :--- |
| `price:開盤價` | open |
| `price:最高價` | high |
| `price:最低價` | low |
| `price:收盤價` | close |
| `price:成交股數` | volume |
| `price:成交金額` | turnover |

#### 2.1.2 法人籌碼：`institutional_investors_trading_summary:外陸資買賣超股數` 等

| 欄位 | 型別 | 範例 | 說明 |
| :--- | :--- | :--- | :--- |
| index (date) | `pd.Timestamp` | `2024-05-30` | — |
| columns | `str (stock_id)` | `'2330'` | — |
| values | `float` | `1234567.0` | 淨買賣超股數（正=買超） |

| FinLab key | 含義 |
| :--- | :--- |
| `institutional_investors_trading_summary:外陸資買賣超股數` | 外資 |
| `institutional_investors_trading_summary:投信買賣超股數` | 投信 |
| `institutional_investors_trading_summary:自營商買賣超股數(自行買賣)` | 自營商 |

#### 2.1.3 籌碼 / 券商分點：`broker_transactions`（FinLab 進階方案）

| 欄位 | 型別 | 範例 | 說明 |
| :--- | :--- | :--- | :--- |
| `stock_id` | `str` | `'2330'` | — |
| `date` | `date` | `2024-05-30` | — |
| `broker` | `str` | `'9A95'` | 券商代號 |
| `branch` | `str` | `'板橋'` | 分點 |
| `buy_volume` | `int` | `10000` | — |
| `sell_volume` | `int` | `5000` | — |

#### 2.1.4 財報：`fundamental_features` / `financial_statements`

| 欄位 | 型別 | 範例 |
| :--- | :--- | :--- |
| index (date) | `pd.Timestamp` | `2024Q1` 公告日 |
| columns | `str (stock_id)` | `'2330'` |
| values | `float` | EPS、ROE、毛利率 |

### 2.2 FinMind Schema（fallback）

> 來自 `FinMindApi.get_data()`；長表格式（每 row = 一個 stock + date）。

#### 2.2.1 `TaiwanStockPrice`

| 欄位 | 型別 | 範例 | 與 FinLab 對應 |
| :--- | :--- | :--- | :--- |
| `date` | `str (YYYY-MM-DD)` | `'2024-05-30'` | index |
| `stock_id` | `str` | `'2330'` | column header |
| `Trading_Volume` | `int` | `12345678` | `volume` |
| `Trading_money` | `int` | `7000000000` | `turnover` |
| `open` | `float` | `540.0` | open |
| `max` | `float` | `545.0` | high（**注意命名差異**）|
| `min` | `float` | `538.0` | low（**注意命名差異**）|
| `close` | `float` | `542.0` | close（**未復權**，需自行 adjustment）|
| `spread` | `float` | `2.0` | 漲跌幅（FinLab 無此欄）|

#### 2.2.2 `TaiwanStockInstitutionalInvestorsBuySell`

| 欄位 | 型別 | 範例 | 與 FinLab 對應 |
| :--- | :--- | :--- | :--- |
| `date` | `str` | `'2024-05-30'` | — |
| `stock_id` | `str` | `'2330'` | — |
| `name` | `str` | `'Foreign_Investor'` | tag 而非欄位 |
| `buy` | `int` | `100000` | 拆出 buy/sell |
| `sell` | `int` | `80000` | — |

**關鍵差異**：FinMind 把三大法人 + 自營商自行/避險拆成 5 個 `name`，需 group_by 才能對齊 FinLab 的「外資/投信/自營商」三欄。

#### 2.2.3 `TaiwanStockDividend`（FinLab 已內建調整，本表僅 fallback）

| 欄位 | 型別 |
| :--- | :--- |
| `date` | `str` |
| `stock_id` | `str` |
| `CashEarningsDistribution` | `float` |
| `StockEarningsDistribution` | `float` |

### 2.3 Shioaji Schema（Live）

#### 2.3.1 Tick（即時逐筆）

```python
# shioaji Quote.Tick (簡化版)
{
    "code": "2330",
    "datetime": "2026-05-31 09:01:23.456",
    "open": 542.0,
    "high": 545.0,
    "low": 540.0,
    "close": 543.0,
    "volume": 100,
    "bid_price": [543.0, 542.5, 542.0],
    "bid_volume": [50, 100, 200],
    "ask_price": [543.5, 544.0, 544.5],
    "ask_volume": [80, 150, 200],
    "tick_type": 1,  # 1=Bid, 2=Ask
    "amount": 54300.0,
}
```

#### 2.3.2 Snapshot（5 秒快照）

```python
{
    "code": "2330",
    "datetime": "2026-05-31 09:01:25",
    "open": 542.0,
    "high": 545.0,
    "low": 540.0,
    "close": 543.5,
    "volume": 12345,
    "amount": 6700000.0,
    "total_volume": 1234567,
    "total_amount": 670000000.0,
    "average_price": 542.8,
}
```

#### 2.3.3 Order Fill（成交回報）

```python
{
    "trade_id": "TXN-20260531-001",
    "order_id": "ORD-20260531-001",
    "code": "2330",
    "action": "Buy",
    "price": 543.0,
    "quantity": 1000,
    "ts": "2026-05-31 09:01:23.789",
    "exchange_ts": "2026-05-31 09:01:23.812",
    "status": "Filled",  # Filled / PartFilled / Cancelled / Rejected
}
```

---

## 3. Zipline Bundle 格式

> **實作狀態（2026-06-01）**：`finmind` bundle 已於 Sprint 1 Day 2-3 落地（commit `ed3a987`）；
> `finlab` bundle 為 M3 規劃，尚未實作。本節以 `finmind` 為當前真相源，FinLab 段落維持為設計目標。

### 3.1 Bundle 結構（Zipline 標準）

```
~/.zipline/data/finmind/                # 當前實作；FinLab 將於 M3 加入 ~/.zipline/data/finlab/
├── 2026-06-01T08;00;00.000000/
│   ├── assets-7.sqlite                 # 標的元資料（sid, symbol, asset_name, start/end_date, exchange=XTAI）
│   ├── daily_equities.bcolz/           # OHLCV 列式儲存
│   │   ├── close/ open/ high/ low/ volume/ day/
│   ├── adjustments.sqlite              # split / dividend（空 table — M1 ETL 已 cash-dividend-adjusted）
│   └── minute_equities.bcolz/          # M5 加入 minute bar 才有
```

### 3.2 Ingest 規格（finmind bundle）

| 項目 | 實際規格（`engines/zipline_adapter/bundles/finmind_bundle.py`）|
| :--- | :--- |
| 寫入函式 | `finmind_to_bundle(environ, asset_db_writer, minute_bar_writer, daily_bar_writer, adjustment_writer, calendar, start_session, end_session, cache, show_progress, output_dir)` |
| 註冊位置 | 模組 import 時 `register("finmind", finmind_to_bundle, calendar_name="XTAI")`（透過 `engines/zipline_adapter/__init__.py` auto-load）|
| Calendar | `XTAI`（`exchange-calendars 4.13.2` 提供，zipline-reloaded 直接引用，見 ADR-013）|
| Frequency | `daily`（M2-M4）；`minute` 為 M5 規劃 |
| Universe 解析 | 三層 fallback：`UNIVERSE_FINMIND` env (csv) → `UNIVERSE_FILE` env (path) → `DEFAULT_UNIVERSE` 10 檔常數（TSE 大中型權值代表）|
| Missing session 處理 | XTAI session 在範圍內但 FinMind 沒資料 → **OHLC ffill + volume=0**（zipline `BcolzDailyBarWriter` 嚴格要求每 session 有 row，不補會 AssertionError 阻塞 ingest）|
| Calendar 溢出處理 | FinMind 給的日期不在 XTAI session 上 → drop |
| 前導 NaN | 最早幾天 FinMind 無資料 → ffill 後仍 NaN，dropna |
| Adjustments | 寫空 table（`splits=pd.DataFrame()`、`dividends=pd.DataFrame()`）— M1 ETL `db_writer.py` 已套用 cash dividend，bundle 不重複處理 |
| 漲跌停 | 不在 bundle 處理，於 broker 模組（`PaperBroker._apply_price_limit()`，M4 實作）|

### 3.3 Asset Metadata（finmind bundle 寫入規格）

zipline-reloaded 3.x `asset_db_writer.write()` 要求的欄位（`_build_asset_metadata()` 產出）：

| 欄位 | 內容 | 備註 |
| :--- | :--- | :--- |
| `sid` | 從 0 遞增的整數 | universe 排序後 enumerate |
| `symbol` | 股票代碼字串（如 `"2330"`） | 主要 lookup key |
| `asset_name` | M2 暫等同 symbol | M3 enrich with company names |
| `start_date` | `bundle.start_date` `Timestamp` | ETLBundle 內最早 bar |
| `end_date` | `bundle.end_date` `Timestamp` | ETLBundle 內最晚 bar |
| `first_traded` | 同 `start_date` | — |
| `auto_close_date` | `end_date + 1 day` | zipline 必填 |
| `exchange` | 固定 `"XTAI"` | — |

### 3.4 Parquet Cache（FinMind API 短路）

`engines/zipline_adapter/bundles/parquet_cache.py` 在 ingest 上游攔截 FinMind API 呼叫，緩解 Plan v3.0 R2 風險（FinMind 免費版 API 配額有限）：

| 項目 | 規格 |
| :--- | :--- |
| 類別 | `ParquetCache(cache_dir: Path)` |
| 入口函式 | `cached_or_fetch(symbol, start, end, *, cache_dir, fetcher) -> ETLBundle` |
| 命中策略 | 檔名 `{cache_dir}/finmind/{symbol}_{start}_{end}.parquet`；存在則直接讀，否則呼叫 `fetcher()` 並寫入 |
| 預期 API 量降幅 | 100 stocks × 7 年 = 2100 API request → **< 7 / day**（首次後幾乎全 cache hit） |
| 失敗策略 | 寫 cache 失敗不阻塞 ingest（log warning，下次重試） |

### 3.5 Ingest 模式

| 模式 | 觸發 | 行為 |
| :--- | :--- | :--- |
| **Initial backfill** | `zipline ingest -b finmind`（首次跑）| Universe 全歷史拉取；parquet cache miss → FinMind API ×N |
| **Re-ingest (cache hit)** | 同上重跑 | parquet cache hit；零 API 呼叫，純本機 IO |
| **Daily incremental** | Prefect cron（M4 規劃，14:35）| 拉當日 universe；append 為新 bundle timestamp 目錄 |
| **Force refresh** | 手動刪 parquet cache | 下次 ingest 走 fresh API |

### 3.6 註冊 Wiring（auto-load）

```python
# engines/zipline_adapter/__init__.py
"""Import 此模組就會註冊 bundle，zipline ingest -b finmind 即可用。"""
from backtest_platform.engines.zipline_adapter.bundles import finmind_bundle  # noqa: F401 — side-effect import
```

```python
# engines/zipline_adapter/bundles/finmind_bundle.py 結尾
register("finmind", finmind_to_bundle, calendar_name="XTAI")
```

zipline 透過 `~/.zipline/extension.py` 找 bundle；本專案改採「import 時自動 register」，無需動 zipline 設定檔。

---

## 4. TimescaleDB Schema（完整 DDL）

### 4.1 Schema 總表

| # | 表 | M1 | M2 | M3 | M4 | M5 | 類型 | 對應功能 |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| 1 | `daily_bars` | ✅ | | | | | hypertable | OHLCV cache |
| 2 | `institutional_flows` | ✅ | | | | | hypertable | 三大法人 |
| 3 | `broker_chips` | ✅ | | | | | hypertable | 籌碼 |
| 4 | `universe` | ✅ | | | | | regular | 篩選結果 |
| 5 | `equity_snapshots` | | ✅ | | | | hypertable | 帳戶權益曲線 |
| 6 | `positions` | | ✅ | | | | regular | 當前部位 |
| 7 | `signals` | | ✅ | | | | hypertable | 訊號日誌 |
| 8 | `fills` | | | | ✅ | | hypertable | 成交回報 |
| 9 | `orders` | | | | ✅ | | hypertable | 訂單記錄 |
| 10 | `risk_metrics` | | | ✅ | | | hypertable | 風控指標 |
| 11 | `validation_runs` | | | ✅ | | | regular | PBO/DSR/WFA |
| 12 | `data_quality_log` | ✅ | | | | | regular | DQ 異常 |
| 13 | `alerts` | | | | ✅ | | hypertable | 告警記錄 |

### 4.2 M1 既有四表（簡化引用，完整 DDL 見 `dashboard/db_schema.sql`）

```sql
-- daily_bars (M1 已有)
CREATE TABLE daily_bars (
    stock_id    TEXT NOT NULL,
    trade_date  DATE NOT NULL,
    open        NUMERIC(12,4),
    high        NUMERIC(12,4),
    low         NUMERIC(12,4),
    close       NUMERIC(12,4),
    volume      BIGINT,
    adj_factor  NUMERIC(12,8) DEFAULT 1.0,
    PRIMARY KEY (stock_id, trade_date)
);
SELECT create_hypertable('daily_bars', 'trade_date', chunk_time_interval => INTERVAL '1 month');
CREATE INDEX ON daily_bars (stock_id, trade_date DESC);

-- institutional_flows, broker_chips, universe 略（M1 已存在）
```

### 4.3 新增表 — equity_snapshots（M2）

```sql
CREATE TABLE equity_snapshots (
    snapshot_time     TIMESTAMPTZ NOT NULL,
    strategy_id       TEXT NOT NULL,
    mode              TEXT NOT NULL,  -- 'backtest' | 'paper' | 'live'
    run_id            TEXT NOT NULL,  -- UUID per run
    equity            NUMERIC(18,4) NOT NULL,
    cash              NUMERIC(18,4) NOT NULL,
    positions_value   NUMERIC(18,4) NOT NULL,
    open_positions    INT NOT NULL,
    portfolio_heat    NUMERIC(6,4),
    drawdown          NUMERIC(6,4),
    daily_return      NUMERIC(8,6),
    cumulative_return NUMERIC(8,6),
    PRIMARY KEY (snapshot_time, strategy_id, run_id)
);
SELECT create_hypertable('equity_snapshots', 'snapshot_time', chunk_time_interval => INTERVAL '1 month');
CREATE INDEX ON equity_snapshots (strategy_id, snapshot_time DESC);

-- M5 retention：live 模式永久；backtest 90 天
SELECT add_retention_policy('equity_snapshots',
    INTERVAL '90 days',
    if_not_exists => TRUE
);
```

### 4.4 新增表 — positions（M2）

```sql
CREATE TABLE positions (
    position_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id      TEXT NOT NULL,
    run_id           TEXT NOT NULL,
    stock_id         TEXT NOT NULL,
    opened_at        TIMESTAMPTZ NOT NULL,
    closed_at        TIMESTAMPTZ,  -- NULL = open
    entry_price      NUMERIC(12,4) NOT NULL,
    exit_price       NUMERIC(12,4),
    quantity         INT NOT NULL,
    stop_loss        NUMERIC(12,4),
    take_profit      NUMERIC(12,4),
    realized_pnl     NUMERIC(18,4),
    unrealized_pnl   NUMERIC(18,4),
    status           TEXT NOT NULL DEFAULT 'OPEN',  -- OPEN | CLOSED | LIQUIDATED
    UNIQUE (strategy_id, run_id, stock_id, opened_at)
);
CREATE INDEX ON positions (strategy_id, status) WHERE status = 'OPEN';
CREATE INDEX ON positions (stock_id, opened_at DESC);
```

### 4.5 新增表 — signals（M2）

```sql
CREATE TABLE signals (
    signal_id        UUID NOT NULL DEFAULT gen_random_uuid(),
    signal_time      TIMESTAMPTZ NOT NULL,
    strategy_id      TEXT NOT NULL,
    run_id           TEXT NOT NULL,
    stock_id         TEXT NOT NULL,
    action           TEXT NOT NULL,  -- buy/add/reduce/exit/stoploss/takeprofit/hold
    priority         INT NOT NULL,   -- 1=stoploss .. 7=hold
    reason_json      JSONB NOT NULL,  -- {scores, prices, context, gates}
    submitted        BOOLEAN DEFAULT FALSE,
    submitted_at     TIMESTAMPTZ,
    PRIMARY KEY (signal_time, signal_id)
);
SELECT create_hypertable('signals', 'signal_time', chunk_time_interval => INTERVAL '7 days');
CREATE INDEX ON signals (strategy_id, signal_time DESC);
CREATE INDEX ON signals (stock_id, signal_time DESC);
CREATE INDEX ON signals USING GIN (reason_json);
```

### 4.6 新增表 — orders（M4）

```sql
CREATE TABLE orders (
    order_id         UUID NOT NULL DEFAULT gen_random_uuid(),
    created_at       TIMESTAMPTZ NOT NULL,
    signal_id        UUID REFERENCES signals(signal_id),
    broker           TEXT NOT NULL,  -- paper | shioaji
    stock_id         TEXT NOT NULL,
    side             TEXT NOT NULL,  -- Buy | Sell
    order_type       TEXT NOT NULL,  -- Market | Limit | MOC | LOC
    quantity         INT NOT NULL,
    limit_price      NUMERIC(12,4),  -- NULL for Market
    status           TEXT NOT NULL,  -- PENDING | SUBMITTED | FILLED | PARTIAL | CANCELLED | REJECTED
    broker_order_id  TEXT,
    submitted_at     TIMESTAMPTZ,
    completed_at     TIMESTAMPTZ,
    error_msg        TEXT,
    PRIMARY KEY (created_at, order_id)
);
SELECT create_hypertable('orders', 'created_at', chunk_time_interval => INTERVAL '7 days');
CREATE INDEX ON orders (status) WHERE status IN ('PENDING', 'SUBMITTED', 'PARTIAL');
CREATE INDEX ON orders (signal_id);
```

### 4.7 新增表 — fills（M4）

```sql
CREATE TABLE fills (
    fill_id          UUID NOT NULL DEFAULT gen_random_uuid(),
    fill_time        TIMESTAMPTZ NOT NULL,
    order_id         UUID NOT NULL,
    signal_id        UUID,
    stock_id         TEXT NOT NULL,
    side             TEXT NOT NULL,
    fill_price       NUMERIC(12,4) NOT NULL,
    fill_quantity    INT NOT NULL,
    commission       NUMERIC(10,4),
    tax              NUMERIC(10,4),
    slippage_bps     NUMERIC(8,2),  -- (fill_price - expected) / expected * 10000
    broker           TEXT NOT NULL,
    broker_trade_id  TEXT,
    PRIMARY KEY (fill_time, fill_id)
);
SELECT create_hypertable('fills', 'fill_time', chunk_time_interval => INTERVAL '7 days');
CREATE INDEX ON fills (order_id);
CREATE INDEX ON fills (stock_id, fill_time DESC);
```

### 4.8 新增表 — risk_metrics（M3）

```sql
CREATE TABLE risk_metrics (
    metric_time      TIMESTAMPTZ NOT NULL,
    strategy_id      TEXT NOT NULL,
    run_id           TEXT NOT NULL,
    current_dd       NUMERIC(6,4),
    var_95           NUMERIC(8,4),
    cvar_95          NUMERIC(8,4),
    portfolio_heat   NUMERIC(6,4),
    concentration_top1 NUMERIC(5,4),
    concentration_top3 NUMERIC(5,4),
    hhi              NUMERIC(6,5),
    sharpe_30d       NUMERIC(6,3),
    sortino_30d      NUMERIC(6,3),
    event_type       TEXT,  -- NULL | HEAT_WARN | CONCENT | L1_PAUSE | L2_CUT | L3_HALT
    event_context    JSONB,
    PRIMARY KEY (metric_time, strategy_id, run_id)
);
SELECT create_hypertable('risk_metrics', 'metric_time', chunk_time_interval => INTERVAL '1 month');
CREATE INDEX ON risk_metrics (strategy_id, metric_time DESC);
CREATE INDEX ON risk_metrics (event_type, metric_time DESC) WHERE event_type IS NOT NULL;
```

### 4.9 新增表 — validation_runs（M3）

```sql
CREATE TABLE validation_runs (
    run_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_time         TIMESTAMPTZ NOT NULL,
    method           TEXT NOT NULL,  -- PBO | DSR | WFA | CPCV | MC
    strategy_id      TEXT NOT NULL,
    params_json      JSONB NOT NULL,
    result_json      JSONB NOT NULL,
    summary_metric   NUMERIC(10,6),
    pass_threshold   BOOLEAN
);
CREATE INDEX ON validation_runs (strategy_id, method, run_time DESC);
CREATE INDEX ON validation_runs USING GIN (result_json);
```

### 4.10 新增表 — data_quality_log（M1 既有結構增強）

> **遷移注意**：M1 原 schema 為 `PRIMARY KEY (check_time, check_name)` + `(check_name, target_date, passed, detail)`。M2 改為 `BIGSERIAL` PK + 新增 `source / check_type / stock_id / trade_date / severity / resolved / resolved_at` 欄位。fresh install（含 `init.sql` 改寫）直接套新 schema；既有 M1 部署需執行 migration（建議新表 + backfill + rename，保留 audit）。

```sql
CREATE TABLE data_quality_log (
    check_id         BIGSERIAL PRIMARY KEY,
    check_time       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source           TEXT NOT NULL,  -- finlab | finmind | shioaji
    check_type       TEXT NOT NULL,  -- missing | outlier | mismatch | stale
    stock_id         TEXT,
    trade_date       DATE,
    severity         TEXT NOT NULL,  -- info | warn | error
    detail_json      JSONB NOT NULL,
    resolved         BOOLEAN DEFAULT FALSE,
    resolved_at      TIMESTAMPTZ
);
CREATE INDEX ON data_quality_log (check_time DESC);
CREATE INDEX ON data_quality_log (resolved, severity) WHERE resolved = FALSE;
```

### 4.11 新增表 — alerts（M4）

```sql
CREATE TABLE alerts (
    alert_id         UUID NOT NULL DEFAULT gen_random_uuid(),
    alert_time       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    rule_id          TEXT NOT NULL,
    level            TEXT NOT NULL,  -- critical | high | info
    title            TEXT NOT NULL,
    message          TEXT NOT NULL,
    context_json     JSONB,
    sent_to_discord BOOLEAN DEFAULT FALSE,
    sent_at          TIMESTAMPTZ,
    PRIMARY KEY (alert_time, alert_id)
);
SELECT create_hypertable('alerts', 'alert_time', chunk_time_interval => INTERVAL '7 days');
CREATE INDEX ON alerts (sent_to_discord, alert_time DESC) WHERE sent_to_discord = FALSE;
CREATE INDEX ON alerts (rule_id, alert_time DESC);
```

---

## 5. 資料一致性策略

### 5.1 三大 ACL（Anti-Corruption Layer）邊界

| ACL | 位置 | 職責 | 失敗處置 |
| :--- | :--- | :--- | :--- |
| **FinLab → Zipline bundle** | `finlab_bundle.py` `_normalize_*()` | 寬表轉長表、欄位 rename、補 timezone | log + skip bad rows，總 skip > 1% → fail bundle |
| **Live feed → TimescaleDB** | `data_feed/finlab_live.py` `_validate_tick()` | Pydantic schema 驗證、reject out-of-hours | drop + write data_quality_log |
| **Shioaji → fills** | `brokers/shioaji_broker.py` `_normalize_fill()` | 統一 trade_id、translate status enum | 拒寫 fills 表、Discord CRITICAL |

### 5.2 強一致 vs 最終一致

| 表 | 一致性 | 理由 | 機制 |
| :--- | :--- | :--- | :--- |
| `orders` / `fills` | 強一致 | audit trail，不能丟 | Postgres ACID transaction |
| `positions` | 強一致 | 即時狀態 | row-level lock + version |
| `signals` | 強一致 | 行為證據 | 直寫 |
| `daily_bars` | 最終一致 | ETL 重跑會修正 | `INSERT ... ON CONFLICT DO UPDATE` |
| `equity_snapshots` | 最終一致 | 可從 fills 重算 | append-only |
| `risk_metrics` | 最終一致 | 派生 | append-only |

### 5.3 跨源 cross-check

| 檢查 | 來源 A | 來源 B | 容忍 | 失敗動作 |
| :--- | :--- | :--- | :--- | :--- |
| OHLCV 對拍 | FinLab | FinMind | < 1% | log + warn |
| 法人金額 | FinLab | FinMind aggregated | < 5% | log（資料來源差異） |
| Live close vs daily close | Shioaji 收盤 tick | FinLab daily close | < 0.5% | data_quality_log |
| 持倉 reconciliation | TimescaleDB `positions` | Shioaji `list_positions()` | 0（精確） | Discord CRITICAL + 暫停下單 |

---

## 6. 資料品質檢查（DQ Rules）

### 6.1 規則表

| Rule ID | 類別 | 條件 | severity | 動作 |
| :--- | :--- | :--- | :--- | :--- |
| `DQ-001` | missing | 預期交易日 daily_bars 無記錄 | error | block downstream + alert |
| `DQ-002` | missing | 三大法人單日缺一檔 | warn | log，續跑 |
| `DQ-003` | outlier | 單日漲跌 > ±15%（非除權息） | warn | flag，人工確認 |
| `DQ-004` | outlier | volume > 30 天平均 × 10 | info | log |
| `DQ-005` | mismatch | adj_factor 跳變 > 50%（未公告除權） | error | block downstream |
| `DQ-006` | stale | 最新 trade_date < today - 2 trading days | error | alert |
| `DQ-007` | cross-source | FinLab vs FinMind close diff > 1% | warn | log，採 FinLab |
| `DQ-008` | live | tick 時間戳 < now - 5min（live mode） | error | 切備援 feed |
| `DQ-009` | reconciliation | positions count != Shioaji list | error | Discord CRITICAL |
| `DQ-010` | adjustment | 同股 close 前後日 diff > 30% 無對應 split/dividend | error | 暫停該股訊號 |

### 6.2 執行頻率

| 規則類 | 頻率 |
| :--- | :--- |
| ETL 後即時 | DQ-001~005, 007, 010 |
| Live polling | DQ-008 |
| 每 5 分鐘 | DQ-009（live mode） |
| 每日 14:35 | DQ-006 |

---

## 7. 資料保留與備份

### 7.1 Retention Policy

| 表 | 保留 | 機制 | 啟用 |
| :--- | :--- | :--- | :--- |
| `daily_bars` | 永久 | — | M1 |
| `institutional_flows` | 永久 | — | M1 |
| `broker_chips` | 永久 | — | M1 |
| `equity_snapshots` | live 永久 / backtest 90 天 | TimescaleDB retention policy | M2 |
| `positions` | closed 後 1 年 | scheduled job | M4 |
| `signals` | 永久 | — | M2 |
| `orders` / `fills` | 永久（audit） | — | M4 |
| `risk_metrics` | 1 年 | retention policy | M3 |
| `validation_runs` | 永久 | — | M3 |
| `data_quality_log` | 1 年 | retention policy | M1 |
| `alerts` | 90 天 | retention policy | M4 |

### 7.2 備份策略

| 環境 | 工具 | 頻率 | 目的地 | RPO | RTO |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Dev | 無 | — | — | N/A | N/A |
| Staging | `pg_dump` | 每週 | local disk | 7d | 4h |
| Prod | `pg_dump` + `pg_basebackup` | daily / hourly WAL | GCS | 1h | 1h |

```bash
# M5 production 備份 cron
0 2 * * * /opt/scripts/pg_backup.sh
# → pg_dump -Fc quant_trading | gzip | gsutil cp - gs://quant-backup/$(date +\%F).dump.gz
```

### 7.3 災難恢復

| 情境 | 動作 | RTO |
| :--- | :--- | :--- |
| 單表 corruption | restore 該表 from 最新 dump | 30min |
| 整 DB 毀損 | 開新 VM + restore + replay WAL | 1h |
| Bundle 毀損 | `zipline ingest -b finlab --start <full>` | 2h（含 FinLab 拉資料） |

---

## 8. Dashboard REST API 契約（ADR-015）

> **背景**：[ADR-015](./adrs/ADR-015-dashboard-design-system-and-react-upgrade.md) 將策略績效層（面板 A–E）由 Streamlit 直連 SQL 升級為 React。React 不能直連 TimescaleDB，故需一層唯讀 REST API 將 §4 各表轉為 JSON 供前端消費。
> **範圍**：僅面板 A–E（策略績效層）。Grafana（F–I）走 InfluxQL，Discord 走規則引擎，皆**不經本 API**。
> **實作**：FastAPI（或既有後端擴充），唯讀（GET）；讀 TimescaleDB（ADR-002）。對應前端規格見 `web_design/pages/02_panel_{a-e}.md` 的 `[DATA & API]`。

### 8.1 通用約定

- **Base path**：`/api/dashboard`
- **方法**：全部 `GET`（唯讀；儀表板不寫資料）。
- **認證**：Bearer token（單人部署可為靜態 token / 反向代理 basic auth）；缺 token → `401`。
- **共用 query 參數**：`strategy_id`（必填，多數端點）、`run_id`（選填，預設最新 run）、`start` / `end`（ISO8601 date，預設 `[end-1y, end]`）、`mode`（`backtest|paper|live`，預設 `live`）。
- **時區**：所有時間 ISO8601 帶 offset（`+08:00` TWT）；數值以 string 或 number 回傳，前端用 Geist Mono tabular 呈現。
- **快取**：回應帶 `Cache-Control: max-age=<TTL>` 與 `ETag`；TTL 對齊面板規格（見 §8.7）。
- **分頁**：列表型端點支援 `limit`（預設 100，上限 500）+ `cursor`（keyset，依時間 DESC）。

### 8.2 回應信封（對齊 `.claude/rules/patterns.md` API 格式）

```jsonc
{
  "success": true,
  "data": { /* 或 [] */ },
  "error": null,           // 失敗時 { "code": "...", "message": "...", "detail": {...} }
  "meta": {                // 列表型才有
    "total": 187, "limit": 100, "cursor": "2026-05-30T09:01:23+08:00", "ttl": 300
  }
}
```

錯誤碼：`UNAUTHORIZED(401)` / `INVALID_PARAM(400)` / `STRATEGY_NOT_FOUND(404)` / `QUERY_TIMEOUT(504)` / `INTERNAL(500)`。錯誤訊息先述發生什麼再給建議（對齊 Design System 文案規則）。

### 8.3 面板 A — 績效總覽

| Endpoint | 來源表 | 關鍵欄位 / 計算 |
| :--- | :--- | :--- |
| `GET /performance/kpis` | `equity_snapshots` | quantstats 計算 total_return / cagr / sharpe / mdd / win_rate / trades |
| `GET /performance/equity` | `equity_snapshots` + `daily_bars(0050)` | `equity`,`cash`；benchmark normalize 同起點 |
| `GET /performance/drawdown` | `equity_snapshots` | `drawdown`（已預算） |
| `GET /performance/rolling-sharpe?window=60` | `equity_snapshots` | `equity` rolling sharpe（window∈{30,60,90}） |
| `GET /performance/monthly-returns` | `equity_snapshots` | resample monthly pct_change |

```jsonc
// GET /api/dashboard/performance/kpis?strategy_id=four_layer_resonance&start=2025-06-01&end=2026-05-31
{ "success": true, "data": {
  "total_return": 0.472, "cagr": 0.183, "sharpe": 1.62,
  "mdd": -0.124, "win_rate": 0.583, "trades": 243,
  "prev_period": { "total_return": 0.41, "sharpe": 1.55 }  // hover 同期變化
}, "error": null }

// GET /performance/equity → data: { "strategy": [{t,equity}], "benchmark": [{t,value}] }
```

### 8.4 面板 B — 部位狀態

| Endpoint | 來源表 | 計算 |
| :--- | :--- | :--- |
| `GET /positions` | `positions`(status=OPEN) + `universe`(industry) + `daily_bars`(current_price) | `pnl_pct=(current-entry)/entry`；HHI=Σ(mv_i/total)² |

```jsonc
// GET /api/dashboard/positions?strategy_id=...&run_id=latest
{ "success": true, "data": {
  "as_of": "2026-05-30T13:30:00+08:00",
  "kpi": { "heat": 0.042, "heat_limit": 0.06, "cash": 1250000, "cash_pct": 0.125,
           "open": 12, "max_open": 15, "equity": 10420000 },
  "positions": [
    { "stock_id":"2330","industry":"Semi","quantity":1000,"entry_price":542,
      "current_price":578,"pnl_pct":0.066,"days_held":12,"stop_loss":520 }
  ],
  "industry_allocation": [ {"industry":"Semi","pct":0.42,"market_value":4380000} ],
  "concentration": { "top1":0.18,"top3":0.47,"top5":0.68,"hhi":0.18 }
}, "error": null, "meta": { "total": 12, "ttl": 60 } }
```

### 8.5 面板 C — 訊號日誌

| Endpoint | 來源表 | 備註 |
| :--- | :--- | :--- |
| `GET /signals?date&action` | `signals` | action∈{all,buy,add,reduce,exit,stoploss}；`reason_json` 隨列回傳供展開 |
| `GET /signals/timeline?days=30` | `signals` | 多軌散點（依 action 分軌） |
| `GET /signals/fill-rate?days=30` | `signals` + `fills` | funnel：generated→submitted→filled + 平均 latency |

```jsonc
// GET /signals/fill-rate?strategy_id=...&days=30
{ "success": true, "data": {
  "generated": 187, "submitted": 184, "filled": 176,
  "submit_rate": 0.984, "fill_rate": 0.941,
  "avg_latency_sec": { "signal_to_submit": 0.8, "submit_to_fill": 2.3 }
}, "error": null }
// latency = fills.fill_time - signals.signal_time（join on signal_id；fills 經 orders.signal_id 關聯）
```

### 8.6 面板 D / E — 風控 + 統計驗證

| Endpoint | 來源表 | 備註 |
| :--- | :--- | :--- |
| `GET /risk/current` | `risk_metrics`(latest) | status 由 `event_type` 推導：NULL→NORMAL / HEAT_WARN,CONCENT→WARN / L*_*→CRITICAL |
| `GET /risk/mdd-trend?days=90` | `risk_metrics` | `current_dd` 序列 + 熔斷線 L1 -10%/L2 -15%/L3 -20% |
| `GET /risk/events?days=7` | `risk_metrics` where `event_type IS NOT NULL` | `event_type`,`event_context` |
| `GET /validation/wfa` | `validation_runs` where `method='WFA'` | `result_json` → IS/OOS sharpe 散點 |
| `GET /validation/summary` | `validation_runs` where `method IN('PBO','DSR')` latest | `summary_metric`,`pass_threshold` |
| `GET /validation/rolling?days=30` | `validation_runs` | rolling PBO/DSR |

```jsonc
// GET /risk/current?strategy_id=...
{ "success": true, "data": {
  "status": "NORMAL",
  "water_levels": [
    { "name":"current_dd","value":-0.032,"limit":-0.15,"pct":0.21 },
    { "name":"daily_pnl_var","value":-0.008,"var_95":-0.021,"pct":0.38 },
    { "name":"heat","value":0.042,"limit":0.06,"pct":0.70 }
  ]
}, "error": null }
```

### 8.7 快取 TTL 對照（對齊面板刷新節奏）

| 面板 / 端點 | TTL | 理由 |
| :--- | :--- | :--- |
| A 績效（kpis/equity/drawdown/rolling/monthly） | 300s | 日線級，5 分鐘快取 |
| B 部位 `/positions` | 60s | 部位變化頻繁 |
| C 即時 `/signals`（當日） | 30s | 盤中訊號 |
| C 歷史 `/signals/timeline`,`/fill-rate` | 300s | 30 日彙總 |
| D 風控 `/risk/*` | 60s | 風險水位需較即時 |
| E 統計 `/validation/*` | 300s | 驗證跑批，低頻 |

### 8.8 ACL 與一致性

- 本 API 為 §5 之外的**唯讀投影層**，不引入新寫入路徑；所有數值以 TimescaleDB 為單一真相。
- 計算型欄位（pnl_pct / HHI / latency / quantstats KPI）在 API 層即時計算，**不落庫**，避免與 §4 原始表產生第二真相。
- 即時性需求（部位 live mode）未來可加 WebSocket/SSE（見 ADR-015 §4 重新評估觸發），本契約先定義 pull 端點。

---

## 9. 變更紀錄

| 版本 | 日期 | 變更 |
| :--- | :--- | :--- |
| v1.0 | 2026-05-31 | 初版（對應 plan v1.0 §3/§5；M1 4 表 + 新增 9 表 DDL） |
| v1.1 | 2026-06-01 | 新增 §8 Dashboard REST API 契約（ADR-015：策略績效層 A–E React 化需唯讀 API 層；定義 14 個 GET 端點、回應信封、TTL 對照、唯讀投影 ACL） |
| v1.2 | 2026-06-02 | §4.10 補 M1→M2 migration note（WBS 3.D.4 落地：`init.sql` 改寫含全部 13 表；`db_writer.upsert_positions` 實作；signals/orders/fills writer stub for M4） |
