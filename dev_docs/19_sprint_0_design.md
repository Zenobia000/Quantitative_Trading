# Sprint 0 — 設計與執行手冊

> **版本：** v1.0 | **更新：** 2026-05-31 | **狀態：** 待執行（M2 啟動前 1 週）
> **性質：** Gate — 任一 spike fail 退回 Hybrid 路線
> **對應 plan：** [17_m2_to_m5_master_plan.md](./17_m2_to_m5_master_plan.md) §7.2、§9.1
> **對應 ADR：** ADR-005（雙引擎）、ADR-006（FinLab 主資料源）

---

## 1. Sprint 0 目的

### 1.1 為什麼需要 Gate

| 風險 | 不做 Sprint 0 的後果 |
| :--- | :--- |
| TQuant-Lab 安裝 / XTAI 日曆不通 | M2 第 1 週才發現，整個技術線失敗 |
| M1 純函式 plug 進 Zipline Algorithm 不順 | M2 第 2–3 週才發現，需重設計 wrapper |
| FinLab bundle ingester 跑不出來 | M3 才發現，被迫切回 FinMind fallback |
| Shioaji 沙箱範例跑不通 | M5 才發現，實盤路徑失敗 |
| FinLab 即時資料 polling 不穩 | M4 paper trading 失敗 |
| Streamlit + TimescaleDB 連不上 | M3 monitor 失敗，被迫改方案 |

**Sprint 0 用 1 週把這 6 個 unknown 提前驗證。任一 fail 立即退場，不浪費 M2 的 4 週。**

### 1.2 Gate 性質

| 結果 | 行動 |
| :--- | :--- |
| 6 spike 全綠 | **Pass** — 啟動 M2 |
| 任一 spike 紅但可短期修復 (< 2 天) | **Conditional Pass** — 修復後再 review |
| 任一 spike 紅且需重新設計 | **Fail** — 退回對應退場路線（見 §6） |

---

## 2. 時程

### 2.1 1 週分配（5 工作日 + 2 weekend buffer）

| 日 | Spike | 平行 |
| :---: | :--- | :--- |
| **D1** | S1 (TQuant-Lab 安裝) + S5 (FinLab polling) | ✅ |
| **D2** | S2 (M1 plug Zipline) | — |
| **D3** | S3 (FinLab bundle ingester) | — |
| **D4** | S4 (Shioaji 沙箱) + S6 (Streamlit) | ✅ |
| **D5** | Gate Review + 修復 | — |
| **D6–D7** | Buffer（如有 Conditional） | — |

### 2.2 並行策略

| Spike 對 | 為何可並行 |
| :--- | :--- |
| S1 + S5 | 不同套件、不同 API、無相依 |
| S4 + S6 | Shioaji 沙箱（網路） + Streamlit（本機 DB），無資源衝突 |

---

## 3. 前置條件清單

> **未滿足前置條件不得啟動 Sprint 0**。

| 類別 | 項目 | 取得方式 | 預估時間 |
| :--- | :--- | :--- | :---: |
| 訂閱 | FinLab 付費帳號 + API key | https://ai.finlab.tw/signup | 1 天（含付款處理） |
| Repo | TQuant-Lab clone | `git clone https://github.com/tejtw/TQuant-Lab` | 5 分鐘 |
| Repo | TEJ Shioaji 整合範例 clone | `git clone https://github.com/tejtw/TEJAPI_Python_Medium_Application` | 5 分鐘 |
| 憑證 | Shioaji 沙箱憑證 | 永豐金沙箱申請 https://sinotrade.github.io/ | 1–3 天 |
| 環境 | Python 3.10.x（**非 3.11+**，Zipline 相容） | pyenv | 30 分鐘 |
| 環境 | TA-Lib 系統套件 | Windows：vcpkg / WSL：apt | 30 分鐘 |
| 環境 | TimescaleDB Docker | `docker-compose up -d timescaledb` | 10 分鐘 |
| 帳號 | Telegram Bot Token（S6 後續） | @BotFather | 5 分鐘 |
| 知識 | Zipline `algorithm` 教學略讀（Quantopian Lectures） | https://www.quantrocket.com/codeload/quant-finance-lectures/quant_finance_lectures/Lecture01-Introduction-to-Research.ipynb.html | 2 小時 |

**前置 checklist 全綠才啟動 Sprint 0。**

---

## 4. 6 個 Spike 詳細規格

### 4.1 S1 — TQuant-Lab + XTAI 安裝

