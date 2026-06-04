# WBS 開發計劃 — backtest_platform

> **版本：** v2.9 | **更新：** 2026-06-02 | **狀態：** M1 ✅ + **v0.2–v0.6 後端 waves ✅**（v0.2 統計驗證 pipeline / v0.3 研究迴圈 + gate machine / v0.5 risk + 監控 + paper broker / v0.6 REST API）。四層共振 v3 進場雙窗口 IS gate FAIL（ADR-017；v3.1a/v3.1b 兩方向皆無強跨窗 edge，ADR-019）→ **策略 edge 未證；改採「平台優先」**：先把策略無關聯的可重用後端平台（validation / research / risk / monitoring / API）建完，待出現候選策略即可直接驗證。**前端（v0.4）與實盤（v1.0）仍 gated 於真實 edge 證明**。
> **v2.6 新增（2026-06-02）**：大廠 UI/UX deep-research 對標 → **監控優先 → 研究迴圈優先 pivot（[ADR-018](./adrs/ADR-018-monitoring-to-research-loop-pivot.md)）**；新增**模組 8.G 研究迴圈 UX 與 Run 物件化**（後端契約 8.G.1–8.G.4 為 M0/M2 最高優先，可純 TDD）；現行 A–E 監控降為 live 子視圖、Panel D / Panel B live WS 凍結至 M5。
> **v2.7 新增（2026-06-02）**：反發散切版 — §6 新增**版本 Roadmap**（v0.1 essential MVP〔M0 v3 進場 + IS gate as code 最小後端〕→ v0.2 OOS/WFA/PBO/DSR → v0.3 研究後端 → v0.4 研究前端 → v0.5 paper → v1.0 live）；§7 Sprint 4-12 對齊版本展開（`scrum_board.json` 真相源同步、`sync_wbs.py` 重生）；**鐵律：v3 edge 未證實前不做前端/重功能**。
>
> **本文件為「狀態真相源」（Single Source of Truth）** — 其他文件（README / 01 / 02 / 17-24 / ADR）禁止寫 milestone 狀態欄；查狀態請來此檔。
>
> **v2.0 變更**：完整重寫對齊 M2 路線變更（ADR-005~013）— rqalpha → ~~TQuant-Lab~~ → zipline-reloaded（ADR-013 supersede ADR-005）、FinMind → FinLab 主、新增 adapters/orchestration/monitoring/dashboard 模組、Discord 取代 Telegram、Sprint 0 spike 工項加入。

---

## 1. 專案總覽

| 項目 | 內容 |
| :--- | :--- |
| **專案名稱** | backtest_platform — 四層共振戰法回測平台 |
| **專案經理** | Self（單人專案） |
| **技術主導** | Self |
| **總工期估算** | M0-M5 約 17 週純工作量；兼職 10h/週 → 約 12 個月（含 buffer） |
| **開始日期** | 2026-05-15（M0 開始） |
| **目前進度** | **M1 完成 + Sprint 0 Gate Conditional Pass + Sprint 1 完成 + Sprint 2 完成（pandas 2 升級 ADR-014、wrapper bug fix `evaluate_bar`、validation 三件套 regression_vs_m1 / cross_check_vectorbt / vectorized_pnl_check）/ Sprint 3 active：universe ingest helper（PR #15）+ M2+ DB schema（PR #16）+ coverage 93.74% gate→80（PR #17）+ R-15 doc sweep（PR #18）已合入；live 9 檔 ingest + portfolio 回測為剩餘關鍵路徑** |
| **目前 git 分支** | `main`（6/1–6/2 PR #2/#3/#5/#10/#12/#15/#16/#17/#18 全數合入）；本次 WBS 同步走 `docs/wbs-sync-2026-06-02` |
| **最新 commit** | `a75c0af`（Merge PR #15 data-universe-ingest；後續 main HEAD 隨 merge commit 推進）|

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
├── 5.A zipline-reloaded 主骨架 (M2，原 TQuant-Lab) ← 重寫 (ADR-005 → superseded by ADR-013)
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
| 4.0 策略層 | 70h | 70h | 100% | ✅ M1 完成；Zipline wrapper (4.4.x) 透過 `four_layer_resonance.py` 完成（Sprint 1） |
| 5.0 回測引擎 | 100h | 66h | 66% | 🚧 Sprint 1 ✅ + Sprint 2 ✅ + Sprint 3 5.A.7 ✅（Wave 2 `ingest_universe` helper + Wave 3 `ingest` CLI + live 10 檔 ingest，R14 關閉）；待 5.A.6 portfolio |
| 6.0 統計驗證 | 180h | 64h | 36% | ✅ v0.2–v0.3（metrics/dsr/pbo/wfa/resampling/tearsheet/gate-state/gate-machine/trials，187 tests）；剩 6.1.3 健檢表 / 6.5.x DOE（待候選策略）|
| 7.0 Paper+實盤 | 110h | 48h | 44% | ✅ v0.5 Wave D（PaperBroker + Risk Gate 12 條 + 3 級熔斷，PR #38）+ 7.D orchestration 引擎/CLI（fail-fast staged flow，Prefect-optional）；7.B Shioaji / 7.D real 接線 ⏳ |
| 8.0 監控與儀表板 | 80h | 50h | 63% | ✅ 8.A.0 設計系統 + 8.A.3 REST API v0.6 + 8.C Discord 完整 + 8.D.1 InfluxDB + 8.B Grafana（4 面板 + 自動 provisioning + influxdb 服務）；待 8.A.1/8.A.2 React 面板 / 8.D.2 Prometheus |
| 9.0 測試品質 | 80h | 64h | 80% | Stream D Wave 2 完成 2026-06-02：新增 73 個測試（29 algorithms + 18 cli + 10 pipeline + 16 schemas + 11 finmind_etl extension）→ 190 pass / 1 skip，coverage 66%→93.74%，`--cov-fail-under` 65→**80** ratchet |
| 10.0 文檔 | 120h | 110h | 92% | 持續 |
| 11.0 跨 milestone | 30h | 24h | 80% | Discord 遷移 + 結構同步完成 |
| **合計** | **1050h** | **690h** | **66%** | M1 ✅ + v0.2–v0.6 後端 waves ✅（validation / research / risk / monitoring / API）|

兼職（10h/週）→ 預估剩 60 週（約 14 個月）完成 M5；含 buffer 預計 2027-08 全倉上線。

---

## 3. 詳細任務分解

### 模組 0.0 Sprint 0（M1→M2 gate）— 新增

| 編號 | 任務 | 角色 | 工時 | 狀態 | 完成 | 備註 |
|:--|:--|:--|:--:|:--:|:--|:--|
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

| 編號 | 任務 | 角色 | 工時 | 狀態 | 完成 | 備註 |
|:--|:--|:--|:--:|:--:|:--|:--|
| 2.4.1 | 寫 ADR-005~009 (路線變更 5 個) | ARCH | 6h | ✅ | 2026-05-31 | — |
| 2.4.2 | 寫 ADR-010 Discord 遷移 | ARCH | 1h | ✅ | 2026-05-31 | — |
| 2.4.3 | 寫 ADR-011 目錄結構決策 | ARCH | 2h | ✅ | 2026-06-01 | — |
| 2.4.4 | 寫 17/18/20/21/22/23/24 規格文檔 | DOC | 8h | ✅ | 2026-05-31 | — |
| 2.4.5 | git mv strategy → strategies/four_layer_resonance | DEV | 2h | ✅ | 2026-05-31 | — |
| 2.4.6 | 新建 adapters/orchestration/monitoring/dashboard 骨架 | DEV | 1h | ✅ | 2026-05-31 | — |
| 2.4.7 | 改 imports (10 處 code + tests) | DEV | 2h | ✅ | 2026-05-31 | — |
| 2.4.8 | 文檔合併方案 B (19 → 01, 21~24 cross-ref) | DOC | 3h | ✅ | 2026-05-31 | — |
| 2.4.9 | 06/08/09 同步 M2 結構 | DOC | 2h | ✅ | 2026-05-31 | — |

**模組小計**：27h | 進度 100% ✅

---

### 模組 3.0 資料層

| 編號 | 任務 | 角色 | 工時 | 狀態 | 完成 | 備註 |
|:--|:--|:--|:--:|:--:|:--|:--|
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
| 3.D.4 | 新增 9 張 M2+ 表 (見 21 §4) + db_writer.upsert_positions | DEV | 8h | ✅ | 2026-06-02 | M2 啟動 |
| 3.E.1 | FinLab live polling adapter | DEV | 8h | ⏳ | — | 0.3.5 |
| 3.E.2 | Shioaji quote adapter (備援) | DEV | 6h | ⏳ | — | 0.3.4 |
| 3.E.3 | Live feed → TimescaleDB writer | DEV | 6h | ⏳ | — | 3.E.1 |

