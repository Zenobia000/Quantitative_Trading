# M2–M5 主規劃文件 — zipline-reloaded 主骨架整合方案

> **版本：** v1.1 | **更新：** 2026-06-01 | **狀態：** 已批准
> **路線代號：** Plan zipline-reloaded（原 Plan TQuant-Lab，Sprint 0 S1 揭露 zipline-tej 強綁 TEJ key 後切換）
> **對應 plan file：** `C:\Users\xdxd2\.claude\plans\maintain-calm-blossom.md`
> **對應 ADR：** ADR-005~012 + **ADR-013（取代 ADR-005 主骨架選擇）**
> **進度追蹤：** 見 [`16_wbs_development_plan.md`](./16_wbs_development_plan.md)（單一狀態真相源；本文件為「路線與計畫書」，不含進度）
>
> **v1.1 變更（2026-06-01）**：主骨架 `TQuant-Lab (zipline-tej)` → `zipline-reloaded 3.0.4`。Sprint 0 S1 spike 揭露 zipline-tej import 階段 hard-code TEJ API call，違反「免 TEJ key 仍可開發」前提。zipline-reloaded 為社群維護 zipline 主線 fork，0 商業綁定、SQLAlchemy 2.x、`exchange-calendars` 提供完整 XTAI 支援。詳見 [ADR-013](./adrs/ADR-013-mainframe-zipline-reloaded-supersedes-tquant-lab.md)。下文「TQuant-Lab」字樣為歷史脈絡保留，現況皆指 zipline-reloaded。

---

## 1. Context — 為什麼做這個變更

### 1.1 三個觸發決策

| # | 原規劃（02 PRD §4） | 新決策 | 衝擊 |
| :---: | :--- | :--- | :--- |
| **D1** | 資料源：FinMind 免費版 + sponsor + TWSE 補爬 | **付費 FinLab**（年費 ~9–10k TWD） | M1 `data/finmind_etl.py` 改為 fallback；不再自 maintain ETL |
| **D2** | 系統定位：純回測平台（M1–M3）→ paper（M4）→ live（M5） | **完整交易系統**：backtest + paper + live 三模式 + 雙儀表板從 M3 啟動 | L7 監控提前 2 個 milestone，新增 Streamlit/Grafana/Discord 三層 |
| **D3** | 工程哲學：截長補短，自寫 framework，rqalpha 為主回測引擎 | **不自建 framework**，以 **TQuant-Lab (Zipline 台股 fork)** 為主骨架，自寫薄 adapter | 砍 rqalpha；引入 Zipline event-driven；vectorbt 降為副引擎 |

### 1.2 現狀問題

| 問題 | 出處 | 處置 |
| :--- | :--- | :--- |
| rqalpha 無台股 mod、無 Shioaji broker | `research_open_source_backtest_platforms.md` §3.5 | 改用 TQuant-Lab，內建 XTAI 日曆 + TEJ 官方 Shioaji 範例 |
| FinMind 免費版缺券商分點 → v2 L3 籌碼分不完整 | 02 PRD §7.1 風險 | 改用 FinLab，原生支援券商分點 |
| M1 已交付 962 LOC（`strategy/` + `data/`），不能浪費 | M1 release | 0 重構，搬路徑 + 補 wrapper 即可 |
| `engines/`、`validation/` 仍為空骨架 | 05 架構 L3-A | M2 用 TQuant-Lab 填 engines；M3 自寫 PBO/DSR 填 validation |
| 業界已有「7 層 reference architecture + 30+ 指標 taxonomy」共識 | LEAN / Nautilus / López de Prado | 一次定義到位，寫進 18 號文檔 |

### 1.3 預期結果

| 指標 | 原規劃 | 新規劃 | 改善 |
| :--- | :---: | :---: | :--- |
| 首版上線時間 | 22 週（自建） | **17 週** | -23% |
| 新寫程式碼 | 6–8k LOC | **~2500 LOC** | -65% |
| M1 既有程式重構 | 部分（rqalpha 整合需改） | **0 重構** | — |
| 業界規格對齊 | 想到才加 | **一次到位（7 層 × 30 指標）** | — |
| 三模式（backtest/paper/live） | 分散在各 milestone | **共用同一份 strategy code** | 維護成本 -50% |