| 項目 | 內容 |
| :--- | :--- |
| **目的** | 驗證 TQuant-Lab 在 Windows + WSL 環境可安裝、`exchange_calendar_xtai` 可載入、`zipline run` 可跑 hello world |
| **Input** | TQuant-Lab repo、Python 3.10、TA-Lib 系統套件 |
| **Steps** | 1. `poetry install`（或 `pip install -e .`）<br>2. `zipline ingest -b tquant`（含內建 sample data）<br>3. 寫 `hello.py`：印出 SPY 收盤價<br>4. `zipline run -f hello.py -b tquant --start 2020-01-01 --end 2020-12-31` |
| **Pass 標準** | (a) ingest 完成無錯<br>(b) `zipline run` 跑完輸出 perf DataFrame<br>(c) trade calendar 認得 2024-02-08（台股春節休市）|
| **Fail 退場** | 安裝失敗或 XTAI 不通 → **退回 Hybrid（自寫 Zipline calendar mod）** 或 **改用 zipline-reloaded + 自寫 XTAI**（額外 1 週） |
| **估時** | 4 小時 |
| **風險** | TA-Lib Windows 安裝坑 → 改用 WSL Ubuntu 22.04 |

### 4.2 S2 — M1 純函式 plug 進 Zipline Algorithm

| 項目 | 內容 |
| :--- | :--- |
| **目的** | 驗證 M1 既有 `compute_scores()` + `compute_signals()` 可在 Zipline algorithm 內被呼叫，且結果與 M1 `pipeline.py` 一致 |
| **Input** | S1 通過、M1 `strategy/scoring.py`、`strategy/signals.py`、M1 `pipeline.py` 對 2330 的歷史 calendar CSV（baseline） |
| **Steps** | 1. 寫 `strategies/four_layer_resonance/__init__.py` skeleton<br>2. 在 `initialize` 載入 strategy_config<br>3. 在 `handle_data` 內取 history bars → 餵 `compute_scores` → 餵 `compute_signals` → emit Zipline order<br>4. 對 2330 跑 2023-01-01 ~ 2023-12-31<br>5. 輸出 trade log，與 M1 `pipeline.py` 對拍 |
| **Pass 標準** | (a) 1 年 252 個 bar 全部成功計算<br>(b) calendar CSV 與 M1 `pipeline.py` 訊號差異 < 0.1%（< 1 個 bar 差異）|
| **Fail 退場** | (a) Zipline `history` API 與 M1 DataFrame schema 不相容 → **加 ACL 層轉換**（+ 2 天）<br>(b) 訊號差異 > 1% → **強制 debug** 找根因，不可進入 M2 |
| **估時** | 8 小時 |
| **風險** | Zipline `history()` 回傳 panel 與 M1 DataFrame 欄位不一致 → 寫 normalize helper |

### 4.3 S3 — FinLab Bundle Ingester POC

| 項目 | 內容 |
| :--- | :--- |
| **目的** | 驗證 FinLab API 可拉資料、可寫入 Zipline bundle 格式、`zipline run` 可使用該 bundle |
| **Input** | S1 通過、FinLab API key、3 檔股票（2330, 2454, 2317）|
| **Steps** | 1. 寫 `adapters/data_bundle/finlab_bundle.py` POC<br>2. `import finlab; finlab.login(token)` → 拉 3 檔 2024 年日 K<br>3. 轉成 Zipline `register_bundle` 需要的格式（OHLCV + adjustments）<br>4. `python -m adapters.data_bundle.finlab_bundle --stocks 2330,2454,2317 --start 2024-01-01 --end 2024-12-31`<br>5. `zipline run -f hello.py -b finlab` 確認可讀 |
| **Pass 標準** | (a) 3 檔 × 1 年 ingest 完成<br>(b) `zipline run` 在 finlab bundle 上跑通<br>(c) 對拍 FinLab 原始 DataFrame：價格欄位 100% 一致 |
| **Fail 退場** | (a) FinLab API 流量限制踩線 → 改抓 1 檔 1 個月驗證即可<br>(b) bundle ingest 格式不通 → **退回 Hybrid（用 FinMind bundle 為主，FinLab 為輔）**（M2 改 4 → 5 週） |
| **估時** | 8 小時 |
| **風險** | FinLab 復權資料與 Zipline `adjustments` table 格式不一致 → 寫轉換 helper |

### 4.4 S4 — Shioaji 沙箱範例

| 項目 | 內容 |
| :--- | :--- |
| **目的** | 驗證 Shioaji SDK 可登入沙箱、可下單、TEJ 官方範例可跑通 |
| **Input** | 永豐金沙箱憑證（CA 證書 + 密碼）、`tejtw/TEJAPI_Python_Medium_Application` repo |
| **Steps** | 1. `pip install shioaji`<br>2. 沙箱登入：`api = sj.Shioaji(simulation=True); api.login(...)`<br>3. 抄 TEJ 範例的下單程式碼<br>4. 下一筆 2330 模擬市價單<br>5. 確認 order callback 收到 fill 訊息 |
| **Pass 標準** | (a) 登入成功<br>(b) 下單成功（沙箱回 ack）<br>(c) callback 收到 fill 事件 |
| **Fail 退場** | (a) 沙箱憑證未到 → **延後 Sprint 0**，等憑證再啟動<br>(b) Shioaji SDK 與 TEJ 範例不相容（版本差異）→ **改參考 Sinotrade/Shioaji 官方 doc**（+ 1 天）<br>(c) 完全卡住 → **M4 才驗證**，M5 上線時間延後 |
| **估時** | 4 小時 |
| **風險** | Shioaji 沙箱 callback timing 不穩 → 加 retry / sleep |