**模組小計**：120h | 進度 60%（含 3.D.4 完成）

---

### 模組 4.0 策略層

| 編號 | 任務 | 角色 | 工時 | 狀態 | 完成 | 備註 |
|:--|:--|:--|:--:|:--:|:--|:--|
| 4.1.1 | StrategyConfig Pydantic frozen | DEV | 3h | ✅ | 2026-05 | — |
| 4.1.2 | RSI / Stochastic / MACD weighted | DEV | 6h | ✅ | 2026-05 | — |
| 4.1.3 | SwingHigh/Low shift(1) 處理 | DEV | 3h | ✅ | 2026-05 | — |
| 4.2.1 | compute_scores 四層計分 | DEV | 8h | ✅ | 2026-05 | — |
| 4.2.2 | REQUIRED_COLUMNS 驗證 | DEV | 1h | ✅ | 2026-05 | — |
| 4.2.3 | net_volume ffill 邏輯 | DEV | 2h | ✅ | 2026-05 | — |
| 4.3.1 | compute_states 4 狀態 | DEV | 4h | ✅ | 2026-05 | — |
| 4.3.2 | _evaluate_priority 7 訊號 + 優先序 | DEV | 10h | ✅ | 2026-05 | — |
| 4.3.3 | compute_signals walk-loop | DEV | 6h | ✅ | 2026-05 | — |
| 4.3.4 | evaluate_bar dataclass + 函式 | DEV | 5h | ✅ | 2026-05 | — |
| 4.4.1 | Zipline algorithm wrapper skeleton | DEV | 4h | ✅ | 2026-06-01 | `four_layer_resonance.py` initialize / schedule_function |
| 4.4.2 | initialize/handle_data 整合 M1 純函式 | DEV | 6h | ✅ | 2026-06-01 | Sprint 2 改為 `evaluate_bar` 事件驅動評估（取代原 `compute_signals.iloc[-1]` walk-loop wrapper bug） |

**模組小計**：70h | 進度 100% ✅（M1 完成；M2 wrapper Sprint 1-2 落地）

---

### 模組 5.0 回測引擎（M2 重點，zipline-reloaded — 原 TQuant-Lab，ADR-013）

| 編號 | 任務 | 角色 | 工時 | 狀態 | 完成 | 備註 |
|:--|:--|:--|:--:|:--:|:--|:--|
| 5.A.1 | TQuant-Lab 環境裝起來（spike S1） | DEV | 4h | ❌→pivot | 2026-06-01 | S1 fail → 5.A.1' 取代 |
| **5.A.1'** | **zipline-reloaded 切換（ADR-013，Sprint 1 Day 1）** | DEV | 4h | ✅ | 2026-06-01 | commit d31044a，Gate 1+2 全綠 |
| 5.A.2 | XTAI calendar 驗證 + 對拍 | QA | 2h | ✅ | 2026-06-01 | Day 1 Gate 2：243 sessions、春節正確 |
| 5.A.3 | Algorithm + Order routing 學習 | DEV | 8h | ✅ | 2026-06-01 | Day 4-5，commit 8b6563b |
| **5.A.3'** | **FinMind bundle ingester + parquet cache（Sprint 1 Day 2-3）** | DEV | 12h | ✅ | 2026-06-01 | commit ed3a987，~360 LOC + 11 tests |
| **5.A.3''** | **Taiwan Stock Controls（漲跌停 / 整股 / 手續費 / 證交稅）** | DEV | 6h | ✅ | 2026-06-01 | commit 8b6563b |
| 5.A.4 | FourLayerResonance Algorithm 完整實作 | DEV | 16h | ✅ | 2026-06-01 | commit 8b6563b → Sprint 2 `b5c97de` `evaluate_bar` 校正 |
| 5.A.5 | 對 2330 IS 回測對齊 M1 pipeline.py | QA | 4h | ✅ | 2026-06-01 | Sprint 2 `validation/regression_vs_m1.py`，2330 2024 全年 **100.00% match**，commit `b5c97de` |
| 5.A.6 | Portfolio (10 檔) IS 回測 | DEV | 8h | ✅ 執行（gate FAIL） | 2026-06-02 | Algorithm 原生支援多股，無需另寫 aggregator。雙窗口 portfolio IS：2020-2024 **−1.75%**、2015-2020（ADR-016 凍結窗口）**−4.94%**；2330 5 年僅 14 次進場、勝率 50%、在市場 3.9%。**對 ADR-016 K1/K2/K3 全 FAIL → 觸發退場（[ADR-017](./adrs/ADR-017-m2-is-gate-failed-return-to-m0-entry-redesign.md)）**。參數探針證實約束在進場非出場 |
| **5.A.7.a** | **`ingest_universe` 批次 helper（per-symbol isolation + all-fail raise）** | DEV | 4h | ✅ Wave 2 | 2026-06-02 | commit `90bdfe9` / PR #15；含 mock/stub unit tests，error isolation 單一來源化 |
| **5.A.7.b** | **DEFAULT_UNIVERSE live 10 檔 FinMind ingest → parquet（含 2330 + 9 檔）** | DEV | 2h | ✅ Wave 3 | 2026-06-02 | **R14 關閉**；新增 `ingest` CLI 子命令（+5 mock test）+ runbook（`dev_docs/runbooks/`）；live 跑 2020-2024 5yr `ok=10/10` 35s；解開 7 個 cache-gated 驗證測試（regression_vs_m1 + cross_check_vectorbt 真正執行並通過）→ 252 pass / 4 skip，coverage 95.22%。cache 不入版控（runbook 化） |
| 5.B.1 | vectorbt adapter (grid 用) | DEV | 12h | ✅ Sprint 2 | 2026-06-01 | ADR-014 升級恢復；`validation/cross_check_vectorbt.py` 2330 多範圍全 PASS，誤差 $6-20/$1M，commit `b5c97de` |
| 5.B.2 | WFA splitter 自寫 | DEV | 8h | ✅ v0.2 | 2026-06-02 | `validation/wfa.py`（purge+embargo，rolling/anchored），對拍驗證過 |
| 5.B.3 | vectorbt vs Zipline 對拍 | QA | 8h | ✅ Sprint 2 | 2026-06-01 | 兩段式 acceptance：相對 1% / 絕對 10 bps；3 個 integration test + 2 unit test 全綠 |
| 5.C.1 | Engine Protocol 抽象 | ARCH | 4h | ✅ v0.3 | — | `engines/protocol.py`（Engine Protocol + SimEngine 實作；zipline/vectorbt stub） |
| 5.D.1 | engines/ Click CLI | DEV | 4h | ✅ | 2026-06-01 | commit c980a44，Sprint 1 Day 6-7 收尾 + README |

**模組小計**：~100h | Sprint 1 ~30h + Sprint 2 ~30h + Sprint 3 5.A.7.a helper 4h + 5.A.7.b CLI/live ingest 2h = 66h（66%）— 主骨架 + bundle + Algorithm + Taiwan controls + CLI + wrapper bug fix + validation 三件套 + ADR-014 + `ingest_universe` helper（PR #15）+ `ingest` CLI 子命令 + **live 10 檔 ingest（R14 關閉，7 個 cache-gated 驗證測試解 skip）**；**剩餘關鍵路徑：5.A.6 multi-stock aggregator + portfolio IS 回測**

---

### 模組 6.0 統計驗證（M3）

| 編號 | 任務 | 角色 | 工時 | 狀態 | 完成 | 備註 |
|:--|:--|:--|:--:|:--:|:--|:--|
| 6.1.1 | metrics.py 30+ 指標 enum + functions | — | 16h | ✅ v0.2 | — | `validation/metrics.py`（A/B/C/E 類 12 函式，對照 18 §4，45 tests） |
| 6.1.2 | quantstats 報表整合 | — | 8h | ✅ v0.3 | — | `validation/tearsheet.py`（write_tearsheet + summary_stats，graceful） |
| 6.1.3 | 對照 v2.md 4.3.1 綠/黃/紅燈表 | — | 4h | ⏳ | — | — |
| 6.2.1 | WFA splitter (M3，從 5.B.2 沿用) | — | (已估) | ✅ v0.2 | 2026-06-02 | `validation/wfa.py`（walk_forward_splits，rolling/anchored，purge+embargo） |
| 6.2.2 | WFA 結果視覺化 | — | 8h | ⏳ | — | 接 dashboard 面板 E |
| 6.3.1 | PBO 自寫（避 pypbo AGPL） | — | 16h | ✅ v0.2 | — | `validation/pbo.py`（CSCV，對照 Bailey 2017 §3 驗證過） |
| 6.3.2 | DSR 自寫 | — | 8h | ✅ v0.2 | — | `validation/dsr.py`（PSR + SR* deflate，Bailey&LdP 2014） |
| 6.4.1 | Bootstrap 1000 iter | — | 8h | ✅ v0.2 | — | `validation/resampling.py` bootstrap_ci |
| 6.4.2 | Monte Carlo trade permutation | — | 8h | ✅ v0.2 | — | `validation/resampling.py` permutation p-value |
| 6.5.x | 跑 DOE 1-10（doe_research_template） | — | ~100h | ⏳ | — | M3 大頭 |

