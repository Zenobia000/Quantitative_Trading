# M1 — 資料 + 策略骨架（Setup & 驗收）

> 對應 `~/.claude/plans/...` 計畫第 6.1 節 M1 驗證條件。

## 1. 環境準備

### 1.1 Python 環境

```bash
# 建議使用 venv 或 uv
python3.10 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

執行 `pip install -e ".[engines,validation,api,ui,broker]"` 才能裝入 rqalpha / vectorbt / Shioaji 等重型依賴；M1 階段只需要 `[dev]` 即可。

### 1.2 服務啟動

```bash
cp .env.example .env  # 填入 FinMind / Shioaji token（M1 可先跳過 Shioaji）
docker compose up -d
docker compose ps     # 三個服務都應該是 healthy
```

服務埠：

| 服務 | URL |
| :--- | :--- |
| TimescaleDB | `localhost:5432` |
| Prefect UI | `http://localhost:4200` |
| Grafana | `http://localhost:3000` (admin / `${GRAFANA_ADMIN_PASSWORD}`) |

## 2. 驗收條件（M1 Acceptance）

對照計畫第 6.1：

### ✅ A1：`docker-compose up` 全部 healthy

```bash
docker compose ps
# 三個容器都是 (healthy)
```

如果 TimescaleDB 起不來，常見原因是埠衝突或 volume 內容過舊：

```bash
docker compose down -v   # 注意：清空 volume
docker compose up -d
```

### A2：FinMind ETL 拉 1 個月台積電資料

```bash
export FINMIND_TOKEN=...
python -m backtest_platform.data.finmind_etl \
    --stock-id 2330 \
    --start 2024-01-01 --end 2024-01-31 \
    --output data/parquet
```

驗證：
- 三個 parquet 檔案產生於 `data/parquet/`
- 抽 1 檔股 K 線與 XQ 對比，差異 < 0.5%
- 若差異 > 0.5%，檢查復權因子（FinMind 預設未復權，需另計）

### A3：v2.md 訊號邏輯轉 Python 後與 XQ 一致

抽 5 檔股 30 個交易日跑 `compute_scores` + `compute_signals`，與 XQ 標記人工核對。腳本見 `docs/m1_signal_reconciliation.md`（待補）。

### ✅ A4：所有單元測試通過

```bash
PYTHONPATH=src python3 -m pytest -p no:asyncio
# 24 passed
```

注意：本機 pytest-asyncio plugin 與 pytest 9.x 不相容，加 `-p no:asyncio` 暫時跳過。CI 用 venv 隔離可避免此問題。

## 3. 已完成清單（M1 deliverables）

- [x] `docker-compose.yml`（TimescaleDB + Prefect + Grafana 三件套）
- [x] `docker/timescaledb/init.sql`（hypertable schema）
- [x] `src/backtest_platform/config/strategy_config.py`（Pydantic frozen model，預設值對齊 v2.md 2.7.1）
- [x] `src/backtest_platform/strategy/indicators.py`（Stochastic、MACD、RSI、SwingHigh/Low）
- [x] `src/backtest_platform/strategy/scoring.py`（`compute_scores` pure function）
- [x] `src/backtest_platform/strategy/signals.py`（state machine + `compute_signals` + `evaluate_bar`）
- [x] `src/backtest_platform/data/schemas.py`（Pydantic ETL schemas + `merged()` join helper）
- [x] `src/backtest_platform/data/finmind_etl.py`（CLI + 可注入 loader）
- [x] `tests/` 24 個單元測試全綠

## 4. 已知限制 / M2 待辦

| 項目 | 限制 | M2 動作 |
| :--- | :--- | :--- |
| Broker chip 子分類（top10/gov/geo） | FinMind 免費版未提供，目前以 0 填充 | 加 TWSE/TPEX 公開資訊爬蟲補齊 |
| 復權因子 | ETL 全部設 1.0 | 整合 FinMind `taiwan_stock_dividend` 計算前復權因子 |
| `SwingHigh` 實作 | 使用 `rolling.max().shift(1)` 近似 XQ pivot | M3 之前抽樣 100 個訊號比對 XQ，差異 > 1% 則改寫為真實 pivot |
| 資料 → DB 寫入 | 目前只寫 parquet，未實作 TimescaleDB upsert | M2 加 `to_sql` + `ON CONFLICT DO UPDATE` 路徑 |
| 已下市股票補齊 | 尚未實作 | M2 加 TWSE 下市清單比對與補爬 |

## 5. 下一里程碑（M2 預覽）

- 安裝 `rqalpha` 並建立 `mod_taiwan_stock`：交易日曆 / 漲跌停 / 手續費 / 法人籌碼欄位注入
- 寫 `engines/rqalpha_runner.py`：吃 parquet → 跑 Portfolio 回測 → 輸出 trade log + equity
- 用 `quantstats` 出 IS 報表（2015–2020 台積電單檔）
- 對照 v2.md 4.3.1 綠/黃/紅燈表，產生 markdown 報告