### 4.5 S5 — FinLab 即時資料 Polling

| 項目 | 內容 |
| :--- | :--- |
| **目的** | 驗證 FinLab 可提供盤中即時資料（1 分鐘 bar 或 tick）、polling 穩定、可餵進 Paper/Live broker |
| **Input** | FinLab API key、盤中時段（09:00–13:30 任一）|
| **Steps** | 1. 寫 `adapters/data_feed/finlab_live.py` POC<br>2. 對 2330 每 60 秒呼叫一次 FinLab realtime API<br>3. 連續 1 小時，記錄成功率<br>4. 對拍 Yahoo / TWSE 即時報價 |
| **Pass 標準** | (a) 60 次 polling 中 ≥ 55 次成功（91.7%）<br>(b) 價格與 Yahoo / TWSE 差異 < 0.5%（accounting for FinLab 延遲）|
| **Fail 退場** | (a) FinLab 無即時 API → **改用 Shioaji 報價作為即時資料源**（M4 paper 階段切換）<br>(b) 成功率 < 80% → **改用 Shioaji 報價** |
| **估時** | 2 小時 setup + 1 小時等盤中 |
| **風險** | 必須在盤中執行（時間窗）→ 安排在 D1 上午 |

### 4.6 S6 — Streamlit 連 TimescaleDB

| 項目 | 內容 |
| :--- | :--- |
| **目的** | 驗證 Streamlit 可連 TimescaleDB、可渲染 equity curve、頁面 < 2 秒載入 |
| **Input** | S1 不需通過；TimescaleDB Docker、Streamlit 套件 |
| **Steps** | 1. `pip install streamlit psycopg2-binary plotly`<br>2. 建 sample table `equity_snapshots` 插入 1000 行假資料<br>3. 寫 `dashboard/streamlit_app.py` MVP：connection + plotly line chart<br>4. `streamlit run dashboard/streamlit_app.py` 開 localhost:8501<br>5. F12 測 first paint 時間 |
| **Pass 標準** | (a) 連線成功<br>(b) equity curve 渲染正確<br>(c) 頁面首次載入 < 2 秒 |
| **Fail 退場** | (a) Streamlit 渲染慢 > 5 秒 → **改 Plotly Dash 或 Gradio**（+ 1 天評估）<br>(b) TimescaleDB connection 不通 → **檢查 Docker port mapping**（必須通，否則整個 L7 失敗） |
| **估時** | 3 小時 |
| **風險** | 低 |

---

## 5. Gate Review 流程

### 5.1 D5 Gate Review 議程

| 時段 | 內容 |
| :--- | :--- |
| 09:00–10:00 | 6 spike 結果匯整 + 證據（log / screenshot / pytest 報告）|
| 10:00–11:00 | 決策樹評估（見 §5.2） |
| 11:00–12:00 | 決策紀錄寫入 `dev_docs/sprint_0_gate_review.md` |
| 14:00–17:00 | 若 Pass → 啟動 M2 第 1 個 sprint planning；若 Fail → 啟動退場路線 |

### 5.2 決策樹

```
6 spike 結果
│
├── 全綠 ──────────────────────→ Pass，啟動 M2
│
├── S1 紅 ────→ Hybrid（自寫 calendar mod 或 zipline-reloaded + 自寫 XTAI）
├── S2 紅 ────→ 強制 debug，不可進 M2
├── S3 紅 ────→ Hybrid（FinMind 主，FinLab 為輔；M2 延 1 週）
├── S4 紅 ────→ 延後 Sprint 0 等沙箱憑證 / 或 M4 才驗證（M5 延後）
├── S5 紅 ────→ 改用 Shioaji 報價作即時資料源（M4 階段切換）
└── S6 紅 ────→ 改 Plotly Dash 或 Gradio
```

### 5.3 Gate Review 產出物

| 文件 | 路徑 |
| :--- | :--- |
| 6 個 spike 報告 | `dev_docs/spikes/S{1-6}_report.md` |
| Gate Review 決議 | `dev_docs/sprint_0_gate_review.md` |
| 退場路線決策（若有）| `dev_docs/adrs/ADR-010-fallback-route.md`（如觸發）|

---

## 6. 失敗備援路線

### 6.1 Hybrid 路線（S1 或 S3 fail）

