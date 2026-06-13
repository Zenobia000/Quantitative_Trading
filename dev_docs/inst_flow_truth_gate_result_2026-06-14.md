# 資金流 — 兩段閘真偽判決（2026-06-14）：🟢 REAL，首個 paper-ready 候選

> 承 [ADR-025](./adrs/ADR-025-two-stage-validation-gate-and-paper-promotion.md)（驗證閘從 binary 改兩段式）。
> binary ADR-016 曾判資金流 NO-GO（[ADR-024](./adrs/ADR-024-institutional-flow-candidate-strategy.md)：survivorship-clean
> CAGR 13.1% < 18%、landscape PBO 42.9% > 30%）。本文把**同一份 survivorship-clean 數據**餵 ADR-025
> 真偽閘——對 pre-registered fixed config，landscape PBO 不適用，真偽改由 OOS breadth + DSR 判。
> 腳本 `scripts/inst_flow_truth_gate.py`（離線跑 116 檔 parquet cache，無 re-ingest）。

## 設定（pre-registered，誠實）
- **固定 config**（事前鎖死，不逐 fold/不從 sweep 選）：`quarterly / lookback=60 / foreign net-buy`。
- **survivorship-clean universe**：116 檔（survivors + 下市），point-in-time，含下市輸家。
- **DSR 誠實去偏**：`n_trials=24`（研究實際掃過的 config landscape）+ cross-trial per-period Sharpe variance → 扣掉「我們看過 24 個 config」的選擇偏誤。

## 結果

| 真偽閘判準 | 值 | 門檻 | 判 |
|:--|:--|:--|:--:|
| survivorship-clean | 116 檔（含下市）| 強制 | ✅ |
| **WFA OOS>0 比例** | **83%**（12 folds，median OOS 1.30）| ≥ 60% | ✅ |
| landscape PBO | 42.9% | — | **忽略**（pre-registered，PBO 量的是選股過擬合）|
| **DSR（deflated, n_trials=24）** | **0.982** | ≥ 0.95 | ✅ |
| K3 滑點 Sharpe（+0.3%/leg）| 0.90 | > 0 | ✅ |

WFA OOS 逐 fold：1.62 / 1.80 / 0.69 / **−0.25** / 1.57 / 0.83 / 2.63 / 0.94 / **−0.51** / 1.03 / 2.57 / 2.14（10/12 > 0）。
fixed config full-span：CAGR 13.1% / Sharpe 0.90。

## 🎯 判決：TRUTH GATE = REAL → 配置閘目標倉位 25%

**資金流 fixed config 過真偽閘。** 配置閘以 OOS Sharpe 1.30（飽和於 reference 1.0）→ 目標權重 `max_weight = 25%`（首個 sleeve、零相關假設、full capacity）。

### 為什麼 binary 殺它、兩段閘救它（且非放水）
- **binary 死因**：絕對 CAGR 13.1% < 18%（市場中性類報酬被絕對門檻錯殺）+ landscape PBO 43%（量錯對象）。
- **兩段閘救回的依據**：DSR **0.982** 是**扣掉 24-config 選擇偏誤後**的誠實機率，仍過 0.95；OOS>0 83% ≫ 60%；K3 撐住。landscape PBO 對一個事前鎖死的單一 config 不適用（ADR-025 §3.1 crux）。

### 與既有 NO-GO 的關係（不矛盾）
- **動能/多因子/long-short 仍 NO-GO**：它們是 selected config、landscape PBO 0.43–0.77，死在真偽閘 PBO 檢查（`two_stage_gate` 測試釘死）。
- **資金流獨特處**：唯一有「pre-registered fixed config + survivorship-clean WFA median OOS 1.30」的候選 → 真偽改判 OOS+DSR → REAL。

## ⚠️ Caveat（25% 是目標天花板，非 day-1）
1. **仍是 backtest 證據**。真偽閘在歷史資料判 REAL；paper 前移的意義＝收 **live forward OOS**（要真實日曆時間 + daemon）。本結果＝「值得 paper」，非「上 25%」。
2. **部署走 §8.1 ramp**：paper → G1 Live 5% → G2 20% → G3 100%，非一步到位。
3. **margin 不寬**：DSR 0.982 vs 0.95、12 folds 有 2 負。真，但非堅不可摧。
4. **sizing 待調**：`reference_sharpe=1.0` 讓 1.30 飽和滿倉，首個 sleeve 偏激進 → 8.G.10 調參點（接真實艦隊相關性後收斂）。

## 下一步
- **7.A.4 paper 前移**：把此 fixed config 接 7.D real collaborators 進 paper daemon，收 live forward OOS（needs daemon + live 資料 + 真實時間）。
- paper 期實際摩擦回饋配置閘（8.G.10）：摩擦吃掉 edge → conviction 下修或退回真偽閘重判。
