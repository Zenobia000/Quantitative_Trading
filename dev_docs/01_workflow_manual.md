# 開發流程說明 — backtest_platform

> **版本：** v1.0 | **更新：** 2026-05-26 | **狀態：** 活躍

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

| 階段 | 目標 | 當前狀態 | Gate |
| :--- | :--- | :---: | :--- |
| **M0** | 策略規格定稿（`strategy/v2.md`） | ✅ v2.1.0 | 蘇格拉底審查通過 |
| **M1** | 資料 + 策略骨架 + 端到端 smoke | ✅ 完成 | 44 unit tests 全綠，2330 端到端跑通 |
| **M2** | IS 回測通過（2015–2020） | 🚧 啟動中 | rqalpha 整合 + IS 全綠燈 |
| **M3** | OOS + 統計驗證 | ⏳ 待 M2 | PBO < 30%、DSR > 0.95 |
| **M4** | Paper trading 3 個月 | ⏳ | Sharpe > 0.7 × 回測 Sharpe |
| **M5** | 小倉位實盤（1/4 倉位） | ⏳ | 月績效不退化、Shioaji 整合 |

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
| M1 → M2 | 單元測試 100% 通過、端到端 smoke 跑得起來、訊號邏輯與 XQ 差異 < 0.5% |
| M2 → M3 | IS 期間達到綠燈（CAGR > 18%、Sharpe > 1.0 等，含生存者偏誤 buffer） |
| M3 → M4 | OOS Sharpe > IS × 0.6、PBO < 30%、DSR > 0.95 |
| M4 → M5 | Paper trading 模擬 Sharpe > 回測 Sharpe × 0.7 |
| M5 → 全倉 | 連續 3 個月實盤不退化、無單日 DD > 5% |

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
