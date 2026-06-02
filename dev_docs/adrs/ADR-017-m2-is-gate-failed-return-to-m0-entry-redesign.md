# ADR-017: M2 IS acceptance 未達標 → 觸發退場條件，回 M0 重設「進場」假設

> **狀態：** 已接受 | **日期：** 2026-06-02 | **決策者：** Self
> **相關：** [ADR-016](./ADR-016-m2-acceptance-kpi-freeze.md)（凍結 M2 acceptance KPI，本 ADR 記錄該 gate 的執行結果）、[ADR-013](./ADR-013-mainframe-zipline-reloaded-supersedes-tquant-lab.md)（M2 引擎）、[16 WBS §5 R9 / §6 里程碑](../16_wbs_development_plan.md)、`strategy/v2.md` §2.4（進出場規則，待 v3 重訂）

---

## 1. 背景與問題

- **上下文**：Sprint 3 完成 universe ingest（5.A.7，ADR-017 前置）後執行 portfolio 10 檔 IS 回測（5.A.6），對照 ADR-016 凍結的 M2 acceptance（K1 CAGR>18% / K2 Sharpe>1.0 / K3 滑點 0.3% 下 Sharpe>1.0）。
- **問題**：IS 回測結果遠低於門檻，且診斷顯示策略「進場極稀 + 出場抽筋」結構性無 edge。需依 ADR-016 §退場條件作出 gate 決策。
- **觸發事件**：2026-06-02 跑 `backtest-run` 10 檔 portfolio，並做參數敏感探針（放寬 flameout 出場）+ 雙窗口驗證。

## 2. 證據（IS 回測 + 探針）

### 2.1 Portfolio IS 結果（equal-weight 10 檔）

| 窗口 | baseline（v2.md as-is） | 放寬出場最佳變體 | 對 K1 (CAGR>18%) |
|:--|:--:|:--:|:--:|
| 2020-2024 | **−1.75%** | +2.20%（box_only）≈ 0.4% CAGR | ❌ FAIL |
| **2015-2020（ADR-016 凍結窗口）** | **−4.94%** | −0.70%（box_only） | ❌ FAIL（負 CAGR）|

兩個窗口、三種出場變體全數 FAIL，差 M2 門檻約兩個量級。

### 2.2 根因診斷（單股 2330，2020-2024）

- 5 年僅 **14 次進場**，在市場時間 **47/1216 bars（3.9%）**，平均持有 3.4 bars，**勝率 50%**（coin-flip）。
- 結構性**不對稱**（忠實實作 v2.md §2.4.1-2.4.2，無 code 漂移）：
  - **進場**：4 層全 `>=1` AND `total>=5` AND `structure_score==2` AND 首次站上 AND 成本濾網 → 極稀
  - **出場（flameout）**：`momentum_score==-1` OR `close<box_lower` → 單一動能層回落即出 → 永遠抱不住趨勢
- 參數探針結論：放寬出場（box_only / 2-day confirm）僅把 portfolio 從 −1.75% 拉到 +2.2%，**真正約束在「進場太嚴」而非出場**。校準層級無法救。

### 2.3 附帶發現（已修）

`engines/zipline_adapter/cli.py:_format_perf_summary` 的 `action_totals` 來自 zipline `record()` 欄位加總，但 `record()` 對未出現的 action 欄**前向填充**，導致「單筆 buy 被讀成 ~1000 筆」。已改為從 `transactions` 計算真實成交筆數（本 PR 同步修復 + regression test）。

## 3. 考量的選項

### 選項一：校準出場參數，續推 M2 ★已用探針否決
- 放寬 flameout → 最佳僅 ~0.4% CAGR（2020-24）/ 負（2015-20）。約束在進場，非出場。**拒絕**。

### 選項二：接受 IS 結果，照原計畫進 M3 統計驗證
- 把 −1% 當資料點進 DOE/WFA/PBO。**拒絕**：ADR-016 退場條件為先驗，IS 未達綠燈即應回 M0，不應用更多統計工序粉飾無 edge 的 baseline。

### 選項三：觸發 early-stopping gate，回 M0 重設「進場」假設 ★採納
- 依 ADR-016 §退場條件 + 16 WBS §6。探針已定位問題在**進場過嚴**（4 層全 AND + structure==2 + 首次站上）。回 M0 重訂進場 hypothesis。

## 4. 決策

**選擇：選項三 — 觸發 M2 退場條件，回 M0 重設進場假設。**

- M2 milestone 標記為 **未通過（IS gate FAIL）**，暫停 Sprint 4 M2 acceptance 與後續 M3 統計工序。
- M0 重設**聚焦進場**（出場校準已證實非主因）。候選方向（待下一個 design cycle 細化，見 `docs/superpowers/specs/`）：
  1. 放寬 4 層「全 AND」為「加權 / N-of-4」進場（提高參與度）
  2. 重新定義 edge 與 universe（v2.md line 134 自承「沒明確說邊際在哪」；large-cap 可能非目標，考慮中小型動能股）
  3. 重訂 flameout 不以單日 momentum==-1 觸發（與進場放寬搭配）
- 不在本 ADR 修改 `strategy/v2.md`；v2→v3 進場重設屬獨立 M0 設計活動。

## 5. 後果

### 正面
- 先驗退場條件被遵守，避免在無 edge baseline 上浪費 M3 統計工序。
- 根因被精確定位（進場稀疏，非出場 / 非 harness bug / 非 code 漂移），M0 重設有明確靶心。
- 修掉誤導性 metric（action_totals ffill），未來回測數字可信。

### 負面
- M2 / M3 時程順延；Sprint 4 重定義為 M0 進場重設。
- v2.md 進場邏輯需重寫 → 既有 scoring/signals 測試部分需隨 v3 調整。

### 影響範圍
- `dev_docs/16_wbs_development_plan.md`：§6 M2 milestone 標未通過、§5 R9（策略無 edge）由「高/致命」轉「已部分實現於 IS」、§7 Sprint 4 重定義、技術債（metric bug 已修）。
- `strategy/v2.md`：§6.3 changelog 待記 v3 進場重設（下一 cycle）。
- `dev_docs/INDEX.md` + `02_project_brief_and_prd.md` §決策沿革（D-015）。
- `docs/superpowers/specs/`：下一 cycle 產出 M0 進場重設 spec。

### 重新評估觸發
- M0 進場重設後，重跑同一 ADR-016 gate（2015-2020 + 2020-2024 雙窗口）。
- 若 v3 進場仍無 edge → 評估 hypothesis 是否根本不成立（可能砍策略，R9 致命路徑）。

## 6. 執行計畫

1. ✅ 本 ADR 記錄 gate 結果 + 決策
2. ✅ 修 `_format_perf_summary` metric ffill bug + regression test
3. ✅ 16 WBS 同步（M2 milestone / R9 / Sprint 4 重定義 / 技術債）
4. ✅ M0 re-scope 文件（`docs/superpowers/specs/2026-06-02-m0-entry-redesign-scope.md`）記錄證據 + 進場重設候選方向
5. ⏳ 下一 cycle：v3 進場 hypothesis 設計（sunnydata-design Phase 1）

---

| 日期 | 審核人 | 備註 |
| :--- | :--- | :--- |
| 2026-06-02 | Self | 初版 — IS gate FAIL（雙窗口）、探針定位進場為約束、回 M0 重設進場 |
