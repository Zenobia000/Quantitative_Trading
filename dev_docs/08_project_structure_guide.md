# 專案結構指南 — backtest_platform

> **版本：** v1.0 | **更新：** 2026-05-26

---

## 設計原則

- **按功能組織**：每個 sub-package（`data/`、`strategy/`、`engines/`）為一個明確職責
- **明確職責**：`config/` = 參數、`data/` = IO、`strategy/` = 純邏輯、`engines/` = 回測 wrapper、`validation/` = 統計檢驗
- **一致命名**：Python `snake_case.py`、測試 `test_*.py`、CLI module 用 `python -m <module>`
- **配置外部化**：`.env` + Pydantic `BaseSettings`（M2 引入）
- **根目錄簡潔**：原始碼放 `src/`，根目錄只放 `pyproject.toml`、`README.md`、`docker-compose.yml`

---

## 頂層結構

```plaintext
backtest_platform/
├── docker/                       # 容器映像與初始化
│   └── timescaledb/init.sql      # DB schema
├── docs/                         # 工程文件（M1_setup、m1_data_audit）
├── data/                         # ETL 產出 cache（gitignore）
│   └── parquet/
├── reports/                      # CLI 輸出報表（gitignore）
├── src/backtest_platform/        # 原始碼
│   ├── __init__.py
│   ├── config/
│   ├── data/
│   ├── strategy/
│   ├── engines/                  # M2+
│   ├── validation/               # M3+
│   └── pipeline.py
├── tests/                        # pytest
│   ├── conftest.py
│   ├── data/
│   ├── strategy/
│   └── test_strategy_config.py
├── .env.example                  # 環境變數樣板
├── .gitignore
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

## 原始碼結構（src/backtest_platform/）

```plaintext
src/backtest_platform/
├── __init__.py
│
├── config/                       # 純資料層
│   ├── __init__.py
│   └── strategy_config.py        # StrategyConfig (Pydantic frozen)
│
├── data/                         # Infrastructure：IO + 外部 API
│   ├── __init__.py
│   ├── schemas.py                # Pydantic models + ETLBundle
│   ├── finmind_etl.py            # FinMind 拉取 + normalize + CLI
│   ├── adjustment.py             # 前復權因子計算
│   ├── db_writer.py              # TimescaleDB idempotent upsert
│   └── universe.py               # 標的池過濾
│
├── strategy/                     # Domain：純函式策略邏輯
│   ├── __init__.py
│   ├── indicators.py             # RSI / KD / MACD / SwingHigh/Low
│   ├── scoring.py                # compute_scores（四層計分）
│   └── signals.py                # compute_signals + evaluate_bar
│
├── engines/                      # M2+：回測引擎 wrapper
│   ├── __init__.py
│   ├── rqalpha_runner.py         # M2
│   ├── vectorbt_runner.py        # M3
│   └── mod_taiwan_stock/         # rqalpha 自訂 mod
│
├── validation/                   # M3+：統計驗證
│   ├── __init__.py
│   ├── pbo.py                    # PBO/CSCV
│   ├── wfa.py                    # Walk-Forward
│   ├── monte_carlo.py
│   └── metrics.py                # 整合 quantstats
│
├── live/                         # M4+：紙上交易與實盤
│   ├── __init__.py
│   ├── paper_trader.py
│   └── shioaji_executor.py
│
└── pipeline.py                   # Application：端到端 CLI 編排
```

---

## 測試結構

```plaintext
tests/
├── conftest.py                   # 全局 fixtures（StrategyConfig, synthetic_uptrend...）
│
├── test_strategy_config.py       # config 模組測試
│
├── data/
│   ├── __init__.py
│   ├── test_finmind_etl.py
│   ├── test_adjustment.py
│   ├── test_db_writer.py         # 含 @integration mark
│   └── test_universe.py
│
└── strategy/
    ├── __init__.py
    ├── test_scoring.py
    └── test_signals.py
```

### 測試標記

`pyproject.toml` 中定義：
- `@pytest.mark.integration` — 需要 DB / FinMind API
- `@pytest.mark.slow` — 執行 > 5 秒

執行：
```bash
pytest -m "not integration"   # 跳過 integration
pytest -m integration          # 只跑 integration
```

---

## 文檔結構

```plaintext
backtest_platform/docs/
├── M1_setup.md                   # M1 驗收條件 + 端到端驗證
├── m1_data_audit_2330_2024_11.md # XQ vs FinMind 抽查報告
├── M2_backtest_report.md         # （待 M2 產出）
├── M3_validation_report.md       # （待 M3）
├── M4_paper_trading_log.md       # （待 M4）
└── M5_live_runbook.md            # （待 M5）

dev_docs/                         # 本目錄：工程文件
└── （見 INDEX.md）
```

---

## 命名慣例

| 檔案類型 | 規則 | 範例 |
| :--- | :--- | :--- |
| Python 模組 | `snake_case.py` | `finmind_etl.py` |
| 測試 | `test_*.py` | `test_scoring.py` |
| 類別 | `PascalCase` | `StrategyConfig`, `ETLBundle` |
| 函式 | `snake_case` | `compute_scores`, `fetch_bundle` |
| 常數 | `UPPER_SNAKE_CASE` | `REQUIRED_COLUMNS`, `SIGNAL_PRIORITY` |
| 私有 helper | `_underscore_prefix` | `_normalize_daily`, `_evaluate_priority` |
| CLI module | 對應檔名 | `python -m backtest_platform.pipeline` |

---

## 跨層依賴規則（強制）

```
pipeline.py  ──► engines/  ──► strategy/  ──► config/
     │              │              │
     └─────────────►data/◄─────────┘
                    │
                    └─► (FinMind API / TimescaleDB)
```

**禁止**：
- ❌ `strategy/` 依賴 `data/`（domain 不知道 IO 存在）
- ❌ `config/` 依賴任何模組（純資料）
- ❌ `data/` 之間 cross-import（schemas 是底層、其他並列）

詳見 [09_file_dependencies_template.md](./09_file_dependencies_template.md)

---

## .env 環境變數

```ini
# .env.example（不存 secret）
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=quant
POSTGRES_PASSWORD=change_me_in_production
POSTGRES_DB=quant_trading

GRAFANA_ADMIN_PASSWORD=admin

FINMIND_TOKEN=

# M5
SHIOAJI_API_KEY=
SHIOAJI_API_SECRET=
SHIOAJI_PERSON_ID=
```

**規則**：`.env` 永遠 gitignore；任何新環境變數先寫入 `.env.example`。

---

## 演進原則

- 本結構是 M1 起點，後續 milestone 依需擴充
- 頂層結構（`src/backtest_platform/` 下的 sub-packages）變更需 ADR
- `engines/` `validation/` `live/` 目前是空殼，M2/M3/M4 才實作
- 一致性比嚴格遵守模式更重要
