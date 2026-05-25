# 四層共振戰法回測平台

> 基於 `../strategy/v2.md` 規格書打造的台股量化回測系統。

## 狀態

**M1 — 資料 + 策略骨架**（進行中）

完整計畫見 `~/.claude/plans/https-sinotrade-github-io-tutor-prepare-idempotent-hearth.md`。

## 技術棧

| 層 | 工具 |
| :--- | :--- |
| 資料 | FinMind + Shioaji + TimescaleDB + DuckDB |
| 回測（主） | rqalpha + 自訂 mod_taiwan_stock |
| 回測（副） | vectorbt（參數網格 / WFA / MC） |
| 統計驗證 | pypbo + quantstats + pyfolio-reloaded |
| 排程 | Prefect 2.x |
| 監控 | Prometheus + Grafana + Telegram |
| API | FastAPI |
| 前端 | Streamlit (Phase 1) → React (Phase 2) |
| 下單 | Shioaji（永豐金證券） |

## 目錄結構

```
backtest_platform/
├── src/backtest_platform/
│   ├── config/          # 策略參數（對應 v2.md 6.1）
│   ├── data/            # FinMind ETL、Shioaji adapter、schemas
│   ├── strategy/        # 四層計分、狀態機、訊號層（純函式）
│   ├── engines/         # rqalpha / vectorbt 整合
│   └── validation/      # PBO / WFA / MC / 績效報表
├── tests/               # pytest 單元測試
├── docker/              # docker-compose + initdb scripts
└── docs/                # 工程文件
```

## 快速開始

```bash
# 1. 啟動基礎服務
cd backtest_platform
cp .env.example .env
docker compose up -d

# 2. 安裝 Python 依賴（建議使用 uv 或 poetry）
pip install -e ".[dev]"

# 3. 跑單元測試
pytest -v

# 4. 觸發 ETL（範例）
python -m backtest_platform.data.finmind_etl --stock_id 2330 --start 2024-01-01
```

## 里程碑

- [x] M0 規格定稿（`strategy/v2.md`）
- [ ] **M1** 資料 + 策略骨架（本階段）
- [ ] M2 IS 回測通過（2015–2020）
- [ ] M3 OOS + 統計驗證通過（PBO < 50%、DSR > 0.95）
- [ ] M4 Paper trading 3 個月
- [ ] M5 React 前端 + 小倉位實盤

## 紀律

- v2.md 是契約，偏離操作需在 Part 6.3 變更紀錄留下文字
- 訊號邏輯抽象成 pure function，rqalpha 與 vectorbt 都呼叫同一份
- 每個 milestone 通不過 → 不晉升，不允許「再調一下」
