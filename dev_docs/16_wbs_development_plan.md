# WBS 開發計劃 — backtest_platform

> **版本：** v2.1 | **更新：** 2026-06-01 | **狀態：** M1 完成 + Sprint 0 scaffolding + Discord 遷移 + 儀表板設計階段完成 / M2 主體待跑
>
> **本文件為「狀態真相源」（Single Source of Truth）** — 其他文件（README / 01 / 02 / 17-24 / ADR）禁止寫 milestone 狀態欄；查狀態請來此檔。
>
> **v2.0 變更**：完整重寫對齊 M2 路線變更（ADR-005~011）— rqalpha → TQuant-Lab、FinMind → FinLab 主、新增 adapters/orchestration/monitoring/dashboard 模組、Discord 取代 Telegram、Sprint 0 spike 工項加入。

---

## 1. 專案總覽

| 項目 | 內容 |
| :--- | :--- |
| **專案名稱** | backtest_platform — 四層共振戰法回測平台 |
| **專案經理** | Self（單人專案） |
| **技術主導** | Self |
| **總工期估算** | M0-M5 約 17 週純工作量；兼職 10h/週 → 約 12 個月（含 buffer） |
| **開始日期** | 2026-05-15（M0 開始） |
| **目前進度** | **M1 完成 + Sprint 0 Gate Conditional Pass (S1 F1 觸發 ADR-013) + Sprint 1 全段完成（Day 1-7：zipline-reloaded + bundle + Algorithm + Taiwan controls + CLI）+ PR #2 merged 進 M2 整合** |
| **目前 git 分支** | `main`（PR #2 M2 整合、PR #3 EOL 正規化 + 儀表板設計 docs 已合入）；`web_design/` UI 設計流水線 + clone 已進 main |
| **最新 commit** | `5714906`（02 PRD v3.0，2026-06-01）|

### 角色（單人多役）

| 角色 | 職責 |
| :--- | :--- |
| PM | 進度追蹤、stage 切換決定 |
| TL | 技術決策、ADR 撰寫 |
| PO | 需求定義（沿用 `strategy/v2.md`）|
| ARCH | 系統架構（含 plan v1.0 / ADR-005~011）|
| DEV | 寫程式 |
| QA | 寫測試、跑驗證 |
| SEC | 安全檢核 |
| SRE | 部署與運維 |

---

## 2. WBS 結構