---

## 2. 路線總覽 — 四條候選路線對比

| 路線 | 主骨架 | 自寫 LOC | 上線時間 | 廠商鎖定 | 7 訊號優先序 | 結論 |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- |
| **Plan A** | 自建 framework + rqalpha | 6–8k | 22 週 | 低 | 自寫 | ❌ 重造輪子 |
| **Plan B** | FinLab SDK 當主骨架 | 1800 | 14 週 | **高** | 表達困難 | ❌ 深度鎖定 + 精度爭議 |
| **Hybrid** | FinLab 資料 + 自寫 adapter + rqalpha | ~4000 | 18 週 | 中 | 自寫 | ⚠️ Sprint 0 失敗時備援 |
| **Plan TQuant-Lab** ✅ | TQuant-Lab (Zipline 台股 fork) + FinLab 資料 + vectorbt 副引擎 | **~2500** | **17 週** | 低 | **天然支援** | ✅ **採用** |

### 2.1 為何選 TQuant-Lab

| 理由 | 說明 |
| :--- | :--- |
| Zipline 是業界 7 層 reference 最經典實作 | Quantopian 遺產，LEAN/Nautilus 設計師都讀過 |
| 內建 `exchange_calendar_xtai` | 全市場唯一原生支援 XTAI 的開源 framework |
| TEJ 官方有 Shioaji 整合範例 | `tejtw/TEJAPI_Python_Medium_Application` repo，M4–M5 實盤幾乎 0 自寫 |
| MIT 授權、純 Python | 可任意修改、fork 不可撤回 |
| L1–L7 模組全部就位 | Data Bundle / Pipeline / Algorithm / Portfolio / Risk / Broker / Reporting |
| Event-driven 天然支援 7 訊號優先序 | 這在 vectorized 內難以表達（見 ADR-005） |

### 2.2 為何不選其他

| 排除 | 原因 |
| :--- | :--- |
| LEAN / Nautilus | 太重，無 XTAI 日曆 |
| rqalpha | 無台股 mod，無 Shioaji broker（已驗證，見前次調研 §3.5） |
| backtrader | 2018 後棄維護 |
| FinLab SDK 當主骨架 | 流量限制、精度爭議、7 訊號優先序表達不出來、廠商鎖定 |
| 純 vectorbt | 是引擎不是完整骨架，L4–L7 全要自寫 |

---

## 3. 業界 7 層 Reference 對應

> **這是 ceiling，不是 wishlist。M2–M5 只是把空殼陸續填滿。**
> 完整規格與業界文獻引用見 [18_reference_architecture_and_metrics.md](./18_reference_architecture_and_metrics.md)。

| 層 | 名稱 | 職責 | 主骨架對應 | M 交付 |
| :--: | :--- | :--- | :--- | :--: |
| **L1** | Data Layer | Market / Fundamental / Reference data | zipline-reloaded `data_portal` + FinMind/FinLab bundle（ADR-013）| **M2** |
| **L2** | Research / Signal | Alpha factor、IC 分析 | M1 `scoring.py` + `signals.py` plug-in | **M2/M3** |
| **L3** | Backtest Engine | Event-driven / Vectorized 雙引擎 | Zipline (event) + vectorbt (vector) | **M2/M3** |
| **L4** | Portfolio Construction | Position sizing、權重、再平衡 | Zipline `Pipeline` + 自寫 allocator | **M3** |
| **L5** | Risk Management | Ex-ante limits、熔斷、集中度 | 自寫 risk gates + Zipline order hook | **M4/M5** |
| **L6** | Execution / OMS | 訂單路由、滑點、實盤接口 | Zipline `Blotter` + Paper / Shioaji broker | **M4/M5** |
| **L7** | Monitor & Attribution | 即時儀表板、告警、績效歸因 | Streamlit + Grafana + Discord | **M3–M5** |

---

## 4. 三模式架構

> **核心設計**：Zipline 的 strategy 與 execution 解耦。三模式只切換三個 plug 點：**資料源 / Broker / 輸出儲存**。
> 詳細業界出處見 18 號文檔 §5 Backtest 標準 Pipeline。

