# 四層共振戰法回測平台

> 基於 `../strategy/archive/v2.md` 規格書打造的台股量化交易系統（含回測 / paper / 實盤三模式）。

## 狀態

> **狀態真相源**：[`../dev_docs/16_wbs_development_plan.md`](../dev_docs/16_wbs_development_plan.md)
>
> 本 README 不重複寫 milestone 進度，避免不一致。

完整 M2-M5 規劃見 [`../dev_docs/17_m2_to_m5_master_plan.md`](../dev_docs/17_m2_to_m5_master_plan.md)。

## 技術棧（M2+，對應 ADR-005~011）

| 層 | 工具 | ADR |
| :--- | :--- | :--- |
| 資料（主） | FinLab 付費 | ADR-006 |
| 資料（fallback） | FinMind + Shioaji quote + TimescaleDB + DuckDB | — |
| 研究/回測 | 內建 EOD sim + vectorbt（grid / WFA） | ADR-007 / ADR-037 |
| 三模式統一 | Backtest / Paper / Live 共用 strategy code | ADR-008 |
| 統計驗證 | 自寫 PBO/DSR/WFA + quantstats | — |
| 排程 | systemd timer / CLI | ADR-031 |
| 監控/操作台 | FastAPI + React console + TimescaleDB telemetry | ADR-031 |
| 告警 | Discord（從 Telegram 遷移） | ADR-010 |
| API | FastAPI（M5）| — |
| 下單 | Shioaji（永豐金證券）| ADR-008 |

## 目錄結構（v1.1，對應 ADR-011）

完整結構見 [`../dev_docs/08_project_structure_guide.md`](../dev_docs/08_project_structure_guide.md) v1.1。簡覽：

```
backtest_platform/
├── src/backtest_platform/
│   ├── config/                          # 策略參數
│   ├── data/                            # M1 FinMind ETL (fallback adapter)
│   ├── strategies/                      # common (共用回測機制, ADR-026) + inst_flow / momentum / four_layer_resonance
│   ├── adapters/                        # 廠商接口 (data_bundle / data_feed / brokers)
│   ├── research/                        # evaluation ledger / workflows / report packs
│   ├── governance/                      # candidate decision / live-OOS / promotion state
│   ├── risk/                            # pre-trade risk gate
│   ├── runtime/                         # paper/live session runtime
│   ├── validation/                      # PBO / WFA / MC / 績效報表
│   ├── orchestration/                   # CLI + daily flow
│   ├── monitoring/                      # Discord notifier + alert rule definitions
│   └── pipeline.py                      # M1 backward-compat shim
├── tests/                               # pytest
├── legacy/                              # 封存驗證碼（ADR-026；spikes / multi_factor / 舊 scripts，不打包不進 CI）
├── docker/                              # TimescaleDB initdb
└── docs/                                # 工程文件
```

## 快速開始

```bash
cd backtest_platform

# 1. 環境變數（含 FINLAB_API_TOKEN, SHIOAJI_*, DISCORD_*）
cp .env.example .env
# 編輯 .env 填入 token

# 2. 啟動本機 TimescaleDB（localhost-only）
docker compose up -d timescaledb

# 3. 安裝 Python 依賴（uv 取代 poetry，見 ADR-012）
uv sync --extra sprint1 --extra api --extra dev

# 4. 建立 demo ledger + TimescaleDB telemetry，供 127.0.0.1:8083 audit/happy-path 使用
POSTGRES_PASSWORD=quant_local_dev_password uv run python ../scripts/seed_demo_data.py

# 5. 跑單元測試
uv run pytest -v

# 6. 啟動 API
POSTGRES_PASSWORD=quant_local_dev_password uv run uvicorn backtest_platform.api.app:app --host 127.0.0.1 --port 8083
```

## 研究 CLI

```bash
# 預覽標準研究工作流設定
uv run python -m backtest_platform.research.cli build-universe --strategy inst_flow --dry-run
uv run python -m backtest_platform.research.cli doe --strategy inst_flow --dry-run

# 執行審判庭評估（需資料 cache / token）
uv run python -m backtest_platform.research.cli truth-gate --strategy inst_flow
```

## 里程碑

進度詳見 [`../dev_docs/16_wbs_development_plan.md §6`](../dev_docs/16_wbs_development_plan.md)。

## 紀律

- `strategy/archive/v2.md` 是契約，偏離操作需在 Part 6.3 變更紀錄留下文字
- 訊號邏輯抽象成 pure function，三模式（backtest/paper/live）都呼叫同一份
- 每個 milestone 通不過 → 不晉升，不允許「再調一下」
- **狀態追蹤集中在 `dev_docs/16_wbs_development_plan.md`，其他文件不重複**
- **架構變更必寫 ADR**（已 11 份）
- **策略變更必更新 `strategy/archive/v2.md` §6.3**
