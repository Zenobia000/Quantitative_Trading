# ADR-016: M2 acceptance KPI 凍結（CAGR / Sharpe / 滑點穩健性）

> **狀態：** 已接受 | **日期：** 2026-06-01 | **決策者：** Self
> **彙整來源：** [`01_workflow_manual.md` §6 transitions](../01_workflow_manual.md) + [`02_project_brief_and_prd.md` §成功指標](../02_project_brief_and_prd.md) + `strategy/v2.md` §4.3.1 綠/黃/紅燈表
> **相關：** [ADR-013](./ADR-013-mainframe-zipline-reloaded-supersedes-tquant-lab.md)（M2 主骨架）、[ADR-014](./ADR-014-zipline-reloaded-3-1-1-upgrade-reverses-adr-013-constraints.md)（pandas 2 / vectorbt 升級）、[16 WBS §6 M2 acceptance](../16_wbs_development_plan.md#m2-acceptance綠燈門檻凍結於-adr-016)

---

## 1. 背景與問題

- **上下文**：Sprint 0/1/2 完成、Sprint 3 將執行 portfolio 10-stock IS 回測，需先鎖定 M2 通過門檻
- **問題**：M2 acceptance 反覆出現「綠燈」字眼但無集中表達。01 §6、02 §成功指標、v2.md §4.3.1、16 WBS §6 各處引用不同子集合
- **觸發事件**：2026-06-01 WBS status audit 發現「M2 退場條件：若 IS 跑不到綠燈 → 回 M0」但「綠燈」具體數字未在單一位置凍結
- **驅動因素 / 約束**：
  - 退場條件須是**先驗**（pre-registered）才能避免事後合理化
  - 規劃文件已有多次引用相同數字，本 ADR 為彙整 + 凍結，不引入新數字
  - 凍結後若調整必須留時間戳於 `strategy/v2.md` §6.3 + 開新 ADR superseding

---

## 2. 考量的選項

### 選項一：不凍結（維持分散於各 doc）
- **描述**：保留現狀，需要時去 01/02/v2.md 個別查
- **優點**：零變更
- **缺點**：
  - 各檔數字若漂移無 single source of truth
  - Sprint 3-4 執行 M2 acceptance 時容易爭辯「是哪個版本的綠燈」
- **拒絕**：違反「狀態真相源」原則

### 選項二：彙整既有數字 + 寫入 ADR-016 ★採納
- **描述**：把 01 §6 / 02 §成功指標 / v2.md §4.3.1 既有數字搬到本 ADR、WBS §6 連結本 ADR
- **優點**：
  - 不引入新數字，純彙整
  - 凍結時間清楚（2026-06-01 Sprint 3 啟動前）
  - 後續任何調整都要新 ADR supersede（trace 清楚）
- **缺點**：多一份 ADR

### 選項三：重新評估更嚴格 / 寬鬆數字
- **描述**：藉機調整門檻（如 Sharpe 1.2 / CAGR 22%）
- **優點**：可能更貼近 R9（策略 edge）的嚴苛要求
- **缺點**：違反「先驗門檻」原則 — 應該先用既有數字測，看結果再決定下一輪
- **拒絕**：不在本次審查範圍

---

## 3. 決策

**選擇：選項二（彙整既有數字 + 凍結）**

### M2 IS acceptance 三項門檻

| # | 指標 | M2 IS 門檻 | 計算 | 來源 |
|:--:|:--|:--:|:--|:--|
| **K1** | **CAGR** | **> 18%** | `(1 + total_return)^(252/N) - 1`（含生存者偏誤 +3% buffer）| `01_workflow_manual.md` §6 transitions、`strategy/v2.md` §4.3.1 |
| **K2** | **Sharpe** | **> 1.0** | `(R - R_f) / σ × sqrt(252)`，R_f 取 0 | `02_project_brief_and_prd.md` §成功指標、`01_workflow_manual.md` §6、`18_reference_architecture_and_metrics.md` §metrics 表 |
| **K3** | **滑點 0.3% 下 Sharpe** | **> 1.0** | 同 K2，於 backtest 套用 0.3% per-leg 滑點 | `02_project_brief_and_prd.md` §成功指標（穩健性測試）|

### 評估範圍

- **Universe**：DEFAULT_UNIVERSE 10 檔（2330 / 2317 / 2454 / 1101 / 3008 / 2882 / 1303 / 2412 / 2308 / 2891）— Sprint 3 Day 1（5.A.7）完成 ingest 後評估
- **期間**：IS 2015-01-01 → 2020-12-31（5 年），對齊 `02 PRD` US-003
- **單位**：完整 portfolio（不是單股），含 commission + tax + slippage 完整 cost stack（Taiwan rules，見 `controls/taiwan_stock_rules.py`）

### 退場條件

任一項（K1 / K2 / K3）不達標 → 觸發 16 WBS §6「M2 退場條件」回 M0 重新檢視策略。

---

## 4. 後果

### 正面
- M2 acceptance 標準在 Sprint 3-4 執行前先驗凍結，避免事後合理化
- WBS §6 + 17 master plan + 02 PRD 都 cross-ref 本 ADR，single source of truth
- M3 OOS 門檻（OOS Sharpe > 0.6 × IS、PBO < 30%、DSR > 0.95）邏輯上需先有 IS baseline 才能算，本 ADR 為其前置依賴

### 負面
- 若 M2 IS 結果落在邊緣（如 Sharpe 0.95 / CAGR 17%）會觸發退場，可能浪費已投資時間。緩解：早期 Sprint 3 跑單股快速 sanity check（2330 既有 cache 可直接跑）
- 數字含 +3% 生存者偏誤 buffer 但本 platform 不模型化下市股（R7），實際 CAGR 可能高估 — 接受此偏誤

### 影響範圍
- `dev_docs/16_wbs_development_plan.md` §6（M2 acceptance KPI 子節已加入，連結本 ADR）
- `dev_docs/INDEX.md`（ADR list 新增 ADR-016）
- 後續 M2 backtest report（Sprint 4）以這三個 K 為通過判據
- M3 OOS spec（Sprint 5+）以 K2 IS Sharpe 作為 0.6× 基準

### 重新評估觸發
- M2 IS 結果顯示策略有 edge 但 Sharpe 落在 0.9-1.0 → 評估是否放寬至 0.9（需新 ADR）
- 換 universe（如改 50 檔）→ 門檻可能需調整（生存者偏誤影響不同）
- 策略修改（v2.md → v3）→ 需重新評估綠燈定義

---

## 5. 執行計畫

1. ✅ **本 ADR** retroactive 彙整既有數字
2. ✅ **16 WBS §6** 加 M2 acceptance KPI 子節（cross-ref 本 ADR）
3. ✅ **INDEX** 加 ADR-016 row
4. **Sprint 3 Day 1**（5.A.7）：ingest 9 檔解 R14
5. **Sprint 4 M2 acceptance**：跑 portfolio 10 檔 IS 5 年，輸出 quantstats 報表，三項 K 對照通過 / 退場

---

| 日期 | 審核人 | 備註 |
| :--- | :--- | :--- |
| 2026-06-01 | Self | 初版 — 彙整 01/02/v2.md/18 既有數字，凍結 M2 acceptance |