| 模式 | 資料源 | Broker | 輸出 | 用途 | 啟用 M |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **Backtest** | Historical bundle (FinLab / FinMind) | `SimulationBlotter` (Zipline 內建) | Parquet | M2 研究、M3 WFA | M2 |
| **Paper** | Live data feed (FinLab realtime) | `PaperBroker`（自寫模擬撮合 + log） | TimescaleDB | M4 實盤前驗證 3 個月 | M4 |
| **Live** | Live data feed (FinLab / Shioaji quote) | `ShioajiBroker`（抄 TEJ 範例改） | TimescaleDB | M5 真錢 | M5 |

### 4.1 CLI 介面

```bash
zipline run --bundle finlab --start 2015 --end 2024              # Backtest
zipline run --bundle finlab-live --paper --broker sim            # Paper
zipline run --bundle finlab-live --broker shioaji                # Live
```

### 4.2 Strategy code 100% 共用

| 元件 | 來源 | 三模式共用 |
| :--- | :--- | :---: |
| `strategy/scoring.py` (181 LOC) | M1 直接搬 | ✅ |
| `strategy/signals.py` (326 LOC) | M1 直接搬 | ✅ |
| `strategy/indicators.py` (96 LOC) | M1 直接搬 | ✅ |
| Zipline algorithm wrapper (~100 LOC) | M2 新寫 | ✅ |
| `data_bundle` adapter | adapter 層切換 | ❌（每模式各一） |
| `broker` adapter | adapter 層切換 | ❌（每模式各一） |

---

## 5. 新目錄結構

> 完整目錄與 LOC 估算詳見 plan file §5。以下為摘要表。

```
backtest_platform/src/backtest_platform/
│
├── strategies/                              # ★ 新增（從 strategy/ 改名）
│   └── four_layer_resonance/
│       ├── __init__.py                      # ~100 LOC（Zipline algorithm wrapper）
│       ├── scoring.py                       # M1 搬遷，0 改動
│       ├── signals.py                       # M1 搬遷，0 改動
│       └── indicators.py                    # M1 搬遷，0 改動
│
├── adapters/                                # ★ 新增（隔離主骨架與外部世界）
│   ├── data_bundle/
│   │   ├── finlab_bundle.py                 # ~150 LOC（FinLab → Zipline ingester，主）
│   │   └── finmind_bundle.py                # ~80 LOC（包 M1 finmind_etl，fallback）
│   ├── data_feed/
│   │   ├── finlab_live.py                   # ~100 LOC（即時資料 polling）
│   │   └── shioaji_quote.py                 # ~80 LOC（Shioaji 報價備援）
│   └── brokers/
│       ├── paper_broker.py                  # ~150 LOC
│       └── shioaji_broker.py                # ~150 LOC（抄 TEJ 官方範例）
│
├── validation/                              # 既有空骨架，M3 填內容
│   ├── metrics.py                           # ~200 LOC（30+ 指標 enum + functions）
│   ├── pbo.py                               # ~150 LOC（自寫，避 pypbo AGPL）
│   ├── dsr.py                               # ~80 LOC（Bailey-López de Prado）
│   ├── wfa.py                               # ~100 LOC（Walk-forward splitter）
│   └── reports.py                           # ~80 LOC（quantstats wrapper）
│
├── engines/                                 # 既有空骨架
│   └── vectorbt_adapter.py                  # ~150 LOC（副引擎 for grid/WFA）
│
├── orchestration/                           # ★ 新增
│   ├── daily_flow.py                        # ~120 LOC（每日排程）
│   └── cli.py                               # ~100 LOC（click entry）
│
├── monitoring/                              # ★ 新增
│   ├── metrics_emitter.py                   # ~80 LOC（Algorithm hook 寫 metrics）
│   └── alerter.py                           # ~100 LOC（Discord 規則引擎，底層 notifier 已 M2 落地）
│
├── dashboard/                               # ★ 新增
│   ├── streamlit_app.py                     # ~400 LOC（5 個策略面板）
│   ├── grafana_dashboards.json              # ~200 LOC（JSON 設定）
│   └── db_schema.sql                        # ~150 LOC（TimescaleDB tables）
│
├── data/                                    # M1 保留作 fallback
│   ├── finmind_etl.py                       # ★ M1 保留
│   ├── adjustment.py                        # ★ M1 保留
│   ├── schemas.py                           # ★ M1 保留
│   ├── db_writer.py                         # ★ M1 保留（cache 用）
│   └── universe.py                          # ★ M1 保留（Zipline pipeline 呼叫）
│
├── config/
│   ├── strategy_config.py                   # ★ M1 凍結
│   └── settings.py                          # ★ 新增（Pydantic Settings 讀 .env）
│
└── pipeline.py                              # ★ M1 保留作 backward-compat shim
```