```
0.0 Sprint 0 (M1→M2 gate)                           ← 新增
├── 0.1 Scaffolding (RUNBOOK + 6 spike 腳本)
├── 0.2 環境準備 (FinLab/TEJ/Shioaji token)
├── 0.3 6 spike 執行
└── 0.4 Gate Review

1.0 專案管理與規劃
├── 1.1 策略規格定稿
├── 1.2 開發計畫與 ADR (含 ADR-005~011)
└── 1.3 進度追蹤 (本檔)

2.0 系統架構與設計
├── 2.1 分層架構設計 (Clean Architecture)
├── 2.2 資料庫 schema 設計
├── 2.3 API / CLI 介面設計
└── 2.4 M2 重組執行 (commit ae869f5)                ← 新增

3.0 資料層
├── 3.A FinMind ETL (M1 完成，現為 fallback)
├── 3.B FinLab Bundle Adapter (M2)                  ← 新增
├── 3.C Universe filter
├── 3.D TimescaleDB upsert
└── 3.E Live Data Feed (M4)                         ← 新增

4.0 策略層
├── 4.1 技術指標
├── 4.2 四層計分
├── 4.3 狀態機 + 訊號優先序
└── 4.4 Zipline algorithm wrapper (M2)              ← 新增

5.0 回測引擎
├── 5.A TQuant-Lab (Zipline) 主骨架 (M2)            ← 重寫 (ADR-005)
├── 5.B vectorbt 副引擎 (M3)                        ← 重寫 (ADR-007)
├── 5.C 雙引擎對齊測試
└── 5.D engines/ CLI

6.0 統計驗證
├── 6.1 績效指標 (quantstats + metrics enum)
├── 6.2 Walk-Forward Analysis (自寫)
├── 6.3 PBO / DSR (自寫，避 pypbo AGPL)             ← 改 (ADR-007 後續)
├── 6.4 Monte Carlo / Bootstrap
└── 6.5 DOE 1-10 執行

7.0 Paper + 實盤
├── 7.A PaperBroker (M4，adapter)                   ← 改 (ADR-008)
├── 7.B ShioajiBroker (M5，adapter)                 ← 改 (ADR-008)
├── 7.C Risk Gate (ex-ante + 熔斷)                  ← 新增 (ADR-011)
└── 7.D Daily orchestration flow (M4)               ← 新增

8.0 監控與儀表板
├── 8.A Streamlit 策略 dashboard (M3 MVP / M5 完整) ← 新增 (ADR-009)
├── 8.B Grafana 系統 dashboard (M4)                 ← 改 (ADR-009)
├── 8.C Discord Alerter (M4)                        ← 新增 (ADR-010)
├── 8.D InfluxDB + Prometheus 整合 (M4)             ← 新增
├── 8.E Backup / Restore
└── 8.F 災難恢復演練

9.0 測試與品質
├── 9.1 單元測試
├── 9.2 整合測試
├── 9.3 對拍測試 (跨引擎，22 §3)                    ← 新增
├── 9.4 訊號重現對齊
└── 9.5 效能測試

10.0 文檔
├── 10.1 策略文檔 (v2.md)
├── 10.2 工程文檔 (dev_docs/，含 M2+ 17-24)         ← 改
├── 10.3 ADR (11 份)                                ← 改
└── 10.4 Runbook (M*_setup)

11.0 跨 milestone 維運                              ← 新增
├── 11.1 Discord 遷移 (從 Telegram)
├── 11.2 文檔結構同步 (目錄重組對齊)
└── 11.3 依賴升級 (pytest-asyncio 等)
```

### 工作包統計

| WBS 模組 | 估計工時 | 已完成 | 進度 | 狀態 |
|:--|:---:|:---:|:---:|:--|
| 0.0 Sprint 0 | 30h | 28h | 93% | ✅ Gate Conditional Pass — 6 spike 全執行（S1 ❌ → ADR-013、S2/S3 ⚠️、S4/S5/S6 ✅） |
| 1.0 專案管理 | 50h | 42h | 84% | 持續 |
| 2.0 系統架構 | 80h | 80h | 100% | ✅ M1 完成 + M2 重組完成 |
| 3.0 資料層 | 120h | 64h | 53% | M1 完成；FinLab bundle / Live feed 待寫 |
| 4.0 策略層 | 70h | 60h | 86% | M1 完成；Zipline wrapper 待 M2 |
| 5.0 回測引擎 | 100h | 30h | 30% | 🚧 Sprint 1 完成（Day 1-7：zipline-reloaded swap + finmind bundle + Algorithm + Taiwan controls + CLI）|
| 6.0 統計驗證 | 180h | 0h | 0% | M3 |
| 7.0 Paper+實盤 | 110h | 0h | 0% | M4-M5 |
| 8.0 監控與儀表板 | 80h | 12h | 15% | Discord notifier 完成 (ADR-010) |
| 9.0 測試品質 | 80h | 44h | 55% | 持續（44 unit + 12 Discord） |
| 10.0 文檔 | 120h | 110h | 92% | 持續 |
| 11.0 跨 milestone | 30h | 24h | 80% | Discord 遷移 + 結構同步完成 |
| **合計** | **1050h** | **448h** | **43%** | M1 完成 + Sprint 0 scaffolding |

兼職（10h/週）→ 預估剩 60 週（約 14 個月）完成 M5；含 buffer 預計 2027-08 全倉上線。

---

## 3. 詳細任務分解

### 模組 0.0 Sprint 0（M1→M2 gate）— 新增

