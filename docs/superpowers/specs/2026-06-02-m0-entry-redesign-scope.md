# M0 Re-scope — 進場假設重設（v2 → v3）

> **狀態：** 證據彙整 / 待下一個 design cycle 細化
> **日期：** 2026-06-02
> **觸發：** [[ADR-017]] M2 IS gate FAIL → 回 M0 重設進場
> **相關：** `strategy/v2.md` §2.4、[16 WBS §5 R9](../../../dev_docs/16_wbs_development_plan.md)、ADR-016（gate KPI）

本文是 v3 進場重設的**證據包 + 開放問題**，供下一個 `sunnydata-design` Phase 1 使用。**不在此修改 v2.md。**

---

## 1. 結論（一句話）

四層共振策略**進場過嚴**（5 年僅 ~10-14 次進場、勝率 50%、在市場 ~4%），於 2015-2020 與 2020-2024 兩個 IS 窗口皆無 edge；放寬出場無法救（最佳 ~0.4% CAGR）。**問題在進場 hypothesis，非出場校準、非實作 bug。**

## 2. 原始證據

### 2.1 Portfolio IS（equal-weight 10 檔，含完整台股成本）

| 窗口 | baseline | box_only（去 momentum 觸發）| mom2（2 日確認）|
|:--|:--:|:--:|:--:|
| 2020-2024 | −1.75% | **+2.20%** | +0.69% |
| 2015-2020 | −4.94% | −0.70% | −2.57% |

M2 gate（ADR-016）：K1 CAGR>18% / K2 Sharpe>1.0 / K3 滑點 Sharpe>1.0 → 全 FAIL。

### 2.2 單股 2330 行為（2020-2024）

| 指標 | 值 |
|:--|:--|
| 進場次數 | 14（5 年）|
| 在市場 bars | 47 / 1216（3.9%）|
| 平均持有 | 3.4 bars（max 9）|
| 勝率 | 50% |

### 2.3 score / state 分布（2330 2020-2024）

- `total_score >= 5`：333/1216 天（27%）— 分數門檻其實常達標
- `state_strong_buy`：188 天 — 但進場僅 14 次（差距來自 `structure_score==2` + 首次站上 + edge_ok 三重 transition gate）
- `state_flameout`：464 天 ≫ strong_buy 188 天 — 出場狀態遠多於進場狀態 → 抱不住

## 3. 為何進場這麼稀？（v2.md §2.4.2 `signal_buy`）

```
buy = 空手 AND state_strong_buy（4 層全 >=1 AND total>=5）
          AND structure_score==2          ← 必須箱型完美突破
          AND prev_total < 5               ← 必須「首次」站上（單日 transition）
          AND edge_ok（波動 >= 成本+min_edge）
```

四個 AND 疊加，每個都收斂機率 → 5 年 ~14 次。**這是設計的，不是 bug**（code 100% 對齊 v2.md）。

## 4. v3 進場重設候選方向（待設計）

| 方向 | 假設 | 風險 |
|:--|:--|:--|
| **A. 全 AND → N-of-4 / 加權** | 放寬「4 層全正」為「至少 3 層 + 總分門檻」，提高參與度 | 可能引入雜訊、增加假訊號 |
| **B. 移除 `structure_score==2` 硬門檻** | 接受非完美突破進場 | 同上 |
| **C. 進場改「持續站上 K 日」非「單日首次」** | 降低 transition 偏誤、抓延續而非瞬間 | 進場延遲、錯過急漲 |
| **D. 換 universe** | large-cap 效率高，改中小型動能股（v2.md line 134 自承 edge 未定義）| 流動性 / 生存者偏誤加劇 |
| **E. 重訂 flameout** | 不以單日 momentum==-1 出場（搭配進場放寬）| 單獨做無效（探針已證）|

**建議優先序**：A/B（進場放寬）為主因靶心；D（universe）為平行假設；E 為配套。

## 5. 開放問題（下一 cycle Phase 1 要回答）

1. v3 進場要走「放寬現有 4 層」還是「重新定義 edge 來源」？
2. universe 是否換？若換，如何處理生存者偏誤（R7）？
3. 重設後仍用 ADR-016 同一 gate，或門檻需隨 universe 調整？
4. v2.md 是整段重寫 §2.4 還是開 v3 並存對照？

## 6. 不做什麼（YAGNI / 紀律）

- 不在無 edge baseline 上跑 M3 DOE/WFA/PBO（ADR-017 §3 選項二已否決）
- 不靠出場校準硬推（探針已證無效）
- 不在本文修改 v2.md / 實作 code（屬下一 cycle）