**新寫總量：~2500 LOC**（含 dashboard 與監控全部）

---

## 6. M1 程式碼處置（檔案級判決）

> **總結：962 LOC 全保留，0 重構，0 改寫，0 砍掉。**

| 既有檔 | LOC | 命運 | 引用點 |
| :--- | :---: | :--- | :--- |
| `strategy/scoring.py` | 181 | **搬到 `strategies/four_layer_resonance/`，0 改動** | Zipline algorithm `compute_signals()` 內 import |
| `strategy/signals.py` | 326 | **搬到 `strategies/four_layer_resonance/`，0 改動** | 同上 |
| `strategy/indicators.py` | 96 | **搬到 `strategies/four_layer_resonance/`，0 改動** | 同上 |
| `config/strategy_config.py` | 67 | **凍結** | 策略契約本身，改它 = 改策略 |
| `data/finmind_etl.py` | 308 | **保留**，被 `adapters/data_bundle/finmind_bundle.py` 呼叫 | fallback 路徑 |
| `data/adjustment.py` | 164 | **保留**，被 finmind_bundle 內部用 | FinLab 已調整，本檔走 fallback 才執行 |
| `data/schemas.py` | 80 | **保留**，Pydantic 驗證仍用 | adapter 邊界 |
| `data/db_writer.py` | 127 | **保留**，改名 `cache` 角色 | bundle 鏡像到 TimescaleDB |
| `data/universe.py` | 128 | **保留，0 改動** | Zipline `Pipeline` 內當 screener |
| `pipeline.py` | 168 | **保留作 backward-compat**，新增 `zipline run` 為主入口 | M1 CLI 不破壞 |
| `tests/*` | 8 檔 | **保留 + 補 import path migration** | M1 36 個 unit test 必須全綠 |

**驗收**：M1 既有 36 個 unit test 在 M2 第 1 週結束前必須全綠（補 import path migration 即可）。

---

## 7. M2–M5 排程

### 7.1 17 週總表

| M | 週數 | 累計 | Deliverable | 對應 7 層 | 三件事覆蓋 |
| :--: | :--: | :--: | :--- | :--- | :--- |
| **Sprint 0** | 1 | 1 | 6 個 spike 全綠（gate） | — | — |
| **M2** | 4 | 5 | zipline-reloaded 跑通 + M1 plug 為 Algorithm + FinMind/FinLab bundle ingester + Backtest 模式端到端（ADR-013）| L1, L2, L3 (event) | ✅ 虛擬交易 (backtest) |
| **M3** | 4 | 9 | vectorbt 副引擎 + Grid + WFA + PBO/DSR 自寫 + Streamlit 面板 A+B+C | L3 (vector), L4, L7 v1 | ✅ 監控儀表板 v1 |
| **M4** | 5 | 14 | PaperBroker + Live data feed + daily_flow 排程 + Grafana + Discord + 3 個月 paper 跑 | L5, L6 (paper), L7 完整 | ✅ 虛擬交易 (live paper) + 監控完整 |
| **M5** | 4 | 18 | ShioajiBroker 切換 + 實盤小倉位（5%）+ Streamlit 面板 D+E + 熔斷規則 | L5 完整, L6 (live) | ✅ 實際交易 |
| **Buffer** | 2 | 17* | bug fix、性能調整、文件 | — | — |
| **合計** | **17 週** | | | | |