**模組小計**：~180h（已完成 64h ≈ 36%）| **v0.2–v0.3 統計驗證 pipeline 後端 ✅**（metrics/dsr/pbo/wfa/resampling/tearsheet 純函式 + gate-state/gate-machine/trials，對照 18 §4 + López de Prado，187 tests）；剩 6.1.3 健檢表 / 6.5.x DOE（策略執行，待有候選）

---

### 模組 7.0 Paper + 實盤（M4-M5）

| 編號 | 任務 | 角色 | 工時 | 狀態 | 完成 | 備註 |
|:--|:--|:--|:--:|:--:|:--|:--|
| 7.A.1 | PaperBroker 模擬撮合 | — | 16h | ✅ v0.5 | — | `adapters/brokers/paper_broker.py`（fills/positions/cash/equity，strategy-agnostic） |
| 7.A.2 | Paper trade log → TimescaleDB | — | 4h | ⏳ | — | — |
| 7.A.3 | 3 個月 paper trading 跑 | — | (時間) | ⏳ | — | — |
| 7.B.1 | ShioajiBroker 抄 TEJ 範例改 | — | 12h | ⏳ | — | sprint S4 後 |
| 7.B.2 | 永豐金實盤接通 + 小倉位 | — | 16h | ⏳ | — | M5 |
| 7.C.1 | Risk Gate 12 條 ex-ante 規則 | — | 16h | ✅ v0.5 | — | `risk/risk_gate.py`（EX-001~012 + §2.2 評估順序，純函式；對應 24 §2） |
| 7.C.2 | 3 級熔斷狀態機 | — | 8h | ✅ v0.5 | — | `risk/circuit_breaker.py`（L1/L2/L3→HALTED latched；EX-012 接 shared BreakerState；對應 24 §4）；kill_switch.sh ⏳ |
| 7.C.3 | Risk metrics 即時計算 | — | 8h | ⏳ | — | — |
| 7.D.1 | Prefect daily flow 每日排程 | — | 8h | 🟡 | 2026-06-04 | `orchestration/daily_flow.py` fail-fast staged 引擎（ETL→signals→risk→orders→log，collaborator 注入）+ **Prefect-optional**（`as_prefect_flow`：未裝 prefect 則 inline fallback，prefect 非硬依賴）|
| 7.D.2 | orchestration/cli.py 完整 | — | 8h | 🟡 | 2026-06-04 | `orchestration/cli.py` run〔--dry-run/--real〕+ list-stages；dry-run 跑 no-op demo 管線（安全），real 套 build_daily_stages；18 測試、模組 94% cov |
| 7.D.3 | 訊號→下單→fills 完整鏈路測試（real collaborator 接線） | — | 16h | ⏳ | — | engine/CLI 已備（7.D.1/2），待接真實 ETL/signals/RiskGate/PaperBroker collaborators |

**模組小計**：~110h

---

### 模組 8.0 監控與儀表板

| 編號 | 任務 | 角色 | 工時 | 狀態 | 完成 | 備註 |
|:--|:--|:--|:--:|:--:|:--|:--|
| 8.A.0 | 儀表板 Design System + 5 面板規格 + Assembly + REST API 契約 (ADR-015) | — | 12h | ✅ | 2026-06-01 | — |
| 8.A.1 | 面板 A+B+C（React 版，ADR-015；Streamlit MVP 為過渡） | — | 16h | ⏳ | — | M3 |
| 8.A.2 | 面板 D+E（React 版，ADR-015） | — | 12h | ⏳ | — | M5 |
| 8.A.3 | Dashboard REST API 層（FastAPI；ADR-015 / 21_data_contract §8） | — | 10h | ✅ v0.6 | 2026-06-02 | `api/`（app 工廠 + runs/gate/metrics/presets 4 router，11 端點，統一信封，100% cov）。**提前交付**（原 M3）；研究迴圈讀寫面已上，監控/風控面板端點待 Wave D 合入後補（見 doc 06 §9.4） |
| 8.B.1 | Grafana 4 個系統面板 (F-I) | — | 12h | 🟡 | 2026-06-04 | `docker/grafana/dashboards/0{1-4}_*.json`（F ETL / G API quota / H 排程 / I 資源，Flux 對 influx_writer measurements）+ 15 結構驗證測試；live import reviewer-verified；node_exporter/data_quality/api_error emitter 待補（follow-up）|
| 8.B.2 | Grafana datasource (InfluxDB + TimescaleDB) | — | 4h | ✅ | 2026-06-04 | `docker/grafana/provisioning/`（InfluxDB datasource 自動載入 + dashboard provider）+ docker-compose 加 **influxdb:2.7 服務**（補齊缺的 metrics DB）+ grafana provisioning mount |
| 8.C.1 | Discord notifier base | — | 4h | ✅ | 2026-05-31 | — |
| 8.C.2 | Discord 3 級告警規則引擎 | — | 6h | ✅ v0.5 | — | `monitoring/alert_rules.py`（Critical/High/Info + 去重 30min + 靜默窗 TWT） |
| 8.C.3 | Discord 整合測試 | — | 2h | ✅ | — | unit tests 12 個 |
| 8.D.1 | InfluxDB metric writer | — | 4h | ✅ v0.5 | — | `monitoring/influx_writer.py`（line protocol + graceful degradation） |
| 8.D.2 | Prometheus exporters | — | 4h | ⏳ | — | M4 |
| 8.E.1 | pg_dump daily backup | — | 4h | ⏳ | — | M5 |
| 8.E.2 | GCS upload script | — | 4h | ⏳ | — | M5 |
| 8.F.1 | 災難恢復演練 | — | 8h | ⏳ | — | M5 |

**模組小計**：~102h | 進度 ~37%（Discord 完整〔notifier + 3 級規則引擎 + 整合測試〕+ InfluxDB writer + 儀表板設計階段：Design System / 5 面板規格 / Assembly / REST API 契約，見 [ADR-015](./adrs/ADR-015-dashboard-design-system-and-react-upgrade.md) + **8.A.3 REST API 層 v0.6 提前交付**〔FastAPI 11 端點、100% 覆蓋〕）

---

### 模組 8.G 研究迴圈 UX 與 Run 物件化（[ADR-018](./adrs/ADR-018-monitoring-to-research-loop-pivot.md)，最高槓桿補強）— 新增

> 大廠 UI/UX deep-research 對標（`web_design/03_uiux_benchmark_and_reinforcement_plan.md`）：現行 A–E 全是 live 監控，缺研究迭代迴圈 UX。**鐵律：補齊研究迴圈前不再擴張監控 panel（Panel D / Panel B live WS 凍結至 M5）**。後端契約先行（純 Python/CLI 可 TDD），最薄前端隨 ADR-015 React 化批次補。

