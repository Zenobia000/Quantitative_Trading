# inst_flow 真偽閘重驗結果（修正後審判庭，ADR-030）

> **日期**：2026-07-02 | **觸發**：ADR-030（PR #137）修正審判庭四缺陷後，既往判決作廢須重驗
> **執行路徑**：`python -m backtest_platform.research.cli truth-gate --strategy inst_flow`（ADR-029 標準化工作流，非已刪 scripts）
> **程式狀態**：main @ PR #145 合入後（含 ADR-030 修正閘 + ADR-028/029 dispatch + WP6 依賴解纏）

---

## 判決

```
verdict=REJECTED  DSR=0.7887  slip_sharpe=3.605  WFA OOS+=33.33%
✗ survivorship not clean (survivor-only universe inflates edge)
✗ WFA OOS>0 frac 0.333 < 0.6 (out-of-sample breadth too thin)
✗ DSR 0.789 < 0.95 (deflated significance)
```

## 解讀（為什麼與 2026-06-15 的 REAL 不同）

1. **Universe 不同**：現行 `strategies/inst_flow/research_config.py` 的 `_WIDE` 是 **40 檔存活股**——正是 [ADR-024](./adrs/ADR-024-institutional-flow-candidate-strategy.md) 判定「生存者膨脹假陽性」的那個 universe。2026-06-15 的 TRUTH GATE REAL（[inst_flow_truth_gate_finlab_result_2026-06-15.md](./inst_flow_truth_gate_finlab_result_2026-06-15.md)）用的是 FinLab survivorship-clean 全史 universe（78↔423 檔含下市股），其建構邏輯隨 `scripts/` 刪除，[ADR-029](./adrs/ADR-029-research-workflow-standardization.md) 明文延後至 sub-project ②。
2. **審判庭數學不同**：舊 DSR 因單位錯配恆等於 1.0（[ADR-030](./adrs/ADR-030-truth-gate-judgement-fix.md)）；修正後對同輸入給出誠實的 0.789。survivorship_clean 不再寫死 True，未宣告即 hard-fail——本次三條 fail 中的第一條正是修正閘拒絕「對存活股 universe 宣稱乾淨」的正確行為。

## 結論與後續

- **本判決不翻案 2026-06-15 的 FinLab 重驗結論**（該輪用的 universe 與方法不同），但確認了審查報告的核心指控：**「TRUTH GATE REAL」在現行程式路徑無法重現，證據鏈斷裂**。
- inst_flow 的 paper-ready 地位**暫停**，直到：
  1. sub-project ② 把 FinLab survivorship-clean universe 建構器重建為平台工作流（從 git 歷史 `inst_flow_revalidate_finlab` 恢復邏輯）；
  2. 用該 universe + 修正後審判庭重跑 truth-gate，取得可重現的判決。
- 在此之前，`research_config.py` 的 `_WIDE` 註解已修正為如實描述（survivor-only，truth gate 會正確拒絕）。