| 變更項目 | 替代方案 | 影響 |
| :--- | :--- | :--- |
| 主骨架 | zipline-reloaded（非 TQuant-Lab）+ 自寫 XTAI calendar | + 1 週開發 |
| 資料源主 | FinMind（M1 既有 ETL）| 缺券商分點，v2 L3 籌碼分降級 |
| 資料源輔 | FinLab（只拉券商分點補 v2 L3） | 流量壓力小 |
| 自寫 LOC 估算 | ~4000 LOC（vs 原 ~2500） | + 60% |
| 上線時間 | 18 週（vs 原 17 週） | + 1 週 |

### 6.2 FinMind Fallback（S3 + S5 都 fail）

| 變更項目 | 替代方案 |
| :--- | :--- |
| 資料源 | 100% FinMind + TWSE 補爬 |
| 即時資料 | 100% Shioaji 報價 |
| v2 L3 籌碼分 | 自爬 TWSE 券商分點頁面 |
| FinLab 訂閱 | **取消**（省 9–10k TWD/年）|

### 6.3 自寫 Adapter Fallback（S1 fail 且 zipline-reloaded 也不通）

| 變更項目 | 替代方案 |
| :--- | :--- |
| 主骨架 | 純 vectorbt + 自寫薄薄 event-driven 包裝層 |
| L4 Portfolio | 全自寫 |
| L6 OMS | 全自寫（Paper + Shioaji） |
| 自寫 LOC 估算 | ~5500 LOC |
| 上線時間 | 21 週 |
| 7 訊號優先序 | 需自寫狀態機，回到 Plan A 的痛點 |

### 6.4 退場路線決策矩陣

| Spike Fail 組合 | 退場路線 | 上線時間 |
| :--- | :--- | :---: |
| 只 S5 fail | 維持 Plan TQuant-Lab，M4 用 Shioaji 報價 | 17 週 |
| 只 S6 fail | 維持 Plan TQuant-Lab，改 Plotly Dash | 17 週 |
| 只 S4 fail | 維持 Plan TQuant-Lab，M5 才驗證 Shioaji（風險集中後段）| 17 + 1 週 |
| 只 S3 fail | Hybrid（FinMind 主 + FinLab 補）| 18 週 |
| 只 S1 fail | Hybrid（zipline-reloaded + 自寫 XTAI）| 18 週 |
| S1 + S3 都 fail | FinMind Fallback + 自寫 calendar | 20 週 |
| S1 + S3 + S5 都 fail | 自寫 Adapter Fallback | 21 週 |
| S2 fail | **強制 debug**，不退場（純函式 plug 是 deal-breaker） | 17 + 不定 |

---

## 7. 產出物（Sprint 0 結束後應有的文件）

| 文件 | 位置 | 用途 |
| :--- | :--- | :--- |
| 6 個 Spike 報告 | `dev_docs/spikes/S{1-6}_report.md` | 每個 spike 的 Steps / Result / Evidence / Decision |
| Gate Review 決議書 | `dev_docs/sprint_0_gate_review.md` | Pass/Fail + 退場路線（如觸發） |
| Hello World 程式碼 | `tests/spikes/hello.py`、`test_zipline_algorithm.py` | S1/S2 可重跑驗證 |
| FinLab Bundle POC | `adapters/data_bundle/finlab_bundle.py` | S3 產出（M2 直接接續開發） |
| Shioaji 沙箱範例 | `tests/integration/test_shioaji_sandbox.py` | S4 產出（M5 直接接續開發） |
| Streamlit MVP | `dashboard/streamlit_app.py` | S6 產出（M3 直接接續開發） |
| 退場路線 ADR（如觸發） | `dev_docs/adrs/ADR-010-fallback-route.md` | 紀錄退場決策 |
| M2 Sprint 1 planning | `dev_docs/m2_sprint1_plan.md` | Pass 後立即啟動 |

---

## 8. 與既有文檔的關係

| 文檔 | 關係 |
| :--- | :--- |
| [17_m2_to_m5_master_plan.md](./17_m2_to_m5_master_plan.md) §7.2、§9.1 | 本文件是其詳細展開 |
| [18_reference_architecture_and_metrics.md](./18_reference_architecture_and_metrics.md) | Sprint 0 不驗證 metrics 細節（M3 才做），但 S2 / S3 通過後 metrics enum stub 可開始建立 |
| [05_architecture_and_design_document.md](./05_architecture_and_design_document.md) §1.1.2 Container | S1 / S3 結果可能要求更新 Container 表（FinLab 容器新增）|
| [adrs/](./adrs/) | Sprint 0 結果可能新增 ADR-005~010 |

---

## 變更紀錄

| 版本 | 日期 | 變更 |
| :--- | :--- | :--- |
| v1.0 | 2026-05-31 | 初版（6 spike 詳細規格 + 決策樹 + 退場路線）|