*Buffer 與 M5 部分重疊使用，總工期 17 週。

### 7.2 Sprint 0 Gate

| 條件 | 行動 |
| :--- | :--- |
| 6 spike 全綠 | 啟動 M2 |
| 任一 spike 紅 | 退回 Hybrid 路線（見 [01_workflow_manual.md §5.A](./01_workflow_manual.md) §6） |

詳見 [01_workflow_manual.md §5.A](./01_workflow_manual.md)。

---

## 8. 關鍵檔案清單

### 8.1 必建檔案（高優先，M2 第一個 Sprint）

| 檔案 | LOC 估 | 用途 |
| :--- | :---: | :--- |
| `strategies/four_layer_resonance/__init__.py` | ~100 | Zipline Algorithm wrapper，把 M1 `scoring.compute_scores()` 與 `signals.compute_signals()` 接進 `initialize/handle_data` |
| `adapters/data_bundle/finlab_bundle.py` | ~150 | FinLab → Zipline data bundle ingester（一次性歷史回填 + 日增量） |
| `adapters/brokers/paper_broker.py` | ~150 | 即時資料 + 模擬撮合，輸出 trade log 到 TimescaleDB |
| `adapters/brokers/shioaji_broker.py` | ~150 | 抄 `tejtw/TEJAPI_Python_Medium_Application` 改 |
| `config/settings.py` | ~50 | Pydantic Settings 讀 `.env` |

### 8.2 必建檔案（中優先，M3+）

| 檔案 | LOC 估 | 用途 |
| :--- | :---: | :--- |
| `validation/metrics.py` | ~200 | 30+ 指標 enum（一次寫死，function 漸次填） |
| `validation/pbo.py` | ~150 | 自寫（避 pypbo AGPL） |
| `validation/dsr.py` | ~80 | Bailey-López de Prado |
| `validation/wfa.py` | ~100 | Walk-forward splitter |
| `engines/vectorbt_adapter.py` | ~150 | grid/WFA 副引擎 |
| `monitoring/alerter.py` | ~100 | Discord bot + 規則引擎 |
| `dashboard/streamlit_app.py` | ~400 | 5 個面板 |
| `dashboard/db_schema.sql` | ~150 | TimescaleDB tables |

### 8.3 既有 M1 引用點（不修改，只 import）

| 檔案 | 函式 |
| :--- | :--- |
| `backtest_platform/src/backtest_platform/strategy/scoring.py` | `compute_scores` |
| `backtest_platform/src/backtest_platform/strategy/signals.py` | `compute_signals`、`evaluate_bar` |
| `backtest_platform/src/backtest_platform/data/universe.py` | `screen_universe` |
| `backtest_platform/src/backtest_platform/data/finmind_etl.py` | `fetch_bundle`（fallback 才呼叫） |
| `backtest_platform/src/backtest_platform/data/adjustment.py` | `adjust_prices`（fallback 才呼叫） |

---

## 9. Verification 標準

> 每個 milestone 不通過 acceptance 不晉升。

### 9.1 Sprint 0 Gate（第 1 週末）

```bash
# S1 — zipline-reloaded + XTAI 安裝（ADR-013 改 bundle 為 finmind）
zipline ingest -b finmind && zipline run -f hello.py -b finmind --trading-calendar XTAI

# S2 — M1 純函式 plug 進 Zipline Algorithm
pytest tests/strategies/test_zipline_algorithm.py::test_2330_matches_m1_pipeline

# S3 — FinLab bundle ingester POC
python -m adapters.data_bundle.finlab_bundle --stocks 2330,2454,2317 --start 2024-01-01 --end 2024-12-31
zipline run -f hello.py -b finlab

# S4 — Shioaji 沙箱
python tests/integration/test_shioaji_sandbox.py

# S5 — FinLab 即時資料 polling
python -m adapters.data_feed.finlab_live --stock 2330 --duration 60

# S6 — Streamlit 連 TimescaleDB
streamlit run dashboard/streamlit_app.py
```

詳見 [01_workflow_manual.md §5.A](./01_workflow_manual.md) §4。

### 9.2 M2 驗收（第 5 週末）

