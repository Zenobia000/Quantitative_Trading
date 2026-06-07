# ADR-024: 三大法人資金流因子 — 候選策略（條件式 GO，待 survivorship-clean + paper）

> **狀態：** 提案中（條件式 GO）| **日期：** 2026-06-07 | **決策者：** Self
> **Related：** [ADR-016](./ADR-016-m2-acceptance-criteria.md)（部署門檻 CAGR>18%/Sharpe>1.0/DSR>0.95/PBO<30%）、[ADR-023](./ADR-023-momentum-no-go-hold-gate.md)（動能 NO-GO，釋放 capacity 換 family）

---

## 1. 背景與問題

R9 收斂：四層共振＝負 edge、動能＝真實但太弱（OOS 0.63–0.86，ADR-023 NO-GO）。
艦隊轉掃描下一候選。**換 edge family**（非動能）：三大法人資金流因子 —— 台股散戶為主、
外資/投信買賣超有領先性，且免費 FinMind 資料可得。用已證可信的統一驗證 pipeline
（`validation/full_report.py`）從零驗。

## 2. 因子定義

- 訊號：trailing 三大法人 net-buy **強度** = Σ(net-buy)/Σ(volume)（跨股可比），橫斷面
  rank、做多前 1/3、再平衡。`signal_lag_days=1` 杜絕同日 look-ahead。
- 實作：`strategies/inst_flow/strategy.py`；機制（rebalance/cost/vol-target）沿用動能模組。
- 最佳 config：quarterly / lookback=60 / foreign net-buy / vol_target=off。

## 3. 證據（全走 ADR-016 門檻，誠實條件）

| 關卡 | 結果 | 門檻 | 判 |
| :--- | :--- | :--- | :--: |
| IS 2016-2020（10 大型股）| Sharpe 1.30 / CAGR 28.5% | — | — |
| OOS 2021-2024（固定 config 不重選）| Sharpe 1.04 / CAGR 21.3% | >1.0 / >18% | ✅ |
| **WFA**（40 檔、12 rolling folds）| median OOS Sharpe **1.41**、OOS>0 92%、OOS>1.0 67% | median>1.0 + >0≥60% | ✅ |
| **PBO**（24-config CSCV）| **11.4%** | <30% | ✅ |
| 全期固定 config（40 檔）| CAGR 18.9% / Sharpe 1.11 | >18% / >1.0 | ✅ |

- **去 look-ahead**：加 1-day signal lag 後 Sharpe 1.35→1.30 → 訊號真實非同期衝擊。
- 同 universe/plumbing 對比：動能 IS 0.92 vs 資金流 1.30；動能死在 OOS、資金流撐過。
- **平台首個 IS+OOS+WFA+PBO 全過的 edge candidate。**

## 4. 決策

**條件式採納為候選策略**，進入部署前最後驗證。**尚未全倉 GO** —— 仍有兩道未繳的稅：

1. **survivorship-clean 複驗（必過）**：目前 40 檔皆現存大型股（大型股偏誤小於中小型，
   但仍需含下市股重跑 WFA/PBO 確認非生存者膨脹）。
2. **paper trading 觀察（真錢前置）**：通過 survivorship-clean 後，走 paper 累積實際
   執行摩擦（外資跟單的容量/衝擊/時序），再談小倉位實盤（ADR-016 + 7.B sign-off）。

並注意：CAGR 18.9% 僅略過 18% buffer 門檻、MaxDD ~31% 偏高 → 部署需風控設計
（vol-target 砍 DD 但壓 Sharpe，需取捨）。

## 5. 後果

- **正面**：平台「先建工具、再換對 edge 就驗得出」獲鐵證；首個真實可部署候選；驗證
  pipeline（full_report + WFA + PBO + DSR）端到端證實能誠實分辨 GO/NO-GO（momentum NO-GO、
  inst_flow 條件式 GO）。
- **負面 / 風險**：單因子單市場集中；CAGR 邊際；survivorship 未繳清前不可宣稱 GO。
- **重新評估觸發**：survivorship-clean WFA/PBO 任一不過 → 退回 NO-GO；paper 期實際摩擦
  吃掉 edge → 重評。

## 6. 執行計畫

1. ✅ 因子實作 + IS/OOS（PR #86）
2. ✅ GO 關卡：WFA + PBO + 寬 universe（本 ADR，PR #87）
3. ⏳ survivorship-clean 複驗（含下市股，重跑 WFA/PBO）
4. ⏳ 通過後：寫全倉 GO ADR + 進 paper（7.A）→ 小倉位實盤（7.B，ADR-016 sign-off）

---

| 日期 | 審核人 | 備註 |
| :--- | :--- | :--- |
| 2026-06-07 | Self | 初版 — 條件式 GO；IS/OOS/WFA/PBO 全過，待 survivorship-clean + paper |