| 編號 | 任務 | 角色 | 工時 | 狀態 | 完成 | 依賴 |
|:--|:--|:--|:---:|:--|:--|:--|
| 0.1.1 | RUNBOOK + 6 spike scaffolding | DEV | 8h | ✅ | 2026-05-31 | — |
| 0.1.2 | pyproject extras (mainframe/data_paid/sprint0) | DEV | 1h | ✅ | 2026-05-31 | — |
| 0.1.3 | .env.example 加 FINLAB/TEJ/INFLUXDB | DEV | 1h | ✅ | 2026-05-31 | — |
| 0.1.4 | gate_review.py 自動匯總工具 | DEV | 2h | ✅ | 2026-05-31 | 0.1.1 |
| 0.2.1 | FinLab `#free` 訂閱啟用 | Self | — | ✅ | 2026-06-01 | S3/S5 已驗證 |
| 0.2.2 | Shioaji 沙箱憑證申請 | Self | — | ✅ | 2026-06-01 | S4 lifecycle 通 |
| 0.2.3 | 本機 `uv sync --extra sprint0`（ADR-012） | DEV | 1h | ✅ | 2026-06-01 | commit ff20df5 / 242550a |
| 0.3.1 | S1 TQuant-Lab + XTAI hello world | DEV | 4h | ❌ | 2026-06-01 | **F1 fail → ADR-013（zipline-reloaded supersede）** |
| 0.3.2 | S2 M1 plug 進 Zipline Algorithm | DEV | 8h | ⚠️ | 2026-06-01 | M1 純函式 callable ✓；wrapper test 被 S1 連帶卡，ADR-003 設計驗證 |
| 0.3.3 | S3 FinLab bundle ingester POC | DEV | 8h | ⚠️ | 2026-06-01 | 寫入邏輯 ✓（10×247 bars）；**FinLab #free 截 2018-12-28，OOS 不可用** |
| 0.3.4 | S4 Shioaji 沙箱範例 | DEV | 4h | ✅ | 2026-06-01 | login + 報價 2330=2355 + 模擬下單 + cancel 完整 |
| 0.3.5 | S5 FinLab live polling | DEV | 3h | ✅ | 2026-06-01 | login + realtime pull + CSV 寫入通 |
| 0.3.6 | S6 Streamlit + TimescaleDB | DEV | 3h | ✅ | 2026-06-01 | TimescaleDB hypertable + 365 行 seed ✓（UI 渲染需 localhost:8501）|
| 0.4.1 | Gate Review + 決策 | PM | 4h | ✅ | 2026-06-01 | gate_review.md（commit 242550a）|

**模組小計**：30h | 完成 93%（scaffolding 12h + 6 spike 執行 + gate 共 ~28h；S2/S3 PARTIAL 不再阻塞，已併入 Sprint 1）

---

### 模組 2.4 M2 重組執行 — 新增（追溯記錄）

| 編號 | 任務 | 角色 | 工時 | 狀態 | 完成 |
|:--|:--|:--|:---:|:--|:--|
| 2.4.1 | 寫 ADR-005~009 (路線變更 5 個) | ARCH | 6h | ✅ | 2026-05-31 |
| 2.4.2 | 寫 ADR-010 Discord 遷移 | ARCH | 1h | ✅ | 2026-05-31 |
| 2.4.3 | 寫 ADR-011 目錄結構決策 | ARCH | 2h | ✅ | 2026-06-01 |
| 2.4.4 | 寫 17/18/20/21/22/23/24 規格文檔 | DOC | 8h | ✅ | 2026-05-31 |
| 2.4.5 | git mv strategy → strategies/four_layer_resonance | DEV | 2h | ✅ | 2026-05-31 |
| 2.4.6 | 新建 adapters/orchestration/monitoring/dashboard 骨架 | DEV | 1h | ✅ | 2026-05-31 |
| 2.4.7 | 改 imports (10 處 code + tests) | DEV | 2h | ✅ | 2026-05-31 |
| 2.4.8 | 文檔合併方案 B (19 → 01, 21~24 cross-ref) | DOC | 3h | ✅ | 2026-05-31 |
| 2.4.9 | 06/08/09 同步 M2 結構 | DOC | 2h | ✅ | 2026-05-31 |

**模組小計**：27h | 進度 100% ✅

