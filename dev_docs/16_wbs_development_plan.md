# WBS 開發計劃 — backtest_platform

> **版本：** v2.6 | **更新：** 2026-06-02 | **狀態：** M1 ✅ + Sprint 0-2 ✅ + Sprint 3 ✅（universe ingest + 5.A.6 portfolio IS 回測執行）→ **⚠️ M2 IS gate FAIL（ADR-017）：策略進場過嚴、雙窗口無 edge → 觸發退場條件，回 M0 重設進場假設**。Sprint 4 重定義為 M0 進場重設。
> **v2.6 新增（2026-06-02）**：大廠 UI/UX deep-research 對標 → **監控優先 → 研究迴圈優先 pivot（[ADR-018](./adrs/ADR-018-monitoring-to-research-loop-pivot.md)）**；新增**模組 8.G 研究迴圈 UX 與 Run 物件化**（後端契約 8.G.1–8.G.4 為 M0/M2 最高優先，可純 TDD）；現行 A–E 監控降為 live 子視圖、Panel D / Panel B live WS 凍結至 M5。
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
| 6.0 統計驗證 | 180h | 0h | 0% | M3 |
| 7.0 Paper+實盤 | 110h | 0h | 0% | M4-M5 |
| 8.0 監控與儀表板 | 80h | 12h | 15% | Discord notifier 完成 (ADR-010) + 設計階段 (ADR-015) |
| 9.0 測試品質 | 80h | 64h | 80% | Stream D Wave 2 完成 2026-06-02：新增 73 個測試（29 algorithms + 18 cli + 10 pipeline + 16 schemas + 11 finmind_etl extension）→ 190 pass / 1 skip，coverage 66%→93.74%，`--cov-fail-under` 65→**80** ratchet |
| 10.0 文檔 | 120h | 110h | 92% | 持續 |
| 11.0 跨 milestone | 30h | 24h | 80% | Discord 遷移 + 結構同步完成 |
| **合計** | **1050h** | **500h** | **48%** | M1 ✅ + Sprint 0 Gate + Sprint 1 ✅ + Sprint 2 ✅ |

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
| 3.D.4 | 新增 9 張 M2+ 表 (見 21 §4) + db_writer.upsert_positions | DEV | 8h | ✅ | 2026-06-02 | M2 啟動 |
| 3.E.1 | FinLab live polling adapter | DEV | 8h | ⏳ | — | 0.3.5 |
| 3.E.2 | Shioaji quote adapter (備援) | DEV | 6h | ⏳ | — | 0.3.4 |
| 3.E.3 | Live feed → TimescaleDB writer | DEV | 6h | ⏳ | — | 3.E.1 |

**模組小計**：120h | 進度 60%（含 3.D.4 完成）

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
| 4.4.1 | Zipline algorithm wrapper skeleton | DEV | 4h | ✅ | 2026-06-01 — `four_layer_resonance.py` initialize / schedule_function |
| 4.4.2 | initialize/handle_data 整合 M1 純函式 | DEV | 6h | ✅ | 2026-06-01 — Sprint 2 改為 `evaluate_bar` 事件驅動評估（取代原 `compute_signals.iloc[-1]` walk-loop wrapper bug） |

