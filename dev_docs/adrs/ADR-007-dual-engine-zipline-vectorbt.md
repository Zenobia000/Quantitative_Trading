# ADR-007: 雙引擎策略（Zipline event-driven + vectorbt vectorized）

> **狀態：** 已接受 | **日期：** 2026-05-31 | **決策者：** Self
> **Related：** ADR-001（rqalpha 角色已被 ADR-005 取代，vectorbt 副引擎角色延續）、ADR-013（主引擎已切到 zipline-reloaded）、[ADR-014](./ADR-014-zipline-reloaded-3-1-1-upgrade-reverses-adr-013-constraints.md)（vector 半邊 2026-06-01 恢復可用）
>
> **2026-06-01 更新**：Sprint 1 期間 vectorbt 因 pandas<2 不相容暫停（記錄於 ADR-013 § 4），zipline-reloaded 3.1.1 升級（ADR-014）後 vectorbt 1.0+ 同棧可裝，本 ADR 雙引擎方案完整回復。

---

## 1. 背景與問題

- **上下文**：ADR-005 已選定 Zipline (TQuant-Lab) 為主骨架；M3 需執行 grid search（24-cell × 19-CCD）與 Walk-Forward Analysis（30 windows），單一引擎難兼顧速度與精度。
- **問題**：
  - Zipline event-driven 跑 1000 trials × 100 檔需數小時，最佳化迭代節奏崩潰
  - 純 vectorized 引擎無法表達 7 訊號優先序與 T+1 限制（在 vectorized API 中難以表達順序依賴）
  - 業界（López de Prado、QuantStart）已有成熟做法稱 "Dual-Engine Validation"
- **驅動因素 / 約束**：
  - 研究最佳化階段需向量化速度（grid 1000 trials × 100 檔 < 2 小時）
  - 實盤前驗證需事件驅動精度（撮合、滑點、T+1）
  - 訊號邏輯必須單一真相（M1 純函式已抽離，見 ADR-003）
  - 兩引擎結果差異必須可量化、可控制

---

## 2. 考量的選項

### 選項一：純 Zipline（單一引擎）
- **描述**：所有回測（IS / WFA / grid）都用 Zipline event-driven
- **優點**：單一引擎、無對拍負擔、結果精確一致
- **缺點**：
  - grid 1000 trials × 100 檔需 8+ 小時
  - WFA 30 windows × 5 參數組需數天
  - 最佳化迭代節奏無法支撐 M3 4 週工期
- **成本/複雜度**：低（但效能不可接受）

### 選項二：純 vectorbt（單一引擎）
- **描述**：放棄 Zipline event-driven，全部走 vectorized
- **優點**：速度極快、grid 原生支援
- **缺點**：
  - 7 訊號優先序在 vectorized API 內幾乎無法表達
  - T+1、漲跌停、整股單位需自寫 portfolio 邏輯
  - 與 Shioaji broker 整合無現成路徑
  - 推翻 ADR-005 全部設計
- **成本/複雜度**：高

### 選項三：雙引擎（Zipline 主 + vectorbt 副）★採納
- **描述**：Zipline 主用 backtest/paper/live 三模式（精度與實盤路徑），vectorbt 副用 grid/WFA/Monte Carlo（速度）；訊號邏輯抽成純函式雙方共用；定期對拍差異 < 0.5%
- **優點**：
  - 各取所長，與業界 "Dual-Engine Validation" 模式對齊
  - 訊號邏輯單一真相（M1 純函式，見 ADR-003）
  - WFA 30 windows 從 ~5 小時降至 ~30 分鐘
  - vectorbt 對拍結果驗證 vectorized 撮合假設成立 → 之後最佳化結果可信
- **缺點**：
  - 維護兩個 wrapper
  - 對拍測試開發成本
- **成本/複雜度**：中

### 選項四：Zipline + 自寫 vectorized 加速層
- **描述**：保留 Zipline，但自寫一層 numpy/pandas vectorized engine 跑 grid
- **優點**：完全可控、無第三方依賴
- **缺點**：reinvent vectorbt、開發成本爆炸
- **成本/複雜度**：極高

---

## 3. 決策

**選擇：選項三（雙引擎 Zipline + vectorbt）**

**理由**：
- ADR-005 已定 Zipline 主骨架，vectorbt 純粹補速度短板，不衝突
- M1 純函式策略層（ADR-003）已天然支援雙引擎共用，無額外重構
- 業界 "Dual-Engine Validation" 模式：vectorized 跑大量 trial 篩選 → event-driven 對 top-N 做精確驗證 → 兩者差異 < 0.5% 即驗證 vectorized 撮合假設成立
- 對拍機制本身就是策略品質的內建檢核（差異過大 = 訊號邏輯有隱藏 path dependency）
- 詳見 plan `C:\Users\xdxd2\.claude\plans\maintain-calm-blossom.md` § 2 副引擎段

---

## 4. 後果

- **正面**：
  - M3 grid search 與 WFA 速度提升 10 倍以上
  - 對拍差異成為策略品質量化指標（內建 sanity check）
  - 與業界標準做法對齊
- **負面**：
  - 兩個 wrapper 都要維護（`engines/zipline_runner.py` + `engines/vectorbt_adapter.py`）
  - 對拍測試需要持續更新（每次訊號邏輯改動）
  - vectorbt 開源版功能受限（Walk-Forward 需自寫，不買 PRO）
- **影響範圍**：
  - `engines/vectorbt_adapter.py`（新增 ~150 LOC，副引擎 for grid/WFA）
  - `strategies/four_layer_resonance/__init__.py`（同時被 Zipline algorithm 與 vectorbt adapter import）
  - `tests/regression/test_dual_engine_alignment.py`（新增對拍測試）
  - `validation/wfa.py`（自寫 Walk-forward splitter，~100 LOC）
- **重新評估觸發**：
  - 對拍差異 > 0.5% 持續無法收斂 → 砍 vectorbt 只用 Zipline，接受慢
  - vectorbt 上游 API 重大破壞性變更（如停止開源版維護）→ 評估自寫 vectorized 層或改用 nautilus
  - Zipline event-driven 經 profiling 優化後 grid 速度可接受 → 退回單引擎簡化維護

---

## 5. 執行計畫

1. **M2 W1-W4**：Zipline 主引擎端到端跑通（backtest mode），不涉及 vectorbt
2. **M3 W1**：撰寫 `engines/vectorbt_adapter.py`，import 同一份 `strategies/four_layer_resonance` 純函式
3. **M3 W2**：對拍測試（同參數 → 同期間 → 兩引擎差異 < 0.5%）
4. **M3 W3**：vectorbt 跑 24-cell × 19-CCD grid（< 2 小時門檻）
5. **M3 W4**：vectorbt 跑 WFA 30 windows，top-N 結果交給 Zipline 做精確對拍
6. **持續**：每次 `strategies/` 純函式變更，CI 觸發對拍測試確保差異 < 0.5%
7. **ADR-001 對齊**：原 ADR-001「rqalpha 主」廢止（由 ADR-005 取代），「vectorbt 副」延續至本 ADR

---

| 日期 | 審核人 | 備註 |
| :--- | :--- | :--- |
| 2026-05-31 | Self | 初版；延續 ADR-001 vectorbt 副引擎角色 |