---

### 模組 3.0 資料層

| 編號 | 任務 | 角色 | 工時 | 狀態 | 完成 | 依賴 |
|:--|:--|:--|:---:|:--|:--|:--|
| 3.A.1 | FinMind fetch_bundle | DEV | 8h | ✅ | 2026-05-22 | — |
| 3.A.2 | Pydantic schemas | DEV | 4h | ✅ | 2026-05-22 | — |
| 3.A.3 | _normalize_* | DEV | 6h | ✅ | 2026-05-22 | 3.A.1 |
| 3.A.4 | Click CLI + dry-run | DEV | 4h | ✅ | 2026-05-23 | 3.A.1 |
| 3.A.5 | Rate limit + lazy import | DEV | 2h | ✅ | 2026-05-23 | 3.A.1 |
| 3.A.6 | compute_adj_factor | DEV | 6h | ✅ | 2026-05-24 | 3.A.1 |
| 3.A.7 | stock dividend 近似 | DEV | 4h | ✅ | 2026-05-24 | 3.A.6 |
| 3.A.8 | apply_adjustment | DEV | 2h | ✅ | 2026-05-24 | 3.A.6 |
| 3.B.1 | FinLab bundle adapter (skeleton in spike S3) | DEV | 4h | ⏳ | — | 0.3.3 |
| 3.B.2 | FinLab bundle 完整實作 (含日增量) | DEV | 12h | ⏳ | — | 3.B.1 |
| 3.B.3 | FinMind bundle adapter (fallback) | DEV | 4h | ⏳ | — | 3.A.1 |
| 3.B.4 | bundle 註冊與 zipline ingest 流程 | DEV | 4h | ⏳ | — | 3.B.2 |
| 3.C.1 | UniverseConfig dataclass | DEV | 2h | ✅ | 2026-05-25 | — |
| 3.C.2 | apply_filters + rejection_summary | DEV | 6h | ✅ | 2026-05-25 | 3.C.1 |
| 3.D.1 | DBConfig + 連線 context manager | DEV | 3h | ✅ | 2026-05-25 | — |
| 3.D.2 | upsert_frame | DEV | 5h | ✅ | 2026-05-25 | 3.D.1 |
| 3.D.3 | Integration test 跑真實 DB | QA | 4h | ✅ | 2026-05-25 | 3.D.2 |
| 3.D.4 | 新增 9 張 M2+ 表 (見 21 §4) | DEV | 8h | ⏳ | — | M2 啟動 |
| 3.E.1 | FinLab live polling adapter | DEV | 8h | ⏳ | — | 0.3.5 |
| 3.E.2 | Shioaji quote adapter (備援) | DEV | 6h | ⏳ | — | 0.3.4 |
| 3.E.3 | Live feed → TimescaleDB writer | DEV | 6h | ⏳ | — | 3.E.1 |

**模組小計**：120h | 進度 53%

---

### 模組 4.0 策略層

| 編號 | 任務 | 角色 | 工時 | 狀態 | 完成 |
|:--|:--|:--|:---:|:--|:--|
| 4.1.1 | StrategyConfig Pydantic frozen | DEV | 3h | ✅ | 2026-05 |
| 4.1.2 | RSI / Stochastic / MACD weighted | DEV | 6h | ✅ | 2026-05 |
| 4.1.3 | SwingHigh/Low shift(1) 處理 | DEV | 3h | ✅ | 2026-05 |
| 4.2.1 | compute_scores 四層計分 | DEV | 8h | ✅ | 2026-05 |
| 4.2.2 | REQUIRED_COLUMNS 驗證 | DEV | 1h | ✅ | 2026-05 |
| 4.2.3 | net_volume ffill 邏輯 | DEV | 2h | ✅ | 2026-05 |
| 4.3.1 | compute_states 4 狀態 | DEV | 4h | ✅ | 2026-05 |
| 4.3.2 | _evaluate_priority 7 訊號 + 優先序 | DEV | 10h | ✅ | 2026-05 |
| 4.3.3 | compute_signals walk-loop | DEV | 6h | ✅ | 2026-05 |
| 4.3.4 | evaluate_bar dataclass + 函式 | DEV | 5h | ✅ | 2026-05 |
| 4.4.1 | Zipline algorithm wrapper skeleton | DEV | 4h | ⏳ | — |
| 4.4.2 | initialize/handle_data 整合 M1 純函式 | DEV | 6h | ⏳ | — |

