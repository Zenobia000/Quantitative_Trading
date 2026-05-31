# 開發流程說明 — backtest_platform

> **版本：** v1.1 | **更新：** 2026-05-31 | **狀態：** 活躍
> **v1.1**：合併原 `19_sprint_0_design.md` 內容（M1→M2 Sprint 0 Gate）；19 號文檔已撤回

---

## 1. 模式選擇：MVP 快速迭代

本專案採用 **MVP 模式**，理由：

| 條件 | 是否觸發完整流程 |
| :--- | :---: |
| 金流/法遵/隱私資料 | ❌（個人研究專案，無外部使用者資料） |
| 高可用與規模化 | ❌（單機、批次處理為主） |
| 跨 3+ 團隊協作 | ❌（單人開發） |
| **快速驗證策略價值假設** | ✅ |
| 時間/預算有限 | ✅ |

→ MVP 模式，按 milestone（M0–M5）迭代。

**升級觸發**：實盤對外、加入第二位協作者、引入即時下單則升級為完整流程。

---

## 2. 開發里程碑（對應 README）

```mermaid
graph LR
  M0[策略規格定稿] --> M1[資料+策略骨架]
  M1 --> M2[IS 回測]
  M2 --> M3[OOS+統計驗證]
  M3 --> M4[Paper Trading 3 月]
  M4 --> M5[小倉位實盤]
```

| 階段 | 目標 | Gate |
| :--- | :--- | :--- |
| **M0** | 策略規格定稿（`strategy/v2.md`） | 蘇格拉底審查通過 |
| **M1** | 資料 + 策略骨架 + 端到端 smoke | 44 unit tests 全綠，2330 端到端跑通 |
| **M2** | IS 回測通過（2015-2020） | TQuant-Lab 整合 + IS 全綠燈（ADR-005）|
| **M3** | OOS + 統計驗證 | PBO < 30%、DSR > 0.95 |
| **M4** | Paper trading 3 個月 | Sharpe > 0.7 × 回測 Sharpe |
| **M5** | 小倉位實盤（1/4 倉位） | 月績效不退化、Shioaji 整合 |

> **當前狀態**：見 [`16_wbs_development_plan.md`](./16_wbs_development_plan.md)（單一狀態真相源；本表只列目標與 Gate）

---

## 3. 每階段紀律

### M0 規格階段
- 任何策略變更必須更新 `strategy/v2.md` Part 6.3 changelog
- 版本號規則：MAJOR（策略本體）/ MINOR（參數）/ PATCH（bug fix）

### M1 開發階段（當前）
- 訊號邏輯**只有一份**：`strategy/scoring.py` + `strategy/signals.py` 為單一真相
- 任何修改必須伴隨單元測試（測 happy / boundary / failure 三類）
- 端到端 smoke test 確保 `pipeline.py` 在真實 FinMind 資料上能跑通

### M2 回測階段
- IS 回測在 2015–2020，可反覆調參數
- 所有測試的參數組合必須記錄（DSR N 計算）
- 對標 `strategy/v2.md` 4.3.1 綠/黃/紅燈表

### M3 統計階段
- OOS 期間 2023–2024
- **OOS 失敗 → 淘汰策略，不允許「再調一次」**

---

## 4. 文檔產出對照

每個 milestone 完成時必須產出對應文檔：

| 階段 | 必要文檔 |
| :--- | :--- |
| M0 | `strategy/v2.md` |
| M1 | `dev_docs/05_architecture_and_design_document.md`、`dev_docs/07_module_specification_and_tests.md`、`backtest_platform/docs/M1_setup.md` |
| M2 | `backtest_platform/docs/M2_backtest_report.md`（待產出） |
| M3 | `backtest_platform/docs/M3_statistical_validation_report.md`（待產出） |
| M4 | `backtest_platform/docs/M4_paper_trading_log.md`（待產出） |
| M5 | `backtest_platform/docs/M5_live_runbook.md`（待產出） |

---

## 5. Gate 度量

| Gate | 度量 |
| :--- | :--- |
| M1 → M2 | Sprint 0 6 spike 全綠（見 §5.A）+ 單元測試 100% 通過、端到端 smoke 跑得起來 |
| M2 → M3 | IS 期間達到綠燈（CAGR > 18%、Sharpe > 1.0 等，含生存者偏誤 buffer） |
| M3 → M4 | OOS Sharpe > IS × 0.6、PBO < 30%、DSR > 0.95 |
| M4 → M5 | Paper trading 模擬 Sharpe > 回測 Sharpe × 0.7 |
| M5 → 全倉 | 連續 3 個月實盤不退化、無單日 DD > 5% |

### 5.A Sprint 0 — M1→M2 Gate 詳細規格

> 2026-05-31 從原 `19_sprint_0_design.md` 合併入本節；可執行腳本在 `backtest_platform/sprint_0_spikes/`，操作步驟詳見該目錄 `RUNBOOK.md`。

#### 5.A.1 為什麼需要 Gate（風險清單）

