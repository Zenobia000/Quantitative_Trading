# ADR-023: 策略評估結論 — 四層廢止、動能 NO-GO（守 ADR-016 門檻）、艦隊持續掃描

> **狀態：** 已接受 | **日期：** 2026-06-05 | **決策者：** Self（使用者裁定）
> **相關：**
> - [ADR-016](./ADR-016-m2-acceptance-kpi-freeze.md)（M2 acceptance gate：CAGR>18% / Sharpe>1.0 / 滑點 Sharpe>1.0，凍結）— 本 ADR **守此門檻不放寬**。
> - [ADR-017](./ADR-017-m2-is-gate-failed-return-to-m0-entry-redesign.md) / [ADR-019](./ADR-019-v3-entry-redesign-relaxation-and-minimal-exit-pairing.md)（四層 v3 進場 IS gate FAIL）。
> - [ADR-020](./ADR-020-candidate-d-smallcap-universe-escalation.md)（候選 D 中小型 universe escalation）。
> - [ADR-022](./ADR-022-multi-strategy-fleet-operations.md)（多策略艦隊營運）— 本 ADR 是艦隊「掃描→評估→裁汰」的第一輪結論。
> - 證據：`dev_docs/factor_baseline_diagnostic_result_2026-06-04.md`、`momentum_strategy_result_2026-06-04.md`、`momentum_large_universe_result_2026-06-04.md`、`momentum_survivorship_clean_result_2026-06-04.md`、`momentum_go_nogo_result_2026-06-05.md`。

---

## 1. 背景

平台優先策略下，四層共振 + 動能依序被當候選跑完整防過擬合驗證（對照診斷 → 對抗式 → PBO/DSR/WFA → 大 universe → survivorship-clean → 固定 config + 實際成本的 final go/no-go）。需一則 ADR 正式裁定兩者去留與門檻立場。

## 2. 決策

1. **四層共振 — 廢止（killed）**。對照診斷證實為**負 edge、毀價值**（同股票 buy-hold +12~22%，四層做成 −2~−3%，落後 ~20pp）。非「edge 不夠」是「主動毀價值」。不再投入任何資源（進場/universe/籌碼）。

2. **動能 12-1 — NO-GO under ADR-016**。最佳形態（季頻 rebalance）在誠實條件（固定 config + 1.2% 實際成本 + 209 檔 survivorship-clean）下：**CAGR 7.1%（<18%）、WFA OOS Sharpe 0.86（<1.0）、PBO 9.7%（極穩健）**。判定：**真實、robust 但太溫和**——台股中小型動能毛溢酬 ~10-12% 被交易成本吃到淨 ~7%，配不上 ADR-016 門檻。

3. **守 ADR-016 原門檻，不為分散因子放寬**（使用者 2026-06-05 裁定）。雖然以「分散因子標準」（Sharpe>0.8 + PBO<10%）季頻動能可算可投資，但**維持單一嚴格 gate 的紀律一致性**，不 move the goalposts 救單一策略。18%/1.0 仍是進 paper/live 的審慎下限。

4. **平台轉持續掃描下一候選**。下一輪掃描方向（未定，待後續 ADR）：大型股動能（spread 低、成本牆較矮）/ 多因子組合 / 非動能 edge 來源。

## 3. 為什麼這樣裁

- **紀律 > 救策略**：放寬門檻收下 7% CAGR 的策略，等於每遇瓶頸就降標準，最終 gate 失去意義。
- **平台價值已被反向驗證**：它量出「過擬合/偏誤稅」（WFA OOS **1.28 → 1.07 → 0.63**，每剝一層 degree of freedom 就掉），擋下一個「看似 1.28、實際 0.63」的策略——天真回測器會部署它然後在真錢上虧。這正是「平台優先」的鐵證。
- **誠實現實**：台股中小型、扣實際成本+反倖存，要過 18%/1.0 很難（市場效率 + 成本牆）。這是事實，不是工具問題。

## 4. 後果

- **動能模組保留**（`strategies/momentum/`，可重用、季頻/cost_mode/vol-target config 已記錄）——換 universe/factor 可一行重驗。
- **無策略進 paper**；前端（v0.4）/實盤（v1.0）仍 gated 於通過 ADR-016 的策略。
- 四層 `strategies/four_layer_resonance/` 標記廢止（程式保留作對照基準/歷史）。
- 下一候選掃描另起，沿用同一條 `momentum_validate.py` / `*_go_nogo.py` 紀律。