**模組小計**：70h | 進度 86%（M1 完成；M2 wrapper 待）

---

### 模組 5.0 回測引擎（M2 重點，zipline-reloaded — 原 TQuant-Lab，ADR-013）

| 編號 | 任務 | 角色 | 工時 | 狀態 | 完成 |
|:--|:--|:--|:---:|:--|:--|
| 5.A.1 | TQuant-Lab 環境裝起來（spike S1）| DEV | 4h | ❌→pivot | 2026-06-01（S1 fail → 5.A.1' 取代）|
| **5.A.1'** | **zipline-reloaded 切換（ADR-013，Sprint 1 Day 1）** | DEV | 4h | ✅ | 2026-06-01（commit d31044a，Gate 1+2 全綠）|
| 5.A.2 | XTAI calendar 驗證 + 對拍 | QA | 2h | ✅ | 2026-06-01（Day 1 Gate 2：243 sessions、春節正確）|
| 5.A.3 | Algorithm + Order routing 學習 | DEV | 8h | ✅ | 2026-06-01（Day 4-5，commit 8b6563b）|
| **5.A.3'** | **FinMind bundle ingester + parquet cache（Sprint 1 Day 2-3）** | DEV | 12h | ✅ | 2026-06-01（commit ed3a987，~360 LOC + 11 tests）|
| **5.A.3''** | **Taiwan Stock Controls（漲跌停 / 整股 / 手續費 / 證交稅）** | DEV | 6h | ✅ | 2026-06-01（commit 8b6563b）|
| 5.A.4 | FourLayerResonance Algorithm 完整實作 | DEV | 16h | 🚧 | — |
| 5.A.5 | 對 2330 IS 回測對齊 M1 pipeline.py | QA | 4h | ⏳ | — |
| 5.A.6 | Portfolio (100 檔) IS 回測 | DEV | 8h | ⏳ | — |
| 5.B.1 | vectorbt adapter (grid 用) | DEV | 12h | ⏳ M3 | — | 2026-06-01 ADR-014 升級恢復排程；validation/cross_check_vectorbt.py 已 smoke-tested |
| 5.B.2 | WFA splitter 自寫 | DEV | 8h | M3 | — |
| 5.B.3 | vectorbt vs Zipline 對拍 | QA | 8h | ⏳ M3 | — | 2026-06-01 ADR-014 升級恢復排程 |
| 5.C.1 | Engine Protocol 抽象 | ARCH | 4h | ⏳ | — |
| 5.D.1 | engines/ Click CLI | DEV | 4h | ✅ | 2026-06-01（commit c980a44，Sprint 1 Day 6-7 收尾 + README） |

**模組小計**：~100h | Sprint 1 全段（Day 1-7）完成 ~30h（30%）— 主骨架切換 + bundle + Algorithm + Taiwan controls + CLI；FourLayerResonance Algorithm 完整實作（5.A.4）為 Sprint 2 起點

---

### 模組 6.0 統計驗證（M3）

| 編號 | 任務 | 工時 | 備註 |
|:--|:--|:---:|:--|
| 6.1.1 | metrics.py 30+ 指標 enum + functions | 16h | 對應 18 §4 taxonomy |
| 6.1.2 | quantstats 報表整合 | 8h | |
| 6.1.3 | 對照 v2.md 4.3.1 綠/黃/紅燈表 | 4h | |
| 6.2.1 | WFA splitter (M3，從 5.B.2 沿用) | (已估) | |
| 6.2.2 | WFA 結果視覺化 | 8h | 接 dashboard 面板 E |
| 6.3.1 | PBO 自寫（避 pypbo AGPL）| 16h | 對 Bailey 論文表 5.2 對拍 |
| 6.3.2 | DSR 自寫 | 8h | |
| 6.4.1 | Bootstrap 1000 iter | 8h | |
| 6.4.2 | Monte Carlo trade permutation | 8h | |
| 6.5.x | 跑 DOE 1-10（doe_research_template）| ~100h | M3 大頭 |

