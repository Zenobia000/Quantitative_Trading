# ADR-001: 雙回測引擎：rqalpha（主）+ vectorbt（副）

> **狀態：** 已接受 | **日期：** 2026-05-26 | **決策者：** Self

---

## 1. 背景與問題

- **上下文**：M2 需要選定回測引擎，跑 portfolio 級別的 IS 回測
- **問題**：單一引擎難以同時滿足「事件驅動精確模擬」與「向量化參數網格」兩種需求
- **驅動因素 / 約束**：
  - 必須支援 T+1 限制、漲跌停、整股單位、手續費 / 證交稅
  - 必須支援 portfolio 級別（多檔同時持倉、Heat 計算）
  - 必須能跑 100+ runs 的參數網格（DOE-3、DOE-4）
  - 訊號邏輯**只能有一份程式碼**（避免雙引擎不一致）

---

## 2. 考量的選項

### 選項一：純 rqalpha
- **描述**：用 rqalpha + 自訂 `mod_taiwan_stock` 處理台股
- **優點**：事件驅動精確、支援 portfolio、台灣社群成熟
- **缺點**：跑 100 runs 參數網格慢（每 run 1–5 分鐘）
- **成本/複雜度**：中

### 選項二：純 vectorbt
- **描述**：用 vectorbt 向量化跑所有回測
- **優點**：速度極快、原生支援參數網格
- **缺點**：事件驅動弱、portfolio 模擬需要自己寫、台股 T+1/漲跌停需手動處理
- **成本/複雜度**：高（需自寫 portfolio 邏輯）

### 選項三：雙引擎（rqalpha 主 + vectorbt 副）
- **描述**：rqalpha 跑精確回測，vectorbt 跑參數網格 / WFA / Monte Carlo
- **優點**：各取所長、訊號邏輯抽成 pure function 雙方共用
- **缺點**：需確保兩引擎結果一致、開發成本較高
- **成本/複雜度**：中高

### 選項四：自寫引擎
- **描述**：從零寫 portfolio backtest engine
- **優點**：完全控制
- **缺點**：開發成本爆炸、reinvent the wheel
- **成本/複雜度**：極高

---

## 3. 決策

**選擇：選項三（雙引擎）**

**理由**：
- 訊號邏輯已抽成 `strategy/scoring.py` + `strategy/signals.py` 純函式（M1 已完成）
- 兩引擎只是「外殼」，呼叫同一份計算邏輯，結果應該一致
- M2 用 rqalpha 出單檔 IS 回測（小心精確），M3 用 vectorbt 跑 24-cell × 19-CCD 參數網格（快）
- 對齊測試確保兩引擎差異 < 0.1%

---

## 4. 後果

- **正面**：
  - 速度 + 精確兼得
  - 訊號邏輯單一真相
  - 跑 WFA 30 windows 從 ~5 hours 降到 ~30 min
- **負面**：
  - 雙引擎需要對齊測試（v2.md 5.3.3 訊號重現規則）
  - 維護成本：兩個 wrapper 都要更新
- **影響範圍**：`engines/rqalpha_runner.py`、`engines/vectorbt_runner.py`、所有 DOE 腳本
- **重新評估觸發**：對齊測試差異 > 0.5% 持續無法收斂 → 砍 vectorbt 只用 rqalpha

---

## 5. 執行計畫

1. M2 第 1 週：rqalpha 自訂 mod_taiwan_stock（交易日曆、漲跌停、手續費）
2. M2 第 2 週：`engines/rqalpha_runner.py` 包裝
3. M2 第 3 週：對 2330 跑 IS 回測，驗證與 `pipeline.py` 訊號一致
4. M3 第 1 週：`engines/vectorbt_runner.py` 包裝
5. M3 第 2 週：對齊測試（同一參數 → 結果差異 < 0.1%）
6. M3 第 3 週：跑 DOE-3 參數網格

---

| 日期 | 審核人 | 備註 |
| :--- | :--- | :--- |
| 2026-05-26 | Self | 初版 |