| 項目 | 命令 / 標準 |
| :--- | :--- |
| 端到端 backtest mode | `zipline run --bundle finlab --start 2015-01-01 --end 2024-12-31 ...` 成功跑完 |
| 性能 | `pytest -m slow tests/performance/test_100stocks_10years.py` < 30 分鐘 |
| 與 M1 對拍 | `pytest tests/regression/test_2330_matches_m1.py` 差異 < 0.1% |
| M1 既有 36 個 unit test | `pytest tests/` 全綠 |

### 9.3 M3 驗收（第 9 週末）

| 項目 | 標準 |
| :--- | :--- |
| vectorbt 副引擎 | grid 1000 trials × 100 檔 < 2 小時 |
| PBO/DSR | 對 Bailey 論文表 5.2 範例數值匹配（容許 1e-4） |
| Streamlit 面板 A+B+C | localhost 可開、equity curve 互動正常 |
| 雙引擎一致性 | Zipline vs vectorbt 在同一段 IS 期間差異 < 0.5%（見 ADR-005） |

### 9.4 M4 驗收（第 14 週末）

| 項目 | 標準 |
| :--- | :--- |
| Paper trading 連續性 | 3 個月每日成功 emit 訊號 + 模擬下單 |
| Grafana | 4 個系統面板可開 |
| Discord | ETL 失敗時收到告警 |
| 三層監控聯動 | Streamlit + Grafana + Discord 端到端測試通過 |

### 9.5 M5 驗收（第 17 週末）

| 項目 | 標準 |
| :--- | :--- |
| ShioajiBroker | 切換成功，實盤小倉位（總資本 5%）下單 |
| OOS 績效 | 實盤 1 個月後落在 WFA 95% 信賴區間內 |
| 熔斷規則 | 手動模擬 DD > 限額 → 自動停單通過測試 |

---

## 10. 風險與緩解

| 風險 | 嚴重度 | 緩解 |
| :--- | :---: | :--- |
| TQuant-Lab 84 stars 社群小 | M | Zipline 本體 17k stars，TQuant-Lab 只是台股 patch；可 fork 到自己 repo 不依賴 upstream |
| TEJ 改 TQuant-Lab license | L | MIT 已授權，fork 後不可撤回 |
| FinLab 5GB/月流量限制 | **H** | 一次性歷史回填寫入 Zipline bundle 後永久本地；日增量打 API；流量 monitor 在 Grafana |
| FinLab 引擎精度爭議 | — | 不用 `finlab.sim`，只用其資料 |
| FinLab 倒閉 / 漲價 | M | FinMind bundle 為 fallback，已驗證可工作（M1 既有實作） |
| Zipline event-driven 慢 | M | vectorbt 副引擎跑 grid/WFA，Zipline 只跑 final 對拍 |
| Zipline API 學習曲線 | L | 1–2 週可掌握；Quantopian 教材豐富 |
| Shioaji SDK API 變更 | M | Broker 邏輯隔離在 `shioaji_broker.py`，升級時只動該檔 |
| 7 訊號優先序在 Zipline | — | Event-driven 天然支援，比 vectorized 更好 |
| Paper / Live 即時資料中斷 | **H** | 雙資料源（FinLab + Shioaji quote）互為備援；中斷觸發 Discord Critical |
| 統計驗證自寫 PBO/DSR 出錯 | M | 對 Bailey 論文表格範例做 unit test；pypbo 結果作 reference（不依賴只比對） |
| 單人開發節奏失控 | **H** | 每個 milestone 不通過 acceptance 不晉升；Buffer 2 週 |

---

## 11. 不做什麼（Linus-style 反清單）