**模組小計**：~180h | M3 大頭

---

### 模組 7.0 Paper + 實盤（M4-M5）

| 編號 | 任務 | 工時 | 備註 |
|:--|:--|:---:|:--|
| 7.A.1 | PaperBroker 即時資料 + 模擬撮合 | 16h | sprint S5/S6 後 |
| 7.A.2 | Paper trade log → TimescaleDB | 4h | |
| 7.A.3 | 3 個月 paper trading 跑 | (時間) | |
| 7.B.1 | ShioajiBroker 抄 TEJ 範例改 | 12h | sprint S4 後 |
| 7.B.2 | 永豐金實盤接通 + 小倉位 | 16h | M5 |
| 7.C.1 | Risk Gate 12 條 ex-ante 規則 | 16h | 對應 24 §2 |
| 7.C.2 | 3 級熔斷狀態機 + kill_switch.sh | 8h | 對應 24 §4 |
| 7.C.3 | Risk metrics 即時計算 | 8h | |
| 7.D.1 | Prefect daily flow 每日排程 | 8h | |
| 7.D.2 | orchestration/cli.py 完整 | 8h | |
| 7.D.3 | 訊號→下單→fills 完整鏈路測試 | 16h | |

**模組小計**：~110h

---

### 模組 8.0 監控與儀表板

| 編號 | 任務 | 工時 | 狀態 |
|:--|:--|:---:|:--|
| 8.A.0 | 儀表板 Design System + 5 面板規格 + Assembly + REST API 契約 (ADR-015) | 12h | ✅ 2026-06-01 |
| 8.A.1 | 面板 A+B+C（React 版，ADR-015；Streamlit MVP 為過渡） | 16h | ⏳ M3 |
| 8.A.2 | 面板 D+E（React 版，ADR-015） | 12h | ⏳ M5 |
| 8.A.3 | Dashboard REST API 層（FastAPI，14 端點；ADR-015 / 21_data_contract §8） | 10h | ⏳ M3 |
| 8.B.1 | Grafana 4 個系統面板 (F-I) | 12h | ⏳ M4 |
| 8.B.2 | Grafana datasource (InfluxDB + TimescaleDB) | 4h | ⏳ M4 |
| 8.C.1 | Discord notifier base | 4h | ✅ 2026-05-31 |
| 8.C.2 | Discord 3 級告警規則引擎 | 6h | ⏳ M4 |
| 8.C.3 | Discord 整合測試 | 2h | ✅（unit tests 12 個） |
| 8.D.1 | InfluxDB metric writer | 4h | ⏳ M4 |
| 8.D.2 | Prometheus exporters | 4h | ⏳ M4 |
| 8.E.1 | pg_dump daily backup | 4h | M5 |
| 8.E.2 | GCS upload script | 4h | M5 |
| 8.F.1 | 災難恢復演練 | 8h | M5 |

**模組小計**：~102h | 進度 ~20%（Discord 完成 + 儀表板設計階段完成：Design System / 5 面板規格 / Assembly / REST API 契約，見 [ADR-015](./adrs/ADR-015-dashboard-design-system-and-react-upgrade.md)）

---

## 4. 進度摘要

| 項目 | 當前值 | 目標值 |
|:--|:---:|:---:|
| 整體進度 | **43%** | 100% |
| M1 完成度 | 100% | 100% |
| Sprint 0 scaffolding | 100% | — |
| Discord 遷移 | 100% | — |
| 單元測試覆蓋率 | ~85%（M1 + Discord） | 80%+ |
| 開放 P0 Bug | 0 | 0 |
| 技術債項目 | 4（見下） | < 3 |
| ADR 數量 | 15（+012 uv / 013 zipline-reloaded / 014 3.1.1 升級 / 015 儀表板 React） | 持續 |
| 文檔完整度 | ~96%（dev_docs 階段 1-7 + 儀表板 Design System / web_design 流水線 / 21 API 契約） | 100% |

