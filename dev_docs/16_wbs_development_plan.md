# WBS 開發計劃 — backtest_platform

> **版本：** v1.0 | **更新：** 2026-05-26 | **狀態：** M1 完成 / M2 啟動中

---

## 1. 專案總覽

| 項目 | 內容 |
| :--- | :--- |
| **專案名稱** | backtest_platform — 四層共振戰法回測平台 |
| **專案經理** | Self（單人專案） |
| **技術主導** | Self |
| **總工期估算** | ~18 個月（兼職，依 milestone 跑） |
| **開始日期** | 2026-05-15（M0 開始） |
| **目前進度** | ~25%（M1 完成） |

### 角色（單人多役）

| 角色 | 職責 |
| :--- | :--- |
| PM | 進度追蹤、stage 切換決定 |
| TL | 技術決策、ADR 撰寫 |
| PO | 需求定義（沿用 strategy/v2.md） |
| ARCH | 系統架構 |
| DEV | 寫程式 |
| QA | 寫測試、跑驗證 |
| SEC | 安全檢核 |
| SRE | 部署與運維 |

---

## 2. WBS 結構

```
1.0 專案管理與規劃
├── 1.1 策略規格定稿
├── 1.2 開發計畫與 ADR
└── 1.3 進度追蹤

2.0 系統架構與設計
├── 2.1 分層架構設計
├── 2.2 資料庫 schema 設計
└── 2.3 API / CLI 介面設計

3.0 資料層開發
├── 3.1 FinMind ETL
├── 3.2 前復權處理
├── 3.3 Universe filter
├── 3.4 TimescaleDB upsert
└── 3.5 下市股資料整合

4.0 策略層開發
├── 4.1 技術指標
├── 4.2 四層計分
├── 4.3 狀態機 + 訊號優先序
└── 4.4 雙週期執行（M2+）

5.0 回測引擎
├── 5.1 rqalpha 整合（含 mod_taiwan_stock）
├── 5.2 vectorbt 整合
├── 5.3 雙引擎對齊
└── 5.4 端到端 pipeline

6.0 統計驗證
├── 6.1 績效指標 (quantstats)
├── 6.2 Walk-Forward Analysis
├── 6.3 PBO / DSR
├── 6.4 Monte Carlo / Bootstrap
└── 6.5 DOE 1-10 執行

7.0 紙上交易 + 實盤
├── 7.1 Paper trading 排程
├── 7.2 Shioaji 整合
├── 7.3 即時監控
└── 7.4 緊急熔斷機制

8.0 監控與運維
├── 8.1 Grafana 儀表板
├── 8.2 Telegram 告警
├── 8.3 Backup / Restore
└── 8.4 災難恢復演練

9.0 測試與品質
├── 9.1 單元測試
├── 9.2 整合測試
├── 9.3 訊號重現對齊
└── 9.4 效能測試

10.0 文檔
├── 10.1 策略文檔（v2.md）
├── 10.2 工程文檔（dev_docs/）
├── 10.3 ADR
└── 10.4 Runbook
```

### 工作包統計

| WBS 模組 | 估計工時 | 已完成 | 進度 | 狀態 |
| :--- | :---: | :---: | :---: | :--- |
| 1.0 專案管理 | 40h | 30h | 75% | 持續 |
| 2.0 系統架構 | 60h | 60h | 100% | ✅ M1 完成 |
| 3.0 資料層 | 80h | 64h | 80% | M2 補下市股 |
| 4.0 策略層 | 60h | 60h | 100% | ✅ M1 完成 |
| 5.0 回測引擎 | 120h | 16h | 13% | 🚧 M2 啟動 |
| 6.0 統計驗證 | 180h | 0h | 0% | M3 |
| 7.0 紙上+實盤 | 100h | 0h | 0% | M4-M5 |
| 8.0 監控運維 | 60h | 8h | 13% | docker compose 已有 |
| 9.0 測試品質 | 60h | 32h | 53% | 持續 |
| 10.0 文檔 | 80h | 64h | 80% | 持續 |
| **合計** | **840h** | **334h** | **40%** | M1 完成 |

兼職（10h/週）→ 預估剩 50 週（約 1 年）完成 M5。

---

## 3. 詳細任務分解

### 模組 3.0 資料層