**模組小計**：70h | 進度 100% ✅（M1 完成；M2 wrapper Sprint 1-2 落地）

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
| 5.A.4 | FourLayerResonance Algorithm 完整實作 | DEV | 16h | ✅ | 2026-06-01（commit 8b6563b → Sprint 2 `b5c97de` `evaluate_bar` 校正）|
| 5.A.5 | 對 2330 IS 回測對齊 M1 pipeline.py | QA | 4h | ✅ | 2026-06-01（Sprint 2 `validation/regression_vs_m1.py`，2330 2024 全年 **100.00% match**，commit `b5c97de`）|
| 5.A.6 | Portfolio (10 檔) IS 回測 | DEV | 8h | ✅ 執行（gate FAIL）| 2026-06-02 — Algorithm 原生支援多股，無需另寫 aggregator。雙窗口 portfolio IS：2020-2024 **−1.75%**、2015-2020（ADR-016 凍結窗口）**−4.94%**；2330 5 年僅 14 次進場、勝率 50%、在市場 3.9%。**對 ADR-016 K1/K2/K3 全 FAIL → 觸發退場（[ADR-017](./adrs/ADR-017-m2-is-gate-failed-return-to-m0-entry-redesign.md)）**。參數探針證實約束在進場非出場 |
| **5.A.7.a** | **`ingest_universe` 批次 helper（per-symbol isolation + all-fail raise）** | DEV | 4h | ✅ Wave 2 | 2026-06-02（commit `90bdfe9` / PR #15；含 mock/stub unit tests，error isolation 單一來源化） |
| **5.A.7.b** | **DEFAULT_UNIVERSE live 10 檔 FinMind ingest → parquet（含 2330 + 9 檔）** | DEV | 2h | ✅ Wave 3 | 2026-06-02 — **R14 關閉**；新增 `ingest` CLI 子命令（+5 mock test）+ runbook（`dev_docs/runbooks/`）；live 跑 2020-2024 5yr `ok=10/10` 35s；解開 7 個 cache-gated 驗證測試（regression_vs_m1 + cross_check_vectorbt 真正執行並通過）→ 252 pass / 4 skip，coverage 95.22%。cache 不入版控（runbook 化） |
| 5.B.1 | vectorbt adapter (grid 用) | DEV | 12h | ✅ Sprint 2 | 2026-06-01（ADR-014 升級恢復；`validation/cross_check_vectorbt.py` 2330 多範圍全 PASS，誤差 $6-20/$1M，commit `b5c97de`）|
| 5.B.2 | WFA splitter 自寫 | DEV | 8h | ⏳ M3 | — |
| 5.B.3 | vectorbt vs Zipline 對拍 | QA | 8h | ✅ Sprint 2 | 2026-06-01（兩段式 acceptance：相對 1% / 絕對 10 bps；3 個 integration test + 2 unit test 全綠）|
| 5.C.1 | Engine Protocol 抽象 | ARCH | 4h | ⏳ M3 | — — vectorbt cross-check 完成後可抽象 |
| 5.D.1 | engines/ Click CLI | DEV | 4h | ✅ | 2026-06-01（commit c980a44，Sprint 1 Day 6-7 收尾 + README） |

**模組小計**：~100h | Sprint 1 ~30h + Sprint 2 ~30h + Sprint 3 5.A.7.a helper 4h + 5.A.7.b CLI/live ingest 2h = 66h（66%）— 主骨架 + bundle + Algorithm + Taiwan controls + CLI + wrapper bug fix + validation 三件套 + ADR-014 + `ingest_universe` helper（PR #15）+ `ingest` CLI 子命令 + **live 10 檔 ingest（R14 關閉，7 個 cache-gated 驗證測試解 skip）**；**剩餘關鍵路徑：5.A.6 multi-stock aggregator + portfolio IS 回測**

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

### 模組 8.G 研究迴圈 UX 與 Run 物件化（[ADR-018](./adrs/ADR-018-monitoring-to-research-loop-pivot.md)，最高槓桿補強）— 新增

> 大廠 UI/UX deep-research 對標（`web_design/03_uiux_benchmark_and_reinforcement_plan.md`）：現行 A–E 全是 live 監控，缺研究迭代迴圈 UX。**鐵律：補齊研究迴圈前不再擴張監控 panel（Panel D / Panel B live WS 凍結至 M5）**。後端契約先行（純 Python/CLI 可 TDD），最薄前端隨 ADR-015 React 化批次補。