| ❌ 不做 | 為什麼 |
| :--- | :--- |
| 不自建 framework | 用 TQuant-Lab，業界 7 層 reference 已有實作 |
| 不重構 M1 既有 962 LOC | 搬路徑、補 wrapper，0 改動 |
| 不為「未來可能換廠商」過度抽象 | Zipline 已有 Broker 介面 |
| 不在 M2 上實盤 | M5 才上，前 4 個 milestone 都在驗證 |
| 不寫 React 前端 | Streamlit 已夠 |
| 不導入 Kubernetes / Airflow | 單人開發，Prefect / cron 已夠 |
| 不付費 vectorbt PRO | 開源版 + 自寫 WFA 已夠 |
| 不用 `finlab.sim()` 當引擎 | 黑盒 + 精度爭議 |
| 不接 mlfinlab / pypbo | 授權風險（AGPL / 商業），自寫 ~300 LOC 即可 |
| 不在 Sprint 0 跳步 | 任一 spike fail 必須退回 Hybrid |

---

## 12. 與既有文檔的關係

| 文檔 | 關係 | 動作 |
| :--- | :--- | :--- |
| [02_project_brief_and_prd.md](./02_project_brief_and_prd.md) §4 功能範圍表 | **被取代**：原 M2 rqalpha + M3 vectorbt + M4 Streamlit 已改 | M2 啟動前更新 PRD 表 4.1 |
| [02_project_brief_and_prd.md](./02_project_brief_and_prd.md) §4 依賴清單 | **被取代**：新增 FinLab、zipline-reloaded、Streamlit、Grafana、Prometheus（ADR-013）| M2 啟動前更新 |
| [05_architecture_and_design_document.md](./05_architecture_and_design_document.md) §1.4 技術選型 | **被取代**：回測（主）從 rqalpha 改 zipline-reloaded；新增 FinLab（ADR-013）| M2 啟動前更新 |
| [05_architecture_and_design_document.md](./05_architecture_and_design_document.md) §1.1.2 Container 表 | **擴充**：新增 dashboard、monitoring、paper/live broker 容器 | M2 啟動前更新 |
| [05_architecture_and_design_document.md](./05_architecture_and_design_document.md) §3.3 元件職責 | **擴充**：新增 adapters、validation、orchestration、monitoring、dashboard | M2 啟動前更新 |
| [05_architecture_and_design_document.md](./05_architecture_and_design_document.md) §7.2 演進路線 | **重寫** Phase 2–5 | M2 啟動前更新 |
| [adrs/ADR-001-engine-rqalpha-plus-vectorbt.md](./adrs/ADR-001-engine-rqalpha-plus-vectorbt.md) | **被取代** | 標 Superseded，指向 ADR-005 |
| [adrs/ADR-002-timescaledb-for-time-series.md](./adrs/ADR-002-timescaledb-for-time-series.md) | 維持有效 | — |
| [adrs/ADR-003-pure-function-strategy-layer.md](./adrs/ADR-003-pure-function-strategy-layer.md) | **加強適用**（純函式設計讓三模式共用變可能） | 加註交叉引用 |
| [adrs/ADR-004-pydantic-frozen-config.md](./adrs/ADR-004-pydantic-frozen-config.md) | 維持有效 | — |
| ADR-005（新增→已 superseded） | Engine：TQuant-Lab 主 + vectorbt 副，取代 ADR-001 | 已新增；**ADR-013 已 supersede 主骨架選擇為 zipline-reloaded** |
| ADR-006（新增） | Data source：FinLab 主 + FinMind fallback | 待新增 |
| ADR-007（新增） | Three modes：backtest/paper/live 共用 strategy | 待新增 |
| ADR-008（新增） | Monitoring：Streamlit + Grafana + Discord 三層 | 待新增 |
| ADR-009（新增） | Statistical validation：自寫 PBO/DSR/CPCV 避 AGPL | 待新增 |
| [18_reference_architecture_and_metrics.md](./18_reference_architecture_and_metrics.md) | 本文件 §3 的詳細展開 | 同步建立 |
| [01_workflow_manual.md §5.A](./01_workflow_manual.md) | 本文件 §7.2 的詳細展開 | 同步建立 |
| [research_open_source_backtest_platforms.md](./research_open_source_backtest_platforms.md) | 本變更的調研基礎 | 維持作 reference |

---

## 變更紀錄

| 版本 | 日期 | 變更 |
| :--- | :--- | :--- |
| v1.0 | 2026-05-31 | 初版（取代原 02 PRD §4 與 05 架構 §1.4 中 rqalpha + vectorbt 雙引擎技術線）|