### 技術債（M2 待處理）

1. 券商分點欄位全 0（FinMind 免費版無；M2 評估 FinLab 是否補齊）
2. ETL 沒寫 DB（目前只寫 parquet；M2 啟用 db_writer）
3. SwingHigh 用 rolling max 近似 XQ pivot（需抽樣驗證 < 1% 差異）
4. lock file 未引入（M2 啟動後 `uv lock` 產出 `uv.lock` 入版控；ADR-012）

### 已解決的技術債（v1.0 列為待解，現已 fix）

- ~~pytest-asyncio 9.x 不相容~~ → 已 bump to >=0.24（commit `2936119`，2026-06-01）
- ~~rqalpha 自訂 mod 是否值得寫~~ → 廢止；改 TQuant-Lab（ADR-005）

---

## 5. 風險管理

| 風險 | 可能性 | 影響 | 緩解 | 負責 |
|:--|:---:|:---:|:--|:--|
| FinLab 5GB/月流量限制 | 中 | 中 | 一次性歷史回填 → Zipline bundle 永久本地 | Self |
| FinLab 倒閉 / 漲價 | 低 | 高 | FinMind bundle 為 fallback（ADR-006 已備）| Self |
| FinLab 引擎精度爭議 | — | — | 不用 finlab.sim，只用其資料 | — |
| ~~TQuant-Lab 84 stars 社群小~~ | — | — | ADR-013 已切到 zipline-reloaded 主線（社群活躍），此風險解除 | — |
| Sprint 0 S2 fail（M1 plug Zipline 不通）| 低 | 高 | 強制 debug，不退場（is deal-breaker） | Self |
| Sprint 0 S1/S3 fail | 中 | 中 | Hybrid 路線（19 →01 §5.A 已備）| Self |
| 下市股資料源無法解決 | 中 | 高 | 退路：接受偏誤 buffer（+3% CAGR target）| Self |
| 訊號邏輯與 XQ 差異 > 0.5% | 中 | 高 | 100 樣本抽查、修正 _normalize | Self |
| 策略本身無 Edge（IC 測試紅燈）| 高 | 致命 | 接受 → 砍策略 / 改 hypothesis | Self |
| 時間不夠（兼職 + 個人專案）| 高 | 中 | 嚴格按 milestone 早期停止 | Self |
| 個人興趣變動 | 中 | 致命 | 文檔完整 → 隨時可重啟 | Self |

---

## 6. 里程碑

| 里程碑 | 預計日期 | 交付物 | 狀態 |
|:--|:--|:--|:---:|
| **M0** 規格定稿 | 2026-05-25 | `strategy/v2.md` v2.1 | ✅ |
| **M1** 資料+策略骨架 | 2026-05-26 | 44 tests 全綠 + 端到端跑通 | ✅ |
| **M2 預備** Sprint 0 scaffolding + 結構重組 + Discord | 2026-06-01 | scaffolding/docs/結構/Discord 全綠 + 11 ADR | ✅ |
| **Sprint 0 Gate** 6 spike 跑通 | 2026-06-08（暫定） | 6 spike PASS + gate_review.md | ⏳ |
| **M2** zipline-reloaded IS 回測通過 | 2026-08（暫定） | Zipline portfolio backtest + 綠燈（ADR-013）| ⏳ |
| **M3** OOS+統計驗證 | 2026-11 | PBO < 30% + DOE 完整 + Streamlit MVP | ⏳ |
| **M4** Paper trading + 監控 | 2027-02 | 3 個月模擬報告 + Discord + Grafana | ⏳ |
| **M5** 小倉位實盤 | 2027-05 | Shioaji + 完整 dashboard + 1/4 倉位 | ⏳ |
| **全倉** | 2027-08 | 連續 3 月不退化 | ⏳ |

