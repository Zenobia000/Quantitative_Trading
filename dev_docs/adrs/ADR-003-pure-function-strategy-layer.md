# ADR-003: 策略層採用純函式設計（compute_scores / compute_signals）

> **狀態：** 已接受 | **日期：** 2026-05-26 | **決策者：** Self

---

## 1. 背景與問題

- **上下文**：四層共振戰法的訊號邏輯必須被多個地方呼叫：rqalpha 引擎、vectorbt 引擎、即時監控、回測 audit
- **問題**：如果每個地方各自實作，必然不一致；如果包成 class，狀態管理會洩漏到計算層
- **驅動因素 / 約束**：
  - **單一真相**：v2.md 5.3.3 要求「線上算的訊號與線下重算的訊號差異 < 5%」
  - 必須能在 jupyter notebook、CLI、引擎裡都呼叫
  - 必須能 vectorize（pandas 整批處理 vs 逐 bar）
  - 必須容易測試（給輸入 → 預期輸出，無副作用）

---

## 2. 考量的選項

### 選項一：StrategyClass 物件導向
- **描述**：`class FourLayerStrategy { on_bar(bar) -> Signal }`
- **優點**：符合 OO 直覺、引擎可注入策略物件
- **缺點**：狀態洩漏（in_position、entry_cost_price 都變 instance 變數）、難 vectorize、測試需建 instance
- **成本/複雜度**：中

### 選項二：純函式 + Pydantic config
- **描述**：`compute_scores(df, config)` / `compute_signals(df_scored, config)`，狀態由呼叫方持有
- **優點**：可 vectorize、易測試、結果可重現（同輸入同輸出）
- **缺點**：呼叫方需自己管 in_position 狀態
- **成本/複雜度**：低

### 選項三：函式 + 雙模式（vectorized + per-bar）
- **描述**：`compute_signals` 給 vectorbt 用，`evaluate_bar` 給 rqalpha 用，內部共用 `_evaluate_priority`
- **優點**：兩種引擎都吃同一份邏輯
- **缺點**：兩個 wrapper 需保持同步
- **成本/複雜度**：低中

---

## 3. 決策

**選擇：選項三（純函式 + 雙模式）**

**理由**：
- 計分層完全純函式（`compute_scores` 給 DataFrame 回 DataFrame）
- 訊號層提供兩個入口：
  - `compute_signals(df_scored, config)`：vectorbt 用，walk bars 模擬單一 long-only position
  - `evaluate_bar(bar: EvaluateBar, config)`：rqalpha 用，引擎負責持有 position state
- 兩者內部共用 `_evaluate_priority` 函式（單一決策邏輯）
- `StrategyConfig` 是 Pydantic `frozen=True` model，傳入後不可變

---

## 4. 後果

- **正面**：
  - 訊號邏輯有單一真相（`_evaluate_priority`）
  - 測試容易：給 fixture DataFrame → assert 結果欄位
  - vectorbt 可大規模 parallel
- **負面**：
  - rqalpha 需自己組 `EvaluateBar` dataclass（從 bar + position state）
  - 雙入口需確保語意一致（已有 8 個對齊測試）
- **影響範圍**：`strategy/scoring.py`、`strategy/signals.py`、所有引擎 wrapper
- **重新評估觸發**：兩入口出現語意分歧 / 訊號層需引入長時程狀態（如 trailing stop trail point）

---

## 5. 執行計畫

1. ✅ M1：`compute_scores` pure function + 8 unit tests
2. ✅ M1：`compute_signals` + `evaluate_bar` + 12 unit tests
3. ✅ M1：`_evaluate_priority` 共用核心
4. M2：rqalpha 包裝呼叫 `evaluate_bar`
5. M3：vectorbt 包裝呼叫 `compute_signals`
6. M3：對齊測試 — 同一 fixture，兩入口結果一致

---

| 日期 | 審核人 | 備註 |
| :--- | :--- | :--- |
| 2026-05-26 | Self | 初版 |
