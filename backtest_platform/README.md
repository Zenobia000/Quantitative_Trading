# 四層共振戰法回測平台

> 基於 `../strategy/v2.md` 規格書打造的台股量化交易系統（含回測 / paper / 實盤三模式）。

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
| 回測（主骨架） | TQuant-Lab (Zipline 台股 fork) | ADR-005 |
| 回測（副引擎） | vectorbt（grid / WFA） | ADR-007 |
| 三模式統一 | Backtest / Paper / Live 共用 strategy code | ADR-008 |
| 統計驗證 | 自寫 PBO/DSR/WFA + quantstats | — |
| 排程 | Prefect 2.x | — |
| 監控（系統）| InfluxDB + Prometheus + Grafana | ADR-009 |
| 監控（策略）| Streamlit + plotly | ADR-009 |
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
│   ├── strategies/four_layer_resonance/ # 純函式策略 (改名自原 strategy/)
│   ├── adapters/                        # 廠商接口 (data_bundle / data_feed / brokers)
│   ├── engines/                         # vectorbt 副引擎
│   ├── validation/                      # PBO / WFA / MC / 績效報表
│   ├── orchestration/                   # CLI + daily flow
│   ├── monitoring/                      # metric emitter + Discord alerter
│   ├── dashboard/                       # Streamlit + Grafana
│   └── pipeline.py                      # M1 backward-compat shim
├── tests/                               # pytest（44 M1 + 12 Discord）
├── sprint_0_spikes/                     # M2 啟動 gate（6 spike + RUNBOOK）
├── docker/                              # docker-compose + initdb
└── docs/                                # 工程文件
```

## 快速開始

```bash
cd backtest_platform

# 1. 環境變數（含 FINLAB_API_TOKEN, SHIOAJI_*, DISCORD_*）
cp .env.example .env
# 編輯 .env 填入 token

# 2. 啟動容器
docker compose up -d

# 3. 安裝 Python 依賴
poetry install --extras sprint0

# 4. 跑單元測試
poetry run pytest -v

# 5. Sprint 0 spike (M2 啟動前)
poetry run python sprint_0_spikes/s1_tquant_hello_world.py
# ...詳見 sprint_0_spikes/RUNBOOK.md
```

## 里程碑

進度詳見 [`../dev_docs/16_wbs_development_plan.md §6`](../dev_docs/16_wbs_development_plan.md)。

## 紀律

- `strategy/v2.md` 是契約，偏離操作需在 Part 6.3 變更紀錄留下文字
- 訊號邏輯抽象成 pure function，三模式（backtest/paper/live）都呼叫同一份
- 每個 milestone 通不過 → 不晉升，不允許「再調一下」
- **狀態追蹤集中在 `dev_docs/16_wbs_development_plan.md`，其他文件不重複**
- **架構變更必寫 ADR**（已 11 份）
- **策略變更必更新 `strategy/v2.md` §6.3**