**M2 退場條件**：若 IS 跑不到綠燈 → 回 M0 重新檢視策略
**Sprint 0 退場條件**：見 `01_workflow_manual.md §5.A.4` 決策樹

---

## 7. 開發節奏建議

### 兼職模式（10h / 週）

- 週末：8h 連續寫程式（一個 deep work block）
- 平日晚：2h 文檔 / review / 思考

### Sprint 規劃（2 週為一個 sprint）

| Sprint | 日期 | 重點 | 對應 WBS |
|:--|:--|:--|:--|
| ✅ Sprint -1 | 5/15-5/25 | M0 策略規格定稿 | 1.1 + 10.1 |
| ✅ Sprint 0a | 5/26-5/30 | M1 完成（資料+策略+pipeline）| 3.A + 4.0 + 9.1 |
| ✅ Sprint 0b | 5/31-6/1 | M2 重組 + scaffolding + ADR + Discord | 2.4 + 0.1 + 8.C |
| ✅ Sprint 0c | 6/1（提前完成）| Sprint 0 spike 執行 + Gate Conditional Pass + ADR-013 pivot | 0.2 + 0.3 + 0.4 |
| 🚧 Sprint 1 | 6/1-6/22 | zipline-reloaded 切換 + FinMind bundle + Algorithm + Taiwan controls + IS 回測 | 5.A.1' + 5.A.3' + 5.A.4 |
| Sprint 2 | 6/23-7/6 | 2330 IS 回測對齊 M1 pipeline.py + DiscordNotifier 端到端整合 | 5.A.4 + 5.A.5 |
| Sprint 3 | 7/7-7/20 | Portfolio 100 檔 IS 回測 + M2 acceptance prep | 5.A.6 + 3.D.4 |
| Sprint 4 | 7/21-8/3 | M2 acceptance + M2_backtest_report + FinLab bundle (M3 規劃) | M2 結尾 |
| Sprint 5-8 | 8/4-9/28 | M3 統計驗證 + vectorbt + DOE | 5.B + 6.* |
| ... | ... | 後續 sprint 待近期規劃 | |

### 早期停止 Gate

每個 sprint 結束問三個問題：
1. 是否達成 sprint goal？
2. 是否暴露策略本身的問題？
3. 是否該停下重新規劃？

任一問題答「應該停」→ 進入冷卻 + 重新規劃，**不硬推**。

---

## 8. 更新規則（v2.0 新增）

本檔為「狀態真相源」，更新規則：

| 觸發 | 動作 | 負責 |
|:--|:--|:--|
| 完成一個 task | 標 ✅ + 填完成日期 + 更新模組進度 % | DEV |
| 切 sprint | 更新 §7 Sprint 規劃表 + 整體進度 % | PM |
| milestone 達成 / 失敗 | 更新 §6 里程碑表 | PM |
| 新增 ADR | §2 WBS 結構對應新模組 + §1 ADR 數量 | ARCH |
| 新增技術債 | §4 技術債清單 | DEV |
| 新風險浮現 | §5 風險表 | PM |
| 依賴升級 | §4 已解決的技術債 | DEV |

**更新頻率**：每週末更新一次（兼職模式建議週日晚上）；重大事件即時更新。

**禁止**：其他文件不准寫 milestone 狀態欄；如需提及，用 `[詳見 16 WBS](./16_wbs_development_plan.md)` cross-ref。

---

## 變更紀錄

| 版本 | 日期 | 變更 |
|:--|:--|:--|
| v2.1 | 2026-06-01 | 模組 8.0 加 8.A.0（儀表板設計階段完成 ✅）+ 8.A.3（REST API 層）；8.A.1/A.2 標註 React 化（ADR-015）；§4 ADR 數量 11→15、文檔完整度更新 |
| v2.0 | 2026-06-01 | 完整重寫對齊 M2 路線變更（ADR-005~011）；新增模組 0.0 (Sprint 0)、2.4（M2 重組追溯）、11.0（跨 milestone 維運）；模組 5.0/7.0/8.0 重寫；確立本檔為狀態真相源 |
| v1.0 | 2026-05-26 | 初版（M1 完成時的 baseline） |