| 編號 | 任務 | 角色 | 工時 | 狀態 | 完成 | 依賴 |
| :--- | :--- | :--- | :---: | :--- | :--- | :--- |
| 3.1.1 | FinMind ETL fetch_bundle 函式 | DEV | 8h | ✅ | 2026-05-22 | - |
| 3.1.2 | Pydantic schemas (DailyBar/Inst/Chip/Bundle) | DEV | 4h | ✅ | 2026-05-22 | - |
| 3.1.3 | _normalize_* 處理 FinMind raw schema | DEV | 6h | ✅ | 2026-05-22 | 3.1.1 |
| 3.1.4 | Click CLI + dry-run / --output / --db | DEV | 4h | ✅ | 2026-05-23 | 3.1.1 |
| 3.1.5 | Rate limit + lazy import | DEV | 2h | ✅ | 2026-05-23 | 3.1.1 |
| 3.2.1 | compute_adj_factor（cash dividend） | DEV | 6h | ✅ | 2026-05-24 | 3.1.1 |
| 3.2.2 | stock dividend 近似（含 warning） | DEV | 4h | ✅ | 2026-05-24 | 3.2.1 |
| 3.2.3 | apply_adjustment + raw_* 欄位 | DEV | 2h | ✅ | 2026-05-24 | 3.2.1 |
| 3.3.1 | UniverseConfig dataclass | DEV | 2h | ✅ | 2026-05-25 | - |
| 3.3.2 | apply_filters + rejection_summary | DEV | 6h | ✅ | 2026-05-25 | 3.3.1 |
| 3.4.1 | DBConfig + 連線 context manager | DEV | 3h | ✅ | 2026-05-25 | - |
| 3.4.2 | upsert_frame 用 execute_values | DEV | 5h | ✅ | 2026-05-25 | 3.4.1 |
| 3.4.3 | Integration test 跑真實 DB | QA | 4h | ✅ | 2026-05-25 | 3.4.2 |
| 3.5.1 | 評估下市股資料源（TEJ/FinMind/自爬） | ARCH | 4h | ⏳ | — | M1 完成 |
| 3.5.2 | TWSE 下市股清單爬蟲 | DEV | 8h | ⏳ | — | 3.5.1 |
| 3.5.3 | 整合下市股 + 補爬歷史資料 | DEV | 16h | ⏳ | — | 3.5.2 |

**模組小計**：80h | 進度 80%

### 模組 4.0 策略層

| 編號 | 任務 | 角色 | 工時 | 狀態 |
| :--- | :--- | :--- | :---: | :--- |
| 4.1.1 | StrategyConfig Pydantic frozen | DEV | 3h | ✅ |
| 4.1.2 | RSI / Stochastic / MACD weighted | DEV | 6h | ✅ |
| 4.1.3 | SwingHigh/Low shift(1) 處理 | DEV | 3h | ✅ |
| 4.2.1 | compute_scores 四層計分 | DEV | 8h | ✅ |
| 4.2.2 | REQUIRED_COLUMNS 驗證 | DEV | 1h | ✅ |
| 4.2.3 | net_volume ffill 邏輯 | DEV | 2h | ✅ |
| 4.3.1 | compute_states 4 狀態 | DEV | 4h | ✅ |
| 4.3.2 | _evaluate_priority 7 訊號 + 優先序 | DEV | 10h | ✅ |
| 4.3.3 | compute_signals walk-loop | DEV | 6h | ✅ |
| 4.3.4 | evaluate_bar dataclass + 函式 | DEV | 5h | ✅ |
| 4.4.x | 雙週期執行（5min/15min） | DEV | 待估 | M2+ |

**模組小計**：~60h | 進度 100%（M1 範圍）

### 模組 5.0 回測引擎（M2 重點）

| 編號 | 任務 | 角色 | 工時 | 狀態 |
| :--- | :--- | :--- | :---: | :--- |
| 5.1.1 | rqalpha 環境裝起來 | DEV | 4h | ⏳ |
| 5.1.2 | mod_taiwan_stock：交易日曆 | DEV | 8h | ⏳ |
| 5.1.3 | mod_taiwan_stock：T+1、漲跌停、整股 | DEV | 12h | ⏳ |
| 5.1.4 | mod_taiwan_stock：手續費 + 證交稅 | DEV | 4h | ⏳ |
| 5.1.5 | rqalpha_runner 呼叫 evaluate_bar | DEV | 16h | ⏳ |
| 5.1.6 | 單檔 IS 回測對齊 pipeline | QA | 4h | ⏳ |
| 5.2.1 | vectorbt portfolio 模擬器 | DEV | 16h | M3 |
| 5.2.2 | vectorbt_runner 呼叫 compute_signals | DEV | 16h | M3 |
| 5.3.1 | 雙引擎對齊測試 | QA | 8h | M3 |
| 5.4.1 | engines/ Click CLI | DEV | 4h | M2 |

**模組小計**：~120h | M2 後 ~52h 完成

### 模組 6.0 統計驗證（M3）

| 編號 | 任務 | 角色 | 工時 |
| :--- | :--- | :--- | :---: |
| 6.1.1 | quantstats 報表整合 | DEV | 8h |
| 6.1.2 | 對照 v2.md 4.3.1 綠/黃/紅燈表 | QA | 4h |
| 6.2.1 | Walk-Forward 30 windows | DEV | 16h |
| 6.2.2 | WFA 結果視覺化 | DEV | 8h |
| 6.3.1 | PBO/CSCV 演算法（用 pypbo） | DEV | 12h |
| 6.3.2 | DSR 計算 + N 記錄 | DEV | 6h |
| 6.4.1 | Bootstrap 1000 iter | DEV | 8h |
| 6.4.2 | Monte Carlo trade permutation | DEV | 8h |
| 6.5.x | 跑 DOE 1-10（見 doe_research_template） | QA | ~100h |