| 編號 | 任務 | 工時 | 狀態 | 里程碑 |
|:--|:--|:---:|:--|:--|
| 8.G.0 | UI/UX deep-research 對標 + 10 維度差距 + 7 流程圖 + roadmap（ADR-018 證據包） | 8h | ✅ 2026-06-02 | — |
| 8.G.1 | `runs` 主表 DDL（21 §4）+ 4 張時序表 run_id 補 FK（Run 物件化 single source of truth） | 6h | ⏳ | M0/M2 |
| 8.G.2 | RunConfig Pydantic schema（IS/OOS 區間 + 成本攤平 + engine + range/step + hypothesis 預登記） | 6h | ⏳ | M0/M2 |
| 8.G.3 | `validation/gate_state.py`：IS→WFA→OOS 不可逆狀態機 + OOS sealed vault + 硬門檻 dict（ADR-016 K1/K2/K3） | 8h | ⏳ | M0 |
| 8.G.4 | 試驗次數計數 → DSR deflate（trials_count + dsr.py 接 n_trials） | 4h | ⏳ | M0/M3 |
| 8.G.5 | CLI 擴充：run-new / run-list / sweep / compare / validate is·wfa·oos / promote check（06 + README 同步） | 8h | ⏳ | M2 |
| 8.G.6 | 設計系統 token 擴充（categorical/diverging/sequential 受控色盤）+ 研究級元件規格（CodeEditor / ResearchTable / CompareChart / FirstRunEmptyState / Cmd-K） | 6h | ⏳ | M0/M2 |
| 8.G.7 | 前端 Research 工作區（/research/runs · /runs/new · /runs/:id Run Report · /compare · /sweep · /validate）+ Cmd-K | 20h | ⏳ | M3 |
| 8.G.8 | 前端 Promotion stepper（/research/promote）+ A–E 改 /monitor/* 子視圖 + Panel E 重定位 Validate gate | 10h | ⏳ | M5 |

**模組小計**：~76h | 進度 ~10%（對標證據包完成；後端契約 8.G.1–8.G.4 為 M0/M2 最高優先，可純 TDD）

---

## 4. 進度摘要

| 項目 | 當前值 | 目標值 |
|:--|:---:|:---:|
| 整體進度 | **48%**（與 §2 工作包統計合計一致） | 100% |
| M1 完成度 | 100% | 100% |
| Sprint 0 scaffolding | 100% | — |
| Discord 遷移 | 100% | — |
| 單元測試覆蓋率 | **95.22%**（5.A.7.b 後 252 pass / 4 skip；`--cov-fail-under` gate 80） | 80%+ |
| 開放 P0 Bug | 0 | 0 |
| 技術債項目 | 4（見下） | < 3 |
| ADR 數量 | 17（+016 M2 KPI 凍結 / **017 M2 IS gate FAIL → 回 M0 重設進場**） | 持續 |
| 文檔完整度 | ~96%（dev_docs 階段 1-7 + 儀表板 Design System / web_design 流水線 / 21 API 契約） | 100% |

### 技術債（M2 待處理）

1. 券商分點欄位全 0（FinMind 免費版無；M2 評估 FinLab 是否補齊）
2. ETL 沒寫 DB（目前只寫 parquet；M2 啟用 db_writer）
3. SwingHigh 用 rolling max 近似 XQ pivot（需抽樣驗證 < 1% 差異）
4. lock file 未引入（M2 啟動後 `uv lock` 產出 `uv.lock` 入版控；ADR-012）

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
| **R9 策略本身無 Edge** | 高 | 致命 | 🔴 **已於 IS 部分實現**（2026-06-02，ADR-017）：portfolio 雙窗口 IS 無 edge（進場 ~14 次/5 年、勝率 50%）。**處置**：回 M0 重設**進場**假設（v3）；非砍策略，先重訂進場 edge 再重跑 ADR-016 gate。若 v3 仍無 edge → 才評估砍策略 | Self |
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
| ⏳ Sprint 4 | 6/16-6/29 | **（重定義，ADR-017）** M0 進場假設重設（v3）：依 `docs/superpowers/specs/2026-06-02-m0-entry-redesign-scope.md` 候選方向 A/B/D 設計 → 重跑 ADR-016 gate | M0 進場重設 |
| Sprint 5-8 | 6/30-8/24 | M3 統計驗證 + WFA + PBO/DSR + DOE | 5.B.2 + 6.* |

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
| v2.6 | 2026-06-02 | **監控優先 → 研究迴圈優先 pivot（ADR-018）**：大廠 UI/UX deep-research 對標（10 平台：QuantConnect/BRAIN/Numerai/Bloomberg/W&B/MLflow/OSS 報表/機構平台/開發者工具/防過擬合）→ 證據包 `web_design/03_uiux_benchmark_and_reinforcement_plan.md`（10 維度差距、8 CRITICAL、7 張 Mermaid 流程圖、補強 roadmap）；§2/§3 新增**模組 8.G 研究迴圈 UX 與 Run 物件化**（runs 主表 / RunConfig schema / gate_state.py IS→WFA→OOS + OOS sealed vault / trials→DSR deflate / CLI 擴充 / 研究級元件 / 前端 research 工作區）；A–E 監控重定位為 live 子視圖（Panel E 改隸屬 Validate gate）、Panel D / Panel B live WS 凍結至 M5；ADR 數量 17→18；§1 banner 加 v2.6 pivot 說明 |
| v2.5 | 2026-06-02 | **M2 IS gate FAIL → 回 M0 重設進場（ADR-017）**：5.A.6 portfolio IS 雙窗口執行（2020-2024 −1.75% / 2015-2020 −4.94%），對 ADR-016 K1/K2/K3 全 FAIL；根因＝進場過嚴（2330 5 年 14 次進場、勝率 50%），參數探針證實非出場非 bug；§1 banner / §6 M2 milestone ❌ / §5 R9 標已部分實現 / §7 Sprint 4 重定義為 M0 進場重設 / ADR 數量 16→17 / 技術債加 `_format_perf_summary` ffill bug（已修）；M0 證據包見 `docs/superpowers/specs/2026-06-02-m0-entry-redesign-scope.md` |
| v2.4 | 2026-06-02 | **5.A.7.b 完成 + R14 關閉**：新增 `ingest` CLI 子命令（+5 mock test）+ runbook（`dev_docs/runbooks/m2_universe_ingest_runbook.md`）+ 06/README 同步；live 跑 2020-2024 10 檔 `ok=10/10`，parquet cache 就緒（不入版控）；7 個 cache-gated 驗證測試（regression_vs_m1 + cross_check_vectorbt）解 skip 並通過 → 252 pass / 4 skip、coverage 95.22%；模組 5.0 64%→66%；§5 R14 標 ✅ 關閉；§7 Sprint 3 更新；剩 5.A.6 portfolio |
| v2.3 | 2026-06-02 | **6/2 PR 批次同步 + R14 真相校正**：§1 banner/git 分支/最新 commit 更新至 `a75c0af`（PR #15/16/17/18 已合入）；**5.A.7 拆為 5.A.7.a helper ✅（PR #15）/ 5.A.7.b live ingest ⏳（R14 仍開放，repo 內無 parquet cache）**；模組 5.0 60%→64%；§4 整體進度統一為 48%（修 43/48 內部打架）、覆蓋率更新為 93.74%（gate→80，PR #17）；§5 R14 改寫為「部分緩解」+ cache runbook 不入版控策略；§7 Sprint 3 列已完成 PR 與剩餘關鍵路徑 |
| v2.2 | 2026-06-01 | **WBS status audit sync**：Sprint 1/2 標 ✅；模組 4.0 100%、5.0 60%、9.0 70%；§3 5.A.4 ~ 5.A.7 / 5.B.1 / 5.B.3 落地紀錄；§5 風險表新增 R14（universe ingest 9 檔缺）/ R15（doc sweep）；§6 加 M2 acceptance KPI 子節（CAGR>18% / Sharpe>1.0，凍結於 ADR-016）；§7 Sprint 表 1/2/3 更新；總進度 43%→48% |
| v2.1 | 2026-06-01 | 模組 8.0 加 8.A.0（儀表板設計階段完成 ✅）+ 8.A.3（REST API 層）；8.A.1/A.2 標註 React 化（ADR-015）；§4 ADR 數量 11→15、文檔完整度更新 |
| v2.0 | 2026-06-01 | 完整重寫對齊 M2 路線變更（ADR-005~011）；新增模組 0.0 (Sprint 0)、2.4（M2 重組追溯）、11.0（跨 milestone 維運）；模組 5.0/7.0/8.0 重寫；確立本檔為狀態真相源 |
| v1.0 | 2026-05-26 | 初版（M1 完成時的 baseline） |
