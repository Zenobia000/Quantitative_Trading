# ADR-019: v3 進場重設 — 參數化分級放寬（必含層+可選）+ 最小 exit 搭配

> **狀態：** 已接受 | **日期：** 2026-06-02 | **決策者：** Self（授權「站在操盤手角度代為決策」，經四交易視角壓測收斂）
> **相關：**
> - [ADR-017](./ADR-017-m2-is-gate-failed-return-to-m0-entry-redesign.md)（M2 IS gate FAIL → 回 M0 重設進場）— 本 ADR 是其 M0 進場重設的具體 hypothesis 定稿。
> - [ADR-016](./ADR-016-m2-acceptance-kpi-freeze.md)（K1/K2/K3 凍結）— IS gate 硬門檻來源。
> - [ADR-018](./ADR-018-monitoring-to-research-loop-pivot.md)（研究迴圈優先 / 版本切版）— 本工作為 v0.1 essential MVP 的策略側。
> - 設計 spec：`docs/superpowers/specs/2026-06-02-m0-v3-entry-redesign-design.md`；實作計畫：`docs/superpowers/plans/2026-06-02-m0-v3-entry-redesign.md`。

---

## 1. 背景與問題

ADR-017 證實四層共振**進場過嚴**（2330 5 年 14 次進場、在市場 3.9%、勝率 50%、平均持有 3.4 bar），雙 IS 窗口無 edge；放寬出場單獨無效（根因在進場）。M0 需重設進場 hypothesis。經 code 實證校正，進場稀的**真正收斂主力**是 `buy_sig` 的三道 transition gate：`structure_score==2`（箱型完美突破）+ `prev_total<5`（單日首次站上）+ 五重 AND，而非空泛的「四層全 AND」。

## 2. 決策

**保留四層共振 hypothesis，採參數化分級放寬進場 + 最小 exit 搭配。** 經四交易視角（波段動能 / 籌碼法人 / 風控部位 / 過擬合懷疑論者）壓測，定稿如下：

### 2.1 layer_policy = 必含層 + 可選層（非純 N-of-4、非加權）

放行充要條件：
```
momentum_score >= 1 AND structure_score >= 1 AND (direction_score >= 1 OR chip_score >= 1)
AND total_score >= 5 AND edge_ok AND NOT (direction_score==-1 OR chip_score==-1)
```
`entry_min_layers` 作為冗餘 N-of-4 計數上限門。

**關鍵實證（駁回純計數）：** L2⊂L3 — `chip_total`（L3）公式含 `foreign_buy + trust_buy`（L2 兩輸入），2330 Pearson=0.615；dir/chip 非兩張獨立票，故當「機構共識至少一邊背書」。在大型股 3-of-4 唯一會放掉 structure（dir/chip 罕單獨失效），但中小型 universe 必含 dir/chip 才擋得住「技術突破但法人籌碼不認帳」的假突破（丟 chip 反事實單 fwd5 −6.9%）—— 故 v0.1 IS 必納中小型股。

### 2.2 六個參數（v2 預設重現 baseline / v3 先驗值）

| 參數 | v2 | v3 | 性質 |
|:--|:--|:--|:--|
| `entry_min_layers` | 4 | 3 | sweep(v0.2) |
| `entry_min_structure` | 2 | 1 | sweep(v0.2) |
| `entry_first_cross_only` | True | False | sweep(v0.2) |
| `entry_confirm_days` | 1 | 2 | sweep(v0.3) |
| `entry_cooldown_bars` | 0 | 3 | 固定守門 |
| `exit_flameout_confirm_bars` | 1 | 2 | 固定守門 |

### 2.3 exit 最小搭配（與進場同 commit、為必要項）

flameout 的 momentum 觸發 1→2 bar 確認；box_lower/risk_swing_low 硬停損不動、優先於 buy。**為何不違反 ADR-017「出場校準單獨無效」：** ADR-017 否決的是「v2 過嚴進場不變下單獨調 flameout」（樣本僅 14 不足）；本次是「進場放寬 + 出場最小鬆綁」成對。464 flameout 天 ≫ 188 strong_buy 天、3.4 bar 持有 → 只放寬進場不動 hair-trigger flameout 會製造「>40 筆但仍 3 bar 被洗」的假成功。v0.1 同批跑 `flameout=1` 對照組證明改善來自搭配。

### 2.4 反過擬合硬約束

- v0.1 **只跑一組先驗預設、不在雙窗口 IS sweep**（雙窗皆 in-sample，4 維 grid search 是 ADR-017 §3 選項二換皮）。
- **進場數 >40 嚴禁當成功指標**，只當樣本健全下限（30–80 筆/股/5 年）。
- 誠實 exit gate：跨雙窗符號一致 + 邊際單品質不劣化 + 操盤手體檢（平均持有≥6、中段進場<30%、churn<20%）。綠燈≠有 edge，只代表「值得進 v0.2 OOS」。
- 凍結清單：`strong_buy_threshold=5`、`min_edge_rate=0.006`、`box_period=60`、`chip_strong_threshold=0.10` 等 v0.1 全程不動。

### 2.5 成本基準校正（doc/code drift）

實測 code（`strategy_config.py`，無 0.2% buffer）：`cost_round_rate=0.671%`、`edge_ok 門檻=1.271%`。v2.md §2.5.1 文字（1.07% / 1.3%）含 0.2%×2 buffer，**code 未實作**。**決定：v0.1 以 code 為真相源，v2.md 加 v3 註記標明落差；0.2% buffer（及中小型 slip 上調）留 v0.2 換 universe 時處理。**

## 3. 後果

- 進場 gate 參數化、可關閉、可對照；v2 預設精確重現 baseline（regression test 釘死）。
- scoring.py 四層分數不動；改動集中於 config + signals（`_evaluate_priority`/`compute_signals`/`EvaluateBar`）。
- v0.1 範圍：設計+實作+雙窗口 IS（人工讀，Sprint 6）。**不碰**前端 / M3 統計重功能 / 換 universe（候選 D 僅退場後備）。
- 誠實退場：雙窗符號不一致 / 邊際單劣化 / 中小型也無一致正期望 → 問題在 hypothesis 不在進場閘，回 M0 換 edge 來源，不續鬆閘自欺（放寬解進場稀、解不了標的無 alpha）。

## 4. 執行狀態

1. ✅ 設計 spec + 實作計畫（設計 skill Phase 1/2）
2. ✅ code 實作（config 6 參數 + signals v3 gate + exit 搭配；16 synthetic 測試、signals.py 100%、suite 271 pass）
3. ⏳ doc-sync（本 ADR + v2.md §2.4 v3 並存 + 成本註記 + 21/24/16 WBS）
4. ⏳ Sprint 6 雙窗口 IS 人工讀（cache-gated；2330 + 中小型成分股）→ gate review

---

| 日期 | 審核人 | 備註 |
| :--- | :--- | :--- |
| 2026-06-02 | Self | 初版 — v3 進場參數化放寬（必含層+可選）+ flameout 最小搭配；四視角壓測收斂；反過擬合硬約束 |