**模組小計**：~180h | M3 大頭

### 模組 7.0 紙上+實盤（M4-M5）

| 編號 | 任務 | 工時 |
| :--- | :--- | :---: |
| 7.1.1 | Prefect 排程：每日 17:00 ETL + 18:00 訊號 | 8h |
| 7.1.2 | Paper trader：模擬下單 + 對比實際成交 | 16h |
| 7.1.3 | Paper trading 報表（每日 / 每週） | 8h |
| 7.2.1 | Shioaji 環境 + 模擬戶測試 | 16h |
| 7.2.2 | Shioaji_executor 包裝（buy/sell/cancel） | 16h |
| 7.2.3 | 風控 wrapper（停損 / 部位上限 / Heat） | 12h |
| 7.3.1 | Grafana TimescaleDB datasource | 4h |
| 7.3.2 | 5 個關鍵儀表板 | 12h |
| 7.4.1 | 自動熔斷規則 | 8h |

**模組小計**：~100h

---

## 4. 進度摘要

| 項目 | 當前值 | 目標值 |
| :--- | :---: | :---: |
| 整體進度 | 40% | 100% |
| M1 完成度 | 100% | 100% |
| 單元測試覆蓋率 | ~80%（M1 模組） | 80%+ |
| 開放 P0 Bug | 0 | 0 |
| 技術債項目 | 5（M2 待處理） | < 3 |
| 文檔完整度 | 80% | 100% |

### 技術債（M2 待處理）

1. 券商分點欄位全 0（FinMind 免費版無）
2. ETL 沒寫 DB（目前只寫 parquet）
3. SwingHigh 用 rolling max 近似 XQ pivot（需抽樣驗證 < 1% 差異）
4. pytest-asyncio 9.x 不相容（暫加 `-p no:asyncio`）
5. lock file 未引入

---

## 5. 風險管理

| 風險 | 可能性 | 影響 | 緩解 | 負責 |
| :--- | :---: | :---: | :--- | :--- |
| FinMind 免費版功能變動 | 中 | 中 | 升級 sponsor / 切 TEJ | Self |
| 下市股資料源無法解決 | 中 | 高 | 退路：接受偏誤 buffer（+3% CAGR target） | Self |
| 訊號邏輯與 XQ 差異 > 0.5% | 中 | 高 | 100 樣本抽查、修正 _normalize | Self |
| rqalpha T+1 支援不完整 | 中 | 高 | 自寫 mod_taiwan_stock | Self |
| 策略本身無 Edge（IC 測試紅燈） | 高 | 致命 | 接受 → 砍策略 / 改 hypothesis | Self |
| 時間不夠（兼職 + 個人專案） | 高 | 中 | 嚴格按 milestone 早期停止 | Self |
| 個人興趣變動 | 中 | 致命 | 文檔完整 → 隨時可重啟 | Self |

---

## 6. 里程碑

| 里程碑 | 預計日期 | 交付物 | 狀態 |
| :--- | :--- | :--- | :---: |
| **M0** 規格定稿 | 2026-05-25 | `strategy/v2.md` v2.0 → v2.1 | ✅ |
| **M1** 資料+策略骨架 | 2026-05-26 | 48 tests 全綠 + 端到端跑通 | ✅ |
| **M2** IS 回測通過 | 2026-08（暫定） | rqalpha 報表 + 綠燈 | ⏳ |
| **M3** OOS+統計驗證 | 2026-11 | PBO < 30% + DOE 完整 | ⏳ |
| **M4** Paper trading | 2027-02 | 3 個月模擬報告 | ⏳ |
| **M5** 小倉位實盤 | 2027-05 | Shioaji + Grafana + 1/4 倉位 | ⏳ |

**M2 退場條件**：若 IS 跑不到綠燈 → 回 M0 重新檢視策略

---

## 7. 開發節奏建議

### 兼職模式（10h / 週）

- 週末：8h 連續寫程式（一個 deep work block）
- 平日晚：2h 文檔 / review / 思考

### Sprint 規劃（2 週為一個 sprint）

- Sprint 1 (5/26 - 6/8)：M2 啟動，3.5.1 下市股評估 + 5.1.1-5.1.2 rqalpha 環境
- Sprint 2 (6/9 - 6/22)：5.1.3-5.1.4 mod_taiwan_stock 完成
- Sprint 3 (6/23 - 7/6)：5.1.5-5.1.6 rqalpha_runner + IS smoke
- Sprint 4 (7/7 - 7/20)：跑 2330 IS 回測，產出 M2_backtest_report
- Sprint 5 (7/21 - 8/3)：擴展到 universe portfolio
- Sprint 6 (8/4 - 8/17)：M2 acceptance check，準備 M3

### 早期停止 Gate

每個 sprint 結束問三個問題：
1. 是否達成 sprint goal？
2. 是否暴露策略本身的問題？
3. 是否該停下重新規劃？

任一問題答「應該停」→ 進入冷卻 + 重新規劃，**不硬推**。
