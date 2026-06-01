# ADR-008: 三模式（Backtest / Paper / Live）共用同一份 Strategy Code

> **狀態：** 已接受 | **日期：** 2026-05-31 | **決策者：** Self
> **Related：** ADR-003（純函式策略層）、ADR-005（Zipline 主骨架）

---

## 1. 背景與問題

- **上下文**：使用者明確要求系統定位由「純回測平台」升級為「完整交易系統」，必須同時支援實際交易（live）與虛擬交易驗證（paper trading 3 個月）。
- **問題**：
  - 若 backtest / paper / live 三模式各自維護 strategy code，必然出現「研究時跑得好、實盤時走樣」的不一致 bug
  - 訊號邏輯散落在三個 entry point，回歸測試成本指數成長
  - M1 既有純函式策略層必須能 100% 共用，不可重寫
- **驅動因素 / 約束**：
  - 訊號邏輯必須單一真相（延續 ADR-003）
  - 三模式只應在 I/O 邊界（資料源、broker、輸出）有差異
  - 自寫程式碼控制在 ~2500 LOC（plan § 5）
  - M5 上實盤前必須有至少 3 個月 paper trading 驗證

---

## 2. 考量的選項

### 選項一：三套 entry point，各自實作
- **描述**：`backtest.py` / `paper.py` / `live.py` 三個獨立 script，各自實作完整流程
- **優點**：模式間完全解耦、互不影響
- **缺點**：
  - 訊號邏輯重複三次，必然漂移
  - 對拍測試成本爆炸（三模式兩兩配對 = 3 套對拍）
  - 違反 ADR-003 純函式單一真相原則
- **成本/複雜度**：高（且品質風險極高）

### 選項二：共用 strategy module，三套 orchestration script
- **描述**：strategy 純函式抽出，但 orchestration（資料拉取 → 訊號 → 下單 → 紀錄）三模式各寫一份
- **優點**：訊號邏輯共用、orchestration 解耦
- **缺點**：
  - orchestration 邏輯仍重複（流程很相似但又有差異）
  - 三模式間切換需改 entry point
  - 與 Zipline 既有設計（strategy / execution 解耦）重複造輪
- **成本/複雜度**：中

### 選項三：Zipline Algorithm + 三個 plug 點 ★採納
- **描述**：以 Zipline 原生設計優勢為核心，strategy 與 execution 解耦，三模式只切換三個 plug 點：資料源（DataPortal / DataFeed）、broker（Blotter）、輸出（Recorder）；M1 scoring/signals 純函式 + 一個 Zipline algorithm wrapper（~100 LOC）三模式 100% 共用
- **優點**：
  - 訊號邏輯單一真相（延續 ADR-003）
  - Zipline 原生設計，不違反框架
  - 三模式切換僅改 CLI flag，無需改 strategy code
  - paper / live 在 3 個月驗證後切換成本接近 0
- **缺點**：
  - 需熟悉 Zipline Blotter / Broker / Bundle 抽象
  - PaperBroker 需自寫（即時資料 + 模擬撮合）
- **成本/複雜度**：中

### 選項四：以 Prefect / Airflow 為 orchestrator
- **描述**：用工作流引擎統一三模式
- **優點**：可視化、可重跑
- **缺點**：
  - 單人開發引入 Prefect / Airflow 過重（plan § 12 反清單）
  - 與 Zipline 既有設計重複
  - 並不解決 strategy code 共用問題
- **成本/複雜度**：高

---

## 3. 決策

**選擇：選項三（Zipline Algorithm + 三個 plug 點）**

**理由**：
- Zipline 核心設計優勢就是 strategy 與 execution 解耦，順著框架走最省力
- M1 純函式（scoring.py / signals.py / indicators.py）100% 直接搬，0 改動（plan § 6）
- 三個 plug 點對應 plan § 3 表格：

  | 模式 | 資料源 | Broker | 輸出 |
  |:--|:--|:--|:--|
  | Backtest | Historical bundle (FinLab/FinMind) | `SimulationBlotter` (Zipline 內建) | Parquet |
  | Paper | Live data feed (FinLab realtime) | `PaperBroker`（自寫 ~150 LOC） | TimescaleDB |
  | Live | Live data feed (FinLab/Shioaji quote) | `ShioajiBroker`（抄 TEJ 範例 ~150 LOC） | TimescaleDB |

- CLI 介面統一：

  ```
  zipline run --bundle finlab --start 2015 --end 2024              # Backtest
  zipline run --bundle finlab-live --paper --broker sim            # Paper
  zipline run --bundle finlab-live --broker shioaji                # Live
  ```

- 詳見 plan `C:\Users\xdxd2\.claude\plans\maintain-calm-blossom.md` § 3

---

## 4. 後果

- **正面**：
  - Strategy code 三模式 100% 共用，無漂移風險
  - Paper → Live 切換僅改一個 CLI flag
  - M1 既有 962 LOC 0 重構
  - 對拍測試只需 backtest vs paper 一組（而非三模式兩兩配對）
- **負面**：
  - PaperBroker 需自寫（~150 LOC，模擬撮合邏輯）
  - 即時資料源中斷會同時影響 paper 與 live 模式（緩解：雙資料源備援 FinLab + Shioaji quote，見 plan 風險表）
- **影響範圍**：
  - `strategies/four_layer_resonance/__init__.py`（單一 Zipline algorithm wrapper，三模式共用）
  - `adapters/brokers/paper_broker.py`（新增 ~150 LOC）
  - `adapters/brokers/shioaji_broker.py`（新增 ~150 LOC，抄 TEJ 範例）
  - `adapters/data_feed/finlab_live.py`（paper + live 共用）
  - `orchestration/cli.py`（新增 ~100 LOC，click 包裝三模式切換）
- **重新評估觸發**：
  - PaperBroker 模擬撮合與 ShioajiBroker 實盤結果差異 > 1% 持續 → 重新檢視撮合假設
  - Paper 3 個月驗證期 OOS 績效落在 WFA 信賴區間外 → 暫緩 M5 上實盤
  - Zipline Algorithm 抽象不足以表達某類訊號（如 intraday tick）→ 評估擴展或回退選項二

---

## 5. 執行計畫

1. **M2 W2**：`strategies/four_layer_resonance/__init__.py` Zipline algorithm wrapper（~100 LOC），確認 backtest 模式跑通
2. **M2 W4**：backtest mode 端到端驗收（plan § 11 M2 驗收）
3. **M4 W1**：撰寫 `adapters/brokers/paper_broker.py` + `adapters/data_feed/finlab_live.py`
4. **M4 W2**：撰寫 `orchestration/cli.py` 統一三模式入口
5. **M4 W3-W5**：paper trading 連續跑 3 個月，每日成功 emit 訊號 + 模擬下單
6. **M5 W1**：抄 `tejtw/TEJAPI_Python_Medium_Application` 撰寫 `adapters/brokers/shioaji_broker.py`
7. **M5 W2**：實盤小倉位（總資本 5%）切 ShioajiBroker
8. **回歸測試**：CI 強制執行「同 strategy 跨三模式輸出一致性」測試

---

| 日期 | 審核人 | 備註 |
| :--- | :--- | :--- |
| 2026-05-31 | Self | 初版 |