| 編號 | 任務 | 角色 | 工時 | 狀態 | 完成 | 備註 |
|:--|:--|:--|:--:|:--:|:--|:--|
| 8.G.0 | UI/UX deep-research 對標 + 10 維度差距 + 7 流程圖 + roadmap（ADR-018 證據包） | — | 8h | ✅ | 2026-06-02 | — |
| 8.G.1 | `runs` 主表 DDL（21 §4）+ 4 張時序表 run_id 補 FK（Run 物件化 single source of truth） | — | 6h | ⏳ | — | M0/M2 |
| 8.G.2 | RunConfig Pydantic schema（IS/OOS 區間 + 成本攤平 + engine + range/step + hypothesis 預登記） | — | 6h | 🟡 v0.1-min | 2026-06-02 | `research/run_config.py`（IS 區間 + 成本 + engine + hypothesis 強制欄已實作）；OOS 鎖死 / range-step sweep / hypothesis 系統鎖死延後 v0.2 |
| 8.G.3 | IS→WFA→OOS 不可逆狀態機 + OOS sealed vault + 硬門檻 dict | — | 8h | ✅ v0.1+v0.3 | — | M0/M2；`gate_state.py`(IS gate dict,v0.1) + `gate_machine.py`(ValidationGate 狀態機+OOSSealedError sealed vault,v0.3) |
| 8.G.4 | 試驗次數計數 → DSR deflate | — | 4h | ✅ v0.3 | — | `validation/trials.py`（TrialsCounter + trials_deflated_criterion 接 dsr） |
| 8.G.5 | CLI：run-is/runs(v0.1) + sweep/compare(v0.3) + validate + promote-check(v0.6) ✅ | — | 8h | ✅ v0.6 | 2026-06-03 | `research/cli.py` run-is〔+`--tearsheet`〕/runs/sweep/compare/**validate**/**promote-check**；`validate`=接 `ValidationGate` 推進 IS→WFA→OOS 工作流 gate（IS 階段）+ OOS sealed-vault 狀態；`promote-check`=唯讀晉升閘，讀 `validation_status`（顯式欄優先，否則推導 IS 狀態），僅 APPROVED 才 ELIGIBLE 否則列待完成階段（防未驗證策略上線）。模組封頂 |
| 8.G.6 | 設計系統 token 擴充（categorical/diverging/sequential 受控色盤）+ 研究級元件規格（CodeEditor / ResearchTable / CompareChart / FirstRunEmptyState / Cmd-K） | — | 6h | ⏳ | — | M0/M2 |
| 8.G.7 | 前端 Research 工作區（/research/runs · /runs/new · /runs/:id Run Report · /compare · /sweep · /validate）+ Cmd-K | — | 20h | ⏳ | — | M3 |
| 8.G.8 | 前端 Promotion stepper（/research/promote）+ A–E 改 /monitor/* 子視圖 + Panel E 重定位 Validate gate | — | 10h | ⏳ | — | M5 |

**模組小計**：~76h（已完成 ~49h ≈ 64%）| 後端契約 ~80%（8.G.0 對標 + 8.G.3 gate_state/gate_machine + 8.G.4 trials→DSR + 8.G.5 CLI 全套〔run-is/runs/sweep/compare/validate/promote-check〕✅；剩 8.G.2 RunConfig OOS/sweep 鎖死 + 8.G.1 runs 主表 DDL）；前端 8.G.6–8.G.8 0%（edge 未證前延後）

---

## 4. 進度摘要

| 項目 | 當前值 | 目標值 |
|:--|:---:|:---:|
| 整體進度 | **66%**（與 §2 工作包統計合計一致；v0.2–v0.6 後端 waves 已合併） | 100% |
| M1 完成度 | 100% | 100% |
| Sprint 0 scaffolding | 100% | — |
| Discord 遷移 | 100% | — |
| 單元測試覆蓋率 | **92.34%**（v0.2–v0.6 merged 714 pass / 4 skip；`--cov-fail-under` gate 80） | 80%+ |
| 開放 P0 Bug | 0 | 0 |
| 技術債項目 | 4（見下） | < 3 |
| ADR 數量 | 19（+017 IS gate FAIL → 回 M0 / **018 監控→研究迴圈 pivot** / **019 v3 進場重設：兩方向無 edge**） | 持續 |
| 文檔完整度 | ~96%（dev_docs 階段 1-7 + 儀表板 Design System / web_design 流水線 / 21 API 契約） | 100% |

### 技術債（M2 待處理）

1. 券商分點欄位全 0（FinMind 免費版無；M2 評估 FinLab 是否補齊）
2. ETL 沒寫 DB（目前只寫 parquet；M2 啟用 db_writer）
3. SwingHigh 用 rolling max 近似 XQ pivot（需抽樣驗證 < 1% 差異）
4. ~~lock file 未引入~~ → **✅ 已解決（2026-06-04）**：實際上 `uv.lock` 早已存在，但因 pyproject `pytest>=8.0` 無上界把 pytest 釘在 9.0.3（pytest 9 移除 `Package.obj` → pytest-asyncio 1.4.0 在 collectstart 仍呼叫 → 全 `tests/<pkg>/` collection 中斷），且 `.venv` 停在 zipline-reloaded 3.0.4（對 numpy 1 編譯，與 numpy 2 ABI 斷裂）+ 缺 `api`(fastapi)/`engines`(vectorbt) extras。修：pyproject pin `pytest>=8.3,<9`（+`pytest-asyncio<2`）+ relock（釘死 pytest 8.4.2 / zipline 3.1.1 / numpy 2 / vectorbt 1.0 / fastapi 0.136.3）+ env sync → 全 suite **729 pass / 4 skip / coverage 93.54%（gate 80）一鍵可驗證**（ADR-012；自主開發 verify-green 前置）

### 已解決的技術債（v1.0 列為待解，現已 fix）

- ~~pytest-asyncio 9.x 不相容~~ → 已 bump to >=0.24（commit `2936119`，2026-06-01）
- ~~rqalpha 自訂 mod 是否值得寫~~ → 廢止；改 zipline-reloaded（ADR-005 → ADR-013）
- ~~`_format_perf_summary` action_totals 來自 zipline `record()` ffill 欄位加總（單筆 buy 讀成 ~1000 筆）~~ → 改從 `transactions` 算真實成交筆數 + regression test（2026-06-02，ADR-017 §2.3）

---

## 5. 風險管理

| 風險 | 可能性 | 影響 | 緩解 | 負責 |
|:--|:---:|:---:|:--|:--|
| FinLab 5GB/月流量限制 | 中 | 中 | 一次性歷史回填 → Zipline bundle 永久本地 | Self |
| FinLab 倒閉 / 漲價 | 低 | 高 | FinMind bundle 為 fallback（ADR-006 已備）| Self |
| FinLab 引擎精度爭議 | — | — | 不用 finlab.sim，只用其資料 | — |
| ~~TQuant-Lab 84 stars 社群小~~ | — | — | ADR-013 已切到 zipline-reloaded 主線（社群活躍），此風險解除 | — |
| **R-15 dev_docs 散落 TQuant-Lab 引用** | — | — | ✅ **Complete** (2026-06-02) — 8 份 docs（INDEX/02/05/08/17/18/22/16）已 sweep 至 ADR-013/014 路線 | Self |
| Sprint 0 S2 fail（M1 plug Zipline 不通）| 低 | 高 | 強制 debug，不退場（is deal-breaker） | Self |
| Sprint 0 S1/S3 fail | 中 | 中 | Hybrid 路線（19 →01 §5.A 已備）| Self |
| 下市股資料源無法解決 | 中 | 高 | 退路：接受偏誤 buffer（+3% CAGR target）| Self |
| 訊號邏輯與 XQ 差異 > 0.5% | 中 | 高 | 100 樣本抽查、修正 _normalize | Self |
| **R9 策略本身無 Edge** | 高 | 致命 | 🟠 **緩解中（v3 進場 v0.1 IS gate FAIL → 待 v3.1 結構修正）**（2026-06-02）：v3 機制已實作（ADR-019；16 測試、signals.py 100%、v2 regression 釘死）。**雙窗口 IS 已跑（`scripts/v3_double_window_is.py`，3 固定 config 不 sweep）→ 🔴 RED**：v3 放寬雙窗皆淨負（portfolio CAGR −4.48%/−2.38%）且**劣於 v2**（−1.08%/+0.44%），勝率下降；**冒煙槍＝structure==1 中段進場占 72–76% ≫ 30% 健檢門檻**（`min_structure=1` 灌入箱中無人區，正中波段 lens 預警）。exit 搭配證實有效（v3>v3_f1、持有 6.1 vs 4.5）。**🟢 真引擎校準（Step 1）：zipline 確認 RED** — config 注入後用真 event-driven 引擎重跑，2020-2024 v2 +1.03%/Sharpe+0.20 → v3 −5.20%/Sharpe−0.43（崩盤、劣於 v2），交易 466 vs 103（4.5×）；**兩引擎 Sharpe 吻合 ~0.01**（sim vs zipline）→ 背書 RED 並驗證 sim 可信、解除 harness 可信度風險。**判決**：未過 v0.1 gate，**不進 v0.2**。**進度**：Step 1 校準 ✅ → **Step 2 `validation/gate_state.py` ✅**（ADR-016+健檢純函式 dict）→ **Step 3 IS harness ✅**（`research/{run_config,is_harness,runs_store,cli}.py`：`run-is --preset v3 --hypothesis ... → gate 逐條綠紅 + runs 落表`；真 v3 2020-2024 判 FAIL，含 K3 滑點 Sharpe −1.03）→ **Step 4 結構競賽 ✅（A+B 跑完，gate review §7-§8）**：三輪（v3 全放鬆 / dirB 突破only / v3.1a +箱頂回測）→ **dirB 最佳但無強 edge**（最佳僅 2020-2024 +1.23%/Sharpe0.41，離 18%/1.0 很遠；2015-2020 仍 -0.72%；任何 structure==1 進場都更差）。**認賠線：struct1<30%✅+邊際單不劣v2✅+同號為正❌=2/3**。**收斂：四層共振在此 large/mid-cap universe 無強跨窗 edge——進場閘已非 bottleneck（dirB 進場乾淨），標的 alpha 不足。下一步＝escalate（換中小型動能 universe 候選 D / 重訂 edge / 砍），非再調進場。** → **Step 5 候選 D 設計定稿（2026-06-03，[ADR-020](./adrs/ADR-020-candidate-d-smallcap-universe-escalation.md) 提案中）**：機制凍結，只換 point-in-time 中小型動能 universe（市值 rank 51-300、季 rebalance、流動性 ≥2000 萬、反 survivorship 含下市股），成本上調（+0.4% buffer、K3 滑點 0.5%），驗 dir/chip 在中小型的鑑別力（spec `2026-06-03-candidate-d-smallcap-universe-design.md`）。**go/no-go gating＝資料 spike**：~250 檔中小型股的 FinLab 進階券商分點 + FinMind OHLCV/法人 2015+ 覆蓋（需使用者 token）；🔴 不足即回 M0 評估去 chip 變體或砍。 → **Step 6 universe builder hermetic TDD ✅（2026-06-04，`data/universe_builder.py` + 14 合成測試）**：spec §8 允許資料 spike 前先建，point-in-time 選股 + 反 survivorship 三鐵律已釘死、與資料解耦；token 進 env 即可一指令觸發雙窗 IS。**前置加碼（免費診斷）：先用現有 FinMind 三大法人量化 chip 層邊際貢獻（IC / ablation），chip 無訊號即不買 FinLab、回 M0；有訊號才付費補券商分點**（避免 edge 未證先燒 ~10k）。 → **Step 7 §3 資料 spike ✅（2026-06-04，`scripts/candidate_d_data_spike.py` live FinMind）**：中小型 OHLCV+法人 2015-2024 **充分可得**（樣本 12 檔 85%/86% 平均覆蓋、候選池 1948 檔、含下市股 2447=0 列驗反 survivorship）→ **L1/L2/L4 🟢**；**兩道閘待使用者決策**：(a) universe builder 市值排名輸入（FinMind 3 個常見 dataset 皆無 → 可改 turnover proxy 全免費）🟡、(b) **L3 券商分點＝FinLab 付費** 🔴（不買則 Candidate D 亦只能 L3 退化跑，與大型股結論同條件）。**full 重驗待 (a)(b) 定案才啟動**。詳見 `candidate_d_data_spike_result_2026-06-04.md` + §6-§8 + ADR-020 | Self |
| 時間不夠（兼職 + 個人專案）| 高 | 中 | 嚴格按 milestone 早期停止 | Self |
| 個人興趣變動 | 中 | 致命 | 文檔完整 → 隨時可重啟 | Self |
| ~~**R14** DEFAULT_UNIVERSE live ingest 尚未執行~~ | — | — | ✅ **已關閉**（2026-06-02）：`ingest` CLI 子命令 + runbook 落地，live 跑 2020-2024 10 檔 `ok=10/10`，parquet cache 就緒（不入版控）；7 個 cache-gated 驗證測試解 skip 並通過。剩 5.A.6 portfolio 回測（與 R14 無關）| Self |

---

## 6. 里程碑

| 里程碑 | 預計日期 | 交付物 | 狀態 |
|:--|:--|:--|:---:|
| **M0** 規格定稿 | 2026-05-25 | `strategy/v2.md` v2.1 | ✅ |
| **M1** 資料+策略骨架 | 2026-05-26 | 44 tests 全綠 + 端到端跑通 | ✅ |
| **M2 預備** Sprint 0 scaffolding + 結構重組 + Discord | 2026-06-01 | scaffolding/docs/結構/Discord 全綠 + 11 ADR | ✅ |
| **Sprint 0 Gate** 6 spike 跑通 | 2026-06-08（暫定） | 6 spike PASS + gate_review.md | ⏳ |
| **M2** zipline-reloaded IS 回測通過 | 2026-08（暫定） | Zipline portfolio backtest + 綠燈（ADR-013）| ❌ **IS gate FAIL**（2026-06-02，ADR-017）→ 退場條件觸發，回 M0 重設進場 |
| **M3** OOS+統計驗證 | 2026-11 | PBO < 30% + DOE 完整 + Streamlit MVP | ⏳ |
| **M4** Paper trading + 監控 | 2027-02 | 3 個月模擬報告 + Discord + Grafana | ⏳ |
| **M5** 小倉位實盤 | 2027-05 | Shioaji + 完整 dashboard + 1/4 倉位 | ⏳ |
| **全倉** | 2027-08 | 連續 3 月不退化 | ⏳ |

**M2 退場條件**：若 IS 跑不到綠燈 → 回 M0 重新檢視策略
**Sprint 0 退場條件**：見 `01_workflow_manual.md §5.A.4` 決策樹

### M2 acceptance「綠燈」門檻（凍結於 [ADR-016](./adrs/ADR-016-m2-acceptance-kpi-freeze.md)）

| 指標 | M2 IS 門檻 | 來源 |
|:--|:--:|:--|
| **CAGR** | **> 18%**（含生存者偏誤 buffer） | `01_workflow_manual.md` §6 + `strategy/v2.md` §4.3.1 |
| **Sharpe** | **> 1.0** | `02_project_brief_and_prd.md` §成功指標 |
| **滑點 0.3% 下 Sharpe** | **> 1.0**（穩健性測試） | `02_project_brief_and_prd.md` §成功指標 |

任一項不達標 → 觸發退場條件回 M0。M3 OOS 門檻（OOS Sharpe > 0.6 × IS、PBO < 30%、DSR > 0.95）見 `01_workflow_manual.md` §6。


### 版本 Roadmap（反發散切版，2026-06-02 收斂）

> **反發散原則（一句）**：唯一真 blocker 是「策略 edge」而非平台功能——每個版本的 exit 都綁一個可客觀驗收的 gate。**v0.2–v0.6 後端基建已先行建完（策略無關聯、可重用，見下方交付現況）；前端（v0.4）與實盤（v1.0）仍在 v3 edge 未證實前不往前推進**。
>
> **essential MVP 邊界（v0.1）**：能把 v3 進場 edge 客觀驗出真偽的最小路徑＝M0 v3 進場重設 + 讓每次迭代「客觀、可重現、可守門」的最小後端護欄。**明確不含任何前端、不含 sweep/compare/Cmd-K/promotion UI、不含 OOS sealed vault 完整版。**

#### 版本切分表

| 版本 | 名稱 | 里程碑 | 目標（一句） | 含哪些 WBS | Exit Criteria |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **v0.1** | edge 驗證最小迴圈（**Essential MVP**） | M0/M2 | v3 進場重設 + 讓迭代客觀可守門的最小後端 | 4.0 v3進場（候選 A/B/C）、8.G.3-min（IS gate 硬門檻 dict as code）、8.G.1-min（runs 主表最小 DDL）、8.G.2-min（RunConfig 最小 schema）、8.G.5-min（CLI run-new/run-list/validate is） | v3 進場重設完成且可重現；對 portfolio 雙窗口（2015-2020 + 2020-2024）跑 IS，`gate_state.py` 自動輸出 ADR-016 K1/K2/K3 + min_trades 逐條 PASS/FAIL + 差距值並落 runs 表。**雙向 gate**：(綠) 全 PASS → 開 v0.2；(紅) 任一 FAIL → 走 ADR-017 退場路徑回 M0 再設或評估砍策略，**不得**推進 v0.2+ |
| **v0.2** | OOS + 統計顯著性驗證 | M3 | IS→WFA→OOS 不可逆 gate 就位後實跑 OOS | 8.G.3-full（IS→WFA→OOS 狀態機 + OOS sealed vault）、8.G.2-full（OOS 區間系統鎖死 + hypothesis 預登記）、8.G.4（trials→DSR deflate）、8.G.1-full（4 張時序表補 run_id FK）、5.B.2（WFA splitter）、6.3（PBO CSCV + DSR） | sealed vault 在 IS 未 PASS 前擋住 OOS 存取且留痕（TDD 覆蓋「未過 gate 讀 OOS 被擋」「狀態不可回退」）；v3 達 OOS Sharpe > 0.6×IS、PBO < 30%、DSR > 0.95（含 trials deflate）。任一紅線自動擋下游 |
| **v0.3** | 統計驗證完整化 + 多 run 比較後端（CLI-only） | M3 | edge 穩健性蓋章（高原非孤立尖峰），全程 code-first | 6.1（metrics.py 30+ 指標 enum + quantstats）、6.4（Bootstrap + Monte Carlo）、6.5.x（DOE 1-10）、8.G.5-full（CLI 補 sweep/compare/promote check）、5.C.1（Engine Protocol 抽象） | DOE 關鍵 run 完成、PBO < 30% 維持；sweep heatmap 資料（CLI 輸出）顯示穩健高原；compare CLI 可對多 run 做 baseline delta；promote check CLI 可讀 validation_status。此版完成＝edge 已被穩健證明 |
| **v0.4** | 研究工作區最薄前端（React 化第一批） | M3 | 把 v0.1-v0.3 的後端真相源最薄前端化（純讀） | 8.G.6（設計系統 token 擴充：categorical/diverging 色盤 + 收 teal drift）、8.G.7-partial（/research/runs Runs Table + /runs/:id Run Report + /validate）、8.A.3（Dashboard REST API 層 FastAPI）、8.A.1（Panel A/B/C React 版）、FirstRunEmptyState 元件 | Runs Table 可瀏覽/排序/pin baseline；Run Report 複用 Panel A 元件渲染 equity/drawdown/rolling/heatmap + Reproduce 卡；Validate gate 前端呈現 IS gate 逐條綠/紅。**前端 0 新增策略邏輯（純讀後端 run 真相源）** |
| **v0.5** | Paper trading + 監控接管 | M4 | edge 證實後才接 broker + 啟監控面板 | 7.A（PaperBroker + trade log）、7.C（Risk Gate 12 條 + 3 級熔斷）、7.D（Prefect daily flow + orchestration CLI）、8.C.2（Discord 3 級告警規則引擎）、8.B（Grafana 系統面板）、8.D（InfluxDB + Prometheus） | 3 個月 paper trading 報告產出且不退化（對照 live_start_date 邊界）；Risk Gate ex-ante 12 條生效；Discord 三級告警 + Grafana 系統面板運作 |
| **v1.0** | 小倉位實盤 + 晉升前端收尾 | M5 | Shioaji 小倉位接通 + 晉升狀態機強制 gate | 7.B（ShioajiBroker + 1/4 倉位）、8.G.8（Promotion stepper + A-E 改 /monitor/* + Panel E 重定位）、8.A.2（Panel D+E React 版）、8.G.7-full（/research/compare + /sweep + Cmd-K）、8.E/8.F（備份 + 災難恢復演練） | Shioaji 小倉位實盤接通 + 1/4 倉位運行；Promotion stepper 強制 gate（每階段綠燈才解鎖 + audit log）；連續觀察不退化即評估全倉 |
| **v1.x** | Roadmap 層（進階研究 UX / 運維） | post-M5 | 高原視覺化、進階防過擬合 UX、Grafana F-I 等 | sweep/compare 視覺化（heatmap + parallel coordinates）、power gauge UI、四層共振歸因下鑽、trade markers 疊 K 線、Grafana 進階面板 | 依實際使用頻次按需疊加，無硬 exit |

> **📊 交付現況（2026-06-02 sync）**：v0.2–v0.6 的**後端/基建已全部建完並合併進 main**（v0.2 validation 統計 pipeline〔metrics/dsr/pbo/wfa/resampling〕、v0.3 research 研究迴圈 + gate machine〔run loop / runs ledger / sweep / compare / OOS sealed vault / trials→DSR〕、v0.5 risk + 監控 + paper broker〔Risk Gate 12 條 / 3 級熔斷 / PaperBroker / Discord 規則引擎 / InfluxDB〕、v0.6 REST API〔FastAPI 11 端點〕）。但這些是**策略無關聯的可重用基建**——各版的 **edge-gated exit criteria 尚未達成**（四層共振 v3 兩方向皆無 edge，ADR-017/019），唯 v0.6（純基建）的 exit 已滿足。故定調**「平台優先」**：基建 ✅ 就緒、待候選策略出現即可直接驗證；**前端（v0.4）與實盤（v1.0）仍 gated 於真實 edge**。§7 Sprint 看板（`scrum_board.json` 真相源）的對齊待另跑 `sync_wbs.py`。

#### essential MVP（v0.1）邊界說明

**包含（不做就無法客觀驗出 v3 edge）**：
- (a) M0 v3 進場重設設計與實作（4.0 策略層：候選 A `4 層全 AND → N-of-4 + 總分門檻` + B `移除 structure_score==2 硬門檻` + C `進場改持續站上 K 日`）；
- (b) 8.G.3-min＝`validation/gate_state.py` 只實作「IS gate 硬門檻 dict（ADR-016 K1/K2/K3 + min_trades）逐條 PASS/FAIL + 差距值」，**不做** IS→WFA→OOS 不可逆狀態機、**不做** OOS sealed vault；
- (c) 8.G.1-min＝`runs` 主表最小 DDL（run_id PK + git_sha + bundle_ref + 4 層進場參數 + status + created_at），收口散落在 4 張時序表的孤兒 run_id，**先不補全部 FK**；
- (d) 8.G.2-min＝RunConfig Pydantic schema 只含「IS 區間 + 進場參數 + 成本攤平 + engine + hypothesis 文字欄」，**先不含** OOS 區間鎖死、range/step sweep、hypothesis 系統鎖死；
- (e) 8.G.5-min＝CLI 只留 `run-new` / `run-list` / `validate is`。

**判準**：一個功能若「即使沒有它，v3 進場 edge 仍能被客觀驗出來」，就不是 essential MVP，一律延後當版本層疊加。

#### deferred 清單（順 edge 進程 / 依賴往後疊）

| 延後項 | 延到版本 | 為何延後 |
| :--- | :--- | :--- |
| 8.G.7 前端 Research 工作區全套（runs/new/:id/compare/sweep/validate） | v0.4 起分批 | edge 未證前前端 ROI 趨近零（無策略可看、無候選池可比） |
| 8.G.8 前端 Promotion stepper + A-E 改 /monitor/* + Panel E 重定位 | v1.0（M5） | 晉升前端只在真要晉升 live 時才需要 |
| Cmd-K command palette | v1.0 | 導覽層 ROI 高但非 edge 驗證剛需 |
| sweep/compare 視覺化（heatmap + parallel coordinates） | 後端 v0.3、前端 v1.0 | v0.1-v0.2 用 CLI/code-first 即可 |
| power gauge UI（回測次數/參數/研究天數三軸） | post-MVP | v0.1 只需後端記 trials counter，UI 非必要 |
| OOS sealed vault 完整封存機制 | v0.2 | IS gate 綠燈後才需要，v0.1 IS 階段用不到 |
| 8.G.4 trials_count → DSR deflate | v0.2 | 多重檢定校正在 OOS 階段才有意義 |
| 8.G.6 設計系統 token 擴充（categorical/diverging 色盤） | v0.4 | 前端第一批時才需色盤 |
| Panel D 全部 / Panel B live WebSocket | 維持 ADR-018 既定 M5（v1.0）凍結 | 無可部署策略前 ROI 趨近零，不提前 |
| 跨策略 correlation gate / baseline factor library | M3+（v0.3 後有候選池） | 無候選池前無意義 |
| 四層共振歸因下鑽 / trade markers 疊 K 線 | Run Report 後續迭代（v1.x） | v3 debug 階段如需可走 code-first ad-hoc，非 v0.x 阻塞 |
| notebook 雙模式 / hosted notebook | 不做 | 只共用 TimescaleDB 資料層即可 |
| leaderboard / staking / 多人簽核 / champion-challenger registry / Alpha marketplace | 永久不做 | 單人專案過度設計（ADR-018 明列） |

---

## 7. 開發節奏建議

### 兼職模式（10h / 週）

- 週末：8h 連續寫程式（一個 deep work block）
- 平日晚：2h 文檔 / review / 思考

### Sprint 規劃（2 週為一個 sprint）

> **互動看板**：下表的真相源已遷移至 `dev_docs/scrum_board.json`，由 `tools/scrum_board`
> 拖拉式看板維護。**請勿手改下方 marker 之間的內容** — 在看板拖拉卡片即會自動回寫此區塊與 JSON。
> 啟動看板：`python tools/scrum_board/server.py` → http://127.0.0.1:8765

<!-- SCRUM_BOARD:START (此區塊由 tools/scrum_board 自動生成，請勿手改) -->

| Sprint | 日期 | 重點 | 對應 WBS |
|:--|:--|:--|:--|
| ✅ Sprint -1 | 5/15-5/25 | M0 策略規格定稿 | 1.1 + 10.1 |
| ✅ Sprint 0a | 5/26-5/30 | M1 完成（資料+策略+pipeline） | 3.A + 4.0 + 9.1 |
| ✅ Sprint 0b | 5/31-6/1 | M2 重組 + scaffolding + ADR + Discord | 2.4 + 0.1 + 8.C |
| ✅ Sprint 0c | 6/1（提前完成） | Sprint 0 spike 執行 + Gate Conditional Pass + ADR-013 pivot | 0.2 + 0.3 + 0.4 |
| ✅ Sprint 1 | 6/1（提前完成） | zipline-reloaded 切換 + FinMind bundle + Algorithm + Taiwan controls + CLI | 5.A.1' + 5.A.3' + 4.4 + 5.D |
| ✅ Sprint 2 | 6/1（單日壓縮） | pandas 2 升級（ADR-014）+ wrapper bug fix `evaluate_bar` + validation 三件套（regression_vs_m1 / cross_check_vectorbt / vectorized_pnl_check） | 5.A.4 + 5.A.5 + 5.B.1 + 5.B.3 |
| ✅ Sprint 3 | 6/2-6/15 | universe ingest（`ingest` CLI + live 10 檔，R14 關閉）+ M2+ DB schema + coverage gate→80 + doc sweep + **5.A.6 portfolio IS 回測執行** → ⚠️ **M2 IS gate FAIL（ADR-017）**：策略進場過嚴、雙窗口無 edge，觸發退場條件 → 回 M0 重設進場假設 | 5.A.7.a ✅ + 5.A.7.b ✅ + 3.D.4 ✅ + 5.A.6 ✅ |
| ⏳ Sprint 4 — v0.1 ①：M0 v3 進場假設設計與實作 | 6/16-6/29 | v0.1 essential ①（修正後，承 v3 IS RED + 顧問收斂）：**Step 1 補 config 注入旁路（STRATEGY_PRESET env + backtest-run --config）+ 算法 v3 wiring（consec_structure/prev_box_upper/bars_since_exit 接進 EvaluateBar）→ 用真 zipline 引擎複核 v3 RED 判決**（校準兩個真相源：zipline vs offline sim；algo:78 原寫死 StrategyConfig()，v3 從未進引擎）。**Step 2 gate_state.py 最小版**（ADR-016 K1/K2/K3 + struct1<30%/churn<20% 純函式 dict，逐條 PASS/FAIL）。 | 4.0 v3進場 + 5.A.6（雙窗口重跑） |
| Sprint 5 — v0.1 ②：客觀化最小後端（runs 表 + RunConfig + 最小 CLI，純 TDD） | 6/30-7/13 | v0.1 essential ②：**Step 3** 把 204 行 offline script 收成可重用 harness `run_is(RunConfig)→metrics+健檢` + 最小 runs 落表（RunConfig 強制寫 hypothesis = 反過擬合預登記）。先不上 TimescaleDB、不補時序表 FK、不做 OOS 欄。把『手寫 script 半天』變『run-new 一行 + gate 自動逐條綠紅』。 | 8.G.1-min + 8.G.2-min + 8.G.5-min |
| Sprint 6 — v0.1 ③：IS gate as code（gate_state.py 最小版）+ v0.1 Exit Gate Review | 7/14-7/27 | v0.1 essential ③：**Step 4 結構 hypothesis 競賽**（非參數 sweep）：方向 B（保 structure==2 只解 transition 偏誤，最小因果隔離）→ 方向 A（structure==2 OR 箱頂回測）vs v2 baseline，三 config 一鍵雙窗、自動落表判 gate。**認賠線**：A+B 兩發後若雙窗仍非『同號為正 + 邊際單不劣於 v2 + struct1<30%』→ 判四層假設無 edge，轉 universe(候選D)或砍。產出 v0.1 gate review。 | 8.G.3-min（gate_state.py IS 硬門檻 dict） |
| Sprint 7 — v0.2 ①：IS→WFA→OOS 不可逆狀態機 + OOS sealed vault（僅當 v0.1 綠燈） | 7/28-8/10 | v0.2 ① gate 升級（純後端 TDD，前置硬依賴：跑 OOS 前 vault 必須先鎖死）：8.G.3-full 把『唯讀 IS 指標』升級為『工作流強制 gate』——IS→WFA→OOS 不可逆狀態機（IS PASS 才解鎖 WFA、WFA PASS 才解鎖 OOS）+ OOS sealed vault（前置 gate 未過前 OOS 區段對 CLI 不可讀/不可執行、存取計次留痕）；8.G.2-full RunConfig 補 OOS 區間系統鎖死 + hypothesis 預登記（防 post-hoc）；8.G.1-full 4 張時序表補 run_id FK（migration 通過）。TDD 覆蓋『未過 gate 讀 OOS 被擋』『狀態不可回退』。**若 v0.1 紅燈：本 sprint 不啟動，容量轉回 M0 再設一輪 v3。** | 8.G.3-full + 8.G.2-full + 8.G.1-full |
| Sprint 8 — v0.2 ②：WFA splitter + PBO/DSR + trials deflate → 實跑 OOS | 8/11-8/24 | v0.2 ② OOS 蓋章：5.B.2 WFA splitter（purge+embargo 自寫）+ 6.3 PBO(CSCV) 自寫（對 Bailey 論文對拍）+ DSR 自寫 + 8.G.4 trials_count → dsr.py deflate 接通。在 v0.2 ① sealed vault 保護下對 v3 跑 OOS（gate 解鎖後僅一次）：驗 OOS Sharpe > 0.6×IS、PBO < 30%、DSR > 0.95（含 deflate）。任一紅線 gate_state 自動擋下游、回 Draft；全綠 → status=oos_pass，解鎖 v0.3。 | 5.B.2 + 6.3 + 8.G.4 |
| Sprint 9 — v0.3 ①：統計驗證完整化（metrics enum + Bootstrap/MC + compare CLI） | 8/25-9/7 | v0.3 ① 統計完整化（CLI-only，仍不做前端）：6.1 metrics.py 30+ 指標 enum/functions + quantstats 報表整合；6.4 Bootstrap + Monte Carlo；8.G.5-full CLI 補 compare（多 run baseline delta 表）+ promote check（讀 validation_status）。多 run 比較走 code-first，取代手敲。06 API + README 同步。 | 6.1 + 6.4 + 8.G.5-full（compare/promote check） |
| Sprint 10 — v0.3 ②：DOE 1-10 + Engine Protocol + sweep CLI（edge 穩健性蓋章） | 9/8-9/21 | v0.3 ② edge 穩健性蓋章（完成統計驗證後端，解鎖 v0.4 前端）：6.5.x DOE 1-10 執行（M3 大頭分批起跑）+ 5.C.1 Engine Protocol 抽象 + 8.G.5-full sweep CLI 寫 DB。確認 v3 edge 為穩健高原（heatmap 資料 CLI 輸出）非單點尖峰；PBO < 30% 維持。此版完成＝edge 已被穩健證明。 | 6.5 + 5.C.1 + 8.G.5-full（sweep） |
| Sprint 11 — v0.4 ①：設計系統 token + REST API + Runs Table/Validate 前端 | 9/22-10/5 | v0.4 ① 最薄前端第一批（edge 已證後才疊加，純讀後端 run 真相源）：8.G.6 設計系統 token 擴充（categorical/diverging 色盤 + 收 teal drift）+ 研究級元件規格；8.A.3 Dashboard REST API 層（FastAPI）；8.G.7-partial /research/runs Runs Table（瀏覽/排序/pin baseline）+ /research/validate（IS gate 逐條綠/紅）+ FirstRunEmptyState（CLI-first 空狀態）。前端 0 新增策略邏輯。 | 8.G.6 + 8.A.3 + 8.G.7-partial（Runs Table/Validate） |
| Sprint 12 — v0.4 ②：Run Report + Panel A/B/C React 化（複用元件） | 10/6-10/19 | v0.4 ② 完成研究前端 MVP：8.G.7-partial /research/runs/:id Run Report（複用 Panel A 元件渲染 equity/drawdown/rolling/heatmap + Reproduce 卡）；8.A.1 Panel A/B/C React 版（run-scoped 複用，非 live-only）。驗收：可從 Runs Table 點進任一 v3 run 看完整 tear sheet + 一鍵 Reproduce。完成即 v0.4 研究工作區前端 MVP，解鎖 v0.5 paper。 | 8.G.7-partial（Run Report）+ 8.A.1（Panel A/B/C React） |
| Sprint 13-15 | 10/20-11/30（外推） | v0.5：Paper trading + 監控接管 — PaperBroker + trade log、Risk Gate ex-ante 12 條 + 3 級熔斷、Prefect daily flow、Discord 3 級告警規則引擎、Grafana 系統面板。3 個月 paper 報告不退化才往 v1.0。 | 7.A + 7.C + 7.D + 8.C.2 + 8.B + 8.D |
| Sprint 16+ | 2027 Q1+（外推） | v1.0：小倉位實盤（Shioaji 1/4 倉）+ 晉升 stepper 強制 gate + Panel D/E React + Compare/Sweep/Cmd-K 前端 + 備份/DR；之後 v1.x roadmap 層按需疊加。 | 7.B + 8.G.8 + 8.A.2 + 8.G.7-full + 8.E/8.F |

<!-- SCRUM_BOARD:END -->

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
| v2.10 | 2026-06-04 | **對照診斷 + 動能策略模組 + 對抗式驗證（四層終局 + 平台反向驗證）**：(1) 對照因子診斷（PR #52）證四層**負 edge、毀價值**（同股票 buy-hold +12~22%、四層做成 −2~−3%），market/buy-hold 全正、12-1 動能 PASS gate → 問題在四層本身非平台/資料/universe。(2) 新增 `strategies/momentum/`（12-1 跨截面動能）+ `research/momentum_harness.py` + `MOMENTUM_GATE`（證平台 strategy-agnostic，第二個策略無痛插入）。(3) 5-agent 對抗式驗證 + **量化防過擬合三件套（PBO/DSR/WFA，首次端到端跑真策略）**：對抗式（定性）顯示參數/regime/universe 脆弱；量化（校準）顯示 **PBO 21%✅ + DSR 1.00✅（有真實 signal、非純過擬合）但 WFA OOS Sharpe 0.84<1.0❌ + 2022 崩盤 fold（不可部署）**——動能＝真實但波動大、會崩盤的因子溢酬。**平台防過擬合機器成功給出校準真相（單一回測 over-optimize、對抗 probing over-pessimize、三件套居中為真）**。詳見 `factor_baseline_diagnostic_result_2026-06-04.md` + `momentum_strategy_result_2026-06-04.md`。**建議：砍四層；動能走完整紀律（Candidate D 大 universe + OOS/PBO/DSR + 崩盤風控 + 誠實成本）才知有無可部署 edge**。08 §strategies 樹 + 模組表已更新。R9 Step 8 待 #48 合併後補。 | Self |
| v2.9 | 2026-06-02 | **v0.2–v0.6 後端 waves 完成同步 + 平台優先 pivot 校正**（6-agent 代碼核對 audit）：§2 工作包統計校正（6.0 0→64h/36%、7.0 0→40h/36%、8.0 12→38h/47%、合計 500→690h、48%→**66%**）；§4 覆蓋率 95.22%/252→**92.34%/714**、ADR 數量 17→**19**；§1 banner 從「回 M0 重設進場」改為「v0.2–v0.6 後端 waves ✅ + 四層 v3 無 edge（ADR-017/019）→ 平台優先」；§6 roadmap preamble + 新增「交付現況」註（後端基建 validation/research/risk/monitoring/API 已建完，但 edge-gated exit 未達成，前端/實盤仍 gated 於真實 edge）；§3 6.0/8.0/8.G 小計 + 6.2.1/8.G.2 狀態校正。**§7 Sprint 看板（`scrum_board.json` 真相源）reconciliation 待另跑 `sync_wbs.py`**（marker 區塊不手改）。 | Self |
| v2.8 | 2026-06-02 | **v3 進場重設 v0.1 實作（ADR-019）**：四交易視角壓測收斂的 v3 進場設計（必含層+可選層，非純 N-of-4 — 實證 L2⊂L3 相關 0.615；6 參數 v2 預設重現 baseline）+ flameout 最小 exit 搭配落地。config +6 欄位 + `DEFAULT_CONFIG_V3`；signals.py `_evaluate_priority`/`compute_signals`/`EvaluateBar` 參數化；16 synthetic 測試（不依賴 cache）、signals.py 100% 覆蓋、suite 271 pass / 4 skip、v2 全路徑 regression 釘死。校正 doc/code 成本 drift（code cost_round 0.671%/edge 1.271% vs v2.md 1.07%/1.3%）。§5 R9 轉「🟠 緩解中」；待 Sprint 6 雙窗口 IS 人工讀（cache-gated，綠燈≠有 edge）。ADR 數量 18→19 | Self |
| v2.7 | 2026-06-02 | **反發散版本切版 + Sprint 對齊（承 ADR-018）**：§6 新增「版本 Roadmap」——essential MVP（v0.1）= M0 v3 進場重設 + 讓迭代客觀可守門的最小後端（8.G.3-min IS gate as code + 8.G.1/8.G.2/8.G.5 最小版），明確不含前端/sweep/compare/Cmd-K/promotion UI/OOS sealed vault；後續 v0.2 OOS+統計 → v0.3 研究後端 → v0.4 研究前端 MVP → v0.5 M4 paper → v1.0 M5 live → v1.x roadmap 層，每版綁可客觀驗收 exit gate。§7 Sprint 表經 `tools/scrum_board`（`scrum_board.json` 真相源 + `sync_wbs.py` 重生）展開為 Sprint 4-12 對齊版本（Sprint 4-6=v0.1、7-8=v0.2、9-10=v0.3、11-12=v0.4）+ Sprint 13-15/16+ 外推 rollup；鐵律：v3 edge 未證前不推進前端/重功能。 |
| v2.6 | 2026-06-02 | **監控優先 → 研究迴圈優先 pivot（ADR-018）**：大廠 UI/UX deep-research 對標（10 平台：QuantConnect/BRAIN/Numerai/Bloomberg/W&B/MLflow/OSS 報表/機構平台/開發者工具/防過擬合）→ 證據包 `web_design/03_uiux_benchmark_and_reinforcement_plan.md`（10 維度差距、8 CRITICAL、7 張 Mermaid 流程圖、補強 roadmap）；§2/§3 新增**模組 8.G 研究迴圈 UX 與 Run 物件化**（runs 主表 / RunConfig schema / gate_state.py IS→WFA→OOS + OOS sealed vault / trials→DSR deflate / CLI 擴充 / 研究級元件 / 前端 research 工作區）；A–E 監控重定位為 live 子視圖（Panel E 改隸屬 Validate gate）、Panel D / Panel B live WS 凍結至 M5；ADR 數量 17→18；§1 banner 加 v2.6 pivot 說明 |
| v2.5 | 2026-06-02 | **M2 IS gate FAIL → 回 M0 重設進場（ADR-017）**：5.A.6 portfolio IS 雙窗口執行（2020-2024 −1.75% / 2015-2020 −4.94%），對 ADR-016 K1/K2/K3 全 FAIL；根因＝進場過嚴（2330 5 年 14 次進場、勝率 50%），參數探針證實非出場非 bug；§1 banner / §6 M2 milestone ❌ / §5 R9 標已部分實現 / §7 Sprint 4 重定義為 M0 進場重設 / ADR 數量 16→17 / 技術債加 `_format_perf_summary` ffill bug（已修）；M0 證據包見 `docs/superpowers/specs/2026-06-02-m0-entry-redesign-scope.md` |
| v2.4 | 2026-06-02 | **5.A.7.b 完成 + R14 關閉**：新增 `ingest` CLI 子命令（+5 mock test）+ runbook（`dev_docs/runbooks/m2_universe_ingest_runbook.md`）+ 06/README 同步；live 跑 2020-2024 10 檔 `ok=10/10`，parquet cache 就緒（不入版控）；7 個 cache-gated 驗證測試（regression_vs_m1 + cross_check_vectorbt）解 skip 並通過 → 252 pass / 4 skip、coverage 95.22%；模組 5.0 64%→66%；§5 R14 標 ✅ 關閉；§7 Sprint 3 更新；剩 5.A.6 portfolio |
| v2.3 | 2026-06-02 | **6/2 PR 批次同步 + R14 真相校正**：§1 banner/git 分支/最新 commit 更新至 `a75c0af`（PR #15/16/17/18 已合入）；**5.A.7 拆為 5.A.7.a helper ✅（PR #15）/ 5.A.7.b live ingest ⏳（R14 仍開放，repo 內無 parquet cache）**；模組 5.0 60%→64%；§4 整體進度統一為 48%（修 43/48 內部打架）、覆蓋率更新為 93.74%（gate→80，PR #17）；§5 R14 改寫為「部分緩解」+ cache runbook 不入版控策略；§7 Sprint 3 列已完成 PR 與剩餘關鍵路徑 |
| v2.2 | 2026-06-01 | **WBS status audit sync**：Sprint 1/2 標 ✅；模組 4.0 100%、5.0 60%、9.0 70%；§3 5.A.4 ~ 5.A.7 / 5.B.1 / 5.B.3 落地紀錄；§5 風險表新增 R14（universe ingest 9 檔缺）/ R15（doc sweep）；§6 加 M2 acceptance KPI 子節（CAGR>18% / Sharpe>1.0，凍結於 ADR-016）；§7 Sprint 表 1/2/3 更新；總進度 43%→48% |
| v2.1 | 2026-06-01 | 模組 8.0 加 8.A.0（儀表板設計階段完成 ✅）+ 8.A.3（REST API 層）；8.A.1/A.2 標註 React 化（ADR-015）；§4 ADR 數量 11→15、文檔完整度更新 |
| v2.0 | 2026-06-01 | 完整重寫對齊 M2 路線變更（ADR-005~011）；新增模組 0.0 (Sprint 0)、2.4（M2 重組追溯）、11.0（跨 milestone 維運）；模組 5.0/7.0/8.0 重寫；確立本檔為狀態真相源 |
| v1.0 | 2026-05-26 | 初版（M1 完成時的 baseline） |