| 風險 | 不做 Sprint 0 的後果 |
| :--- | :--- |
| TQuant-Lab 安裝 / XTAI 日曆不通 | M2 第 1 週才發現，整個技術線失敗 |
| M1 純函式 plug 進 Zipline Algorithm 不順 | M2 第 2-3 週才發現，需重設計 wrapper |
| FinLab bundle ingester 跑不出來 | M3 才發現，被迫切回 FinMind fallback |
| Shioaji 沙箱範例跑不通 | M5 才發現，實盤路徑失敗 |
| FinLab 即時資料 polling 不穩 | M4 paper trading 失敗 |
| Streamlit + TimescaleDB 連不上 | M3 monitor 失敗，被迫改方案 |

**核心精神**：用 1 週把 6 個 unknown 提前驗證；任一 fail 立即退場，不浪費 M2 的 4 週。

#### 5.A.2 6 spike 摘要表

| Spike | 主題 | 估時 | 並行 | Pass 標準 |
| :---: | :--- | :---: | :---: | :--- |
| S1 | TQuant-Lab + XTAI 安裝 | 4h | + S5 | `zipline ingest` + `zipline run` hello world 跑通；XTAI 2024 sessions ≈ 245 |
| S2 | M1 純函式 plug 進 Zipline Algorithm | 8h | — | 對 2330 一年資料，action 序列與 M1 `pipeline.py` 差異 < 0.1% |
| S3 | FinLab Bundle Ingester POC | 8h | — | 3 檔 × 1 年 ingest 成功，價格欄位與 FinLab raw 100% 一致 |
| S4 | Shioaji 沙箱範例 | 4h | + S6 | 沙箱登入 + 下單 + callback 收到 fill 事件 |
| S5 | FinLab 即時資料 Polling | 3h | + S1 | 60 次 polling ≥ 55 次成功；對拍 Yahoo/TWSE < 0.5% |
| S6 | Streamlit 連 TimescaleDB | 3h | + S4 | equity curve 渲染正確，首次載入 < 2 秒 |

#### 5.A.3 1 週日程

| Day | Spike | 平行 |
| :---: | :--- | :---: |
| D1 | S1 + S5 | ✅ |
| D2 | S2 | — |
| D3 | S3 | — |
| D4 | S4 + S6 | ✅ |
| D5 | Gate Review + 修復 | — |
| D6-D7 | Buffer | — |

#### 5.A.4 Gate Review 決策樹

| Spike Fail 組合 | 退場路線 | 上線時間 |
| :--- | :--- | :---: |
| 全綠 | **Pass — 啟動 M2 Sprint 1** | 17 週 |
| 只 S5 fail | 維持 plan，M4 用 Shioaji 報價 | 17 週 |
| 只 S6 fail | 改 Plotly Dash 或 Gradio | 17 週 |
| 只 S4 fail | M5 才驗證 Shioaji（風險集中後段） | 18 週 |
| 只 S3 fail | Hybrid（FinMind 主 + FinLab 補） | 18 週 |
| 只 S1 fail | Hybrid（zipline-reloaded + 自寫 XTAI） | 18 週 |
| S1 + S3 都 fail | FinMind Fallback + 自寫 calendar | 20 週 |
| S1 + S3 + S5 都 fail | 自寫 Adapter Fallback | 21 週 |
| **S2 fail** | **強制 debug，不退場**（純函式 plug 是 deal-breaker） | 17 + 不定 |

#### 5.A.5 失敗備援路線（高層摘要）

| 路線 | 觸發 | 主要變更 |
| :--- | :--- | :--- |
| **Hybrid** | S1 或 S3 單獨 fail | 換成 zipline-reloaded + 自寫 calendar；或 FinMind 為主 FinLab 為輔 |
| **FinMind Fallback** | S3 + S5 都 fail | 100% FinMind + TWSE 補爬；FinLab 訂閱取消 |
| **自寫 Adapter Fallback** | S1 fail 且 zipline-reloaded 也不通 | 純 vectorbt + 自寫薄薄 event-driven，~5500 LOC |

#### 5.A.6 Sprint 0 產出物

| 文件 / 程式碼 | 位置 |
| :--- | :--- |
| 6 個 Spike 報告 | `backtest_platform/sprint_0_spikes/results/S*.json` |
| Gate Review 決議書 | `backtest_platform/sprint_0_spikes/results/gate_review.md` |
| FinLab Bundle POC | `backtest_platform/sprint_0_spikes/s3_finlab_bundle_poc.py` |
| Shioaji 沙箱範例 | `backtest_platform/sprint_0_spikes/s4_shioaji_sandbox.py` |
| Streamlit MVP | `backtest_platform/sprint_0_spikes/s6_streamlit_dashboard.py` |
| 退場路線 ADR（若觸發） | `dev_docs/adrs/ADR-010-fallback-route.md` |

---

## 6. 檢查清單（每階段必過）

### 通用
- [ ] 對應 milestone 的文檔已更新
- [ ] 對應的 ADR 已記錄重大決策
- [ ] 測試覆蓋率 > 80%
- [ ] 沒有 hardcoded secrets

### 策略相關
- [ ] 訊號邏輯與 `strategy/v2.md` 一致
- [ ] 任何門檻調整在 v2.md 6.3 留下時間戳
- [ ] DSR N（測試組合數）已記錄
