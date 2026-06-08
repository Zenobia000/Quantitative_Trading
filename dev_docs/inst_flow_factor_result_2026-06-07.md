# 三大法人資金流因子 — 首輪結果（2026-06-07）：🟢 通過 IS+OOS（待寬 universe / WFA / PBO）

> 承「換 edge family」。動能 family 在誠實條件下確認 NO-GO（R9 Step 10）。本次換到
> **三大法人資金流因子**（非動能、流量/情緒驅動、免費 FinMind 三大法人資料），用已證可信
> 的統一 pipeline 從零驗。**這是平台首個 IS+OOS 雙過的 edge candidate。**

## 因子定義
- **訊號**：trailing 三大法人 net-buy **強度** = Σ(net_buy, lookback) / Σ(volume, lookback)
  —— net-buy 佔成交量比例，跨股可比；橫斷面 rank、做多前 1/3、再平衡。
- **機制**：rebalance/cost/vol-target 沿用動能模組（同 plumbing，僅訊號不同）。
- **杜絕 look-ahead**：`signal_lag_days=1`（預設）——用截至 rb−1 的 net-buy 排序，避免
  「外資當日買→當日漲」的同期衝擊被誤當預測力。**加 lag 後 Sharpe 1.35→1.30，幾乎不變
  → 非 look-ahead，訊號真實。**

## 結果（DEFAULT_UNIVERSE 10 大型股，統一 full_validation_report，誠實 DSR）

DOE 16 configs 最佳：**quarterly / lb=60 / foreign / vt=None**。

| 窗口 | CAGR | Sharpe | MaxDD | 判 |
|:--|--:|--:|--:|:--:|
| IS 2016-2020 | 28.5% | **1.30** | 30.8% | — |
| **OOS 2021-2024**（固定 config，不重選）| **21.3%** | **1.04** | 31.6% | 🟢 |
| ADR-016 門檻 | >18% | >1.0 | — | |

- **IS+OOS 雙過**：OOS Sharpe 1.04>1.0、CAGR 21.3%>18%——固定 config 出樣本撐住
  （IS→OOS 正常衰減，未崩）。**動能正是死在這關（OOS 0.63-0.86）；資金流因子撐過。**
- DOE 多個 config 過閘（Sharpe 1.30/1.29/1.24/1.18…），非單點僥倖；DSR 0.98-0.99（含 16-trial deflate）。
- 對比同 universe/plumbing：動能最佳 IS 0.92 vs 資金流 1.30 —— 顯著更強的訊號。

## ⚠️ 尚未繳的稅（GO 前必過，不可自欺）

1. **生存者偏誤**：仍 10 檔現存大型股。註：大型股 survivorship 偏誤遠小於中小型
   （這 10 檔本就長期流動），但仍需 **寬 + survivorship-clean universe** 複驗。
2. **窄 universe**：10 檔、僅 3 持股——集中度/僥倖風險。需擴 universe 確認 breadth。
3. **單一 OOS 窗**：需 **WFA（rolling）** 確認非單一 OOS 窗運氣。
4. **MaxDD 31%**：偏高（健檢黃/紅區）；vol-target 砍到 21% 但壓 Sharpe。需風控設計。
5. **PBO**：需跨 config landscape 正式過擬合檢驗（<30%）。

## 判讀

**首個真實 edge candidate。** 在公平條件（1-day lag 去 look-ahead、固定 config OOS、誠實
DSR）下，三大法人資金流因子在台股大型股 IS+OOS 雙過 ADR-016 的 CAGR/Sharpe/DSR ——
這是平台至今最強、且方法上最乾淨的結果。但**這不是 GO**：survivorship-clean 寬 universe +
WFA + PBO 三關未過。下一步＝擴 universe（含下市）+ WFA + PBO，全綠才談部署。

腳本 `scripts/inst_flow_doe.py`；策略 `strategies/inst_flow/strategy.py`。

---

## GO 關卡（寬 universe 40 檔 + WFA + PBO，2026-06-07，PR #87）

承首輪 IS+OOS 雙過，跑部署前三道關卡（`scripts/inst_flow_go_gates.py`，固定 config
quarterly/lb60/foreign）：

| 關卡 | 結果 | 門檻 | 判 |
|:--|:--|:--|:--:|
| **WFA**（12 rolling folds）| median OOS Sharpe **1.41** · OOS>0 **92%** · OOS>1.0 **67%** | median>1.0 + >0≥60% | ✅ |
| **PBO**（24-config CSCV S=8）| **11.4%** | <30% | ✅ |
| 全期固定 config（40 檔）| CAGR **18.9%** · Sharpe **1.11** | >18% / >1.0 | ✅ |

**三關全過** → 條件式 GO（[ADR-024](./adrs/ADR-024-institutional-flow-candidate-strategy.md)）。
WFA 12 個 rolling OOS 窗 median 1.41、92% 為正——非單一 OOS 窗運氣；PBO 11.4% 低度
過擬合。**平台首個 IS+OOS+WFA+PBO 全過的 candidate。**

### 仍未繳清（GO 前最後）
- **survivorship-clean**：40 檔皆現存（大型股偏誤小但仍需含下市股複驗 WFA/PBO）。
- **CAGR 18.9% 邊際**、**MaxDD ~31% 偏高** → 部署需風控設計。
- 通過 survivorship-clean 後 → paper（實際執行摩擦）→ 小倉位實盤（ADR-016 sign-off）。

---

## Survivorship-clean 複驗（116 檔 = 40 survivors + 76 下市，2026-06-08）：🔴 FAIL

最後一道回測關卡。ingest 76 檔下市股（FinMind `TaiwanStockDelisting` 篩 89 → 76 成功，
free tier；point-in-time 排序自動讓下市股交易期內納入、下市後消失）。`scripts/inst_flow_survivorship.py`。

| 關卡 | 40 survivors (#87) | 116 survivorship-clean | 門檻 | 判 |
|:--|:--:|:--:|:--:|:--:|
| 全期 CAGR | 18.9% | **13.1%** | >18% | ❌ |
| 全期 Sharpe | 1.11 | **0.90** | >1.0 | ❌ |
| PBO | 11.4% | **42.9%** | <30% | ❌ |
| WFA median OOS | 1.41 | 1.30 | >1.0 | ✅ |

**判決：🔴 NO-GO。** 加入下市輸家後 headline 跌破所有絕對門檻、PBO 爆到 43%（config
landscape 過擬合）。**survivor-only 40 檔的 GO 是生存者膨脹的假陽性** —— 與動能死法完全相同。

### 但仍有訊號（誠實的 nuance）
WFA fixed-config median OOS **1.30 仍 PASS**：若**事前承諾單一 config**（不在 landscape 選），
它有真實 OOS edge。問題在 (1) config 選擇過擬合（PBO 43%）(2) headline 絕對值跌破門檻。
→ 三大法人資金流是**真實但不夠強/不夠乾淨**的訊號，守 ADR-016 不部署。

### 平台意義
**平台再次做對它的工作**：survivor-only 看似 GO（1.11/18.9%），survivorship-clean 一照妖
就現形（0.90/13.1%/PBO43%）。這正是 ADR-016 紀律的價值 —— 在真錢前擋下假陽性。動能與
資金流兩個 family 都倒在同一道牆（survivorship+landscape 過擬合）→ 強烈提示：**台股這類
單因子 long-only 在嚴格門檻下難達部署**；下一步應考慮多因子組合 / 不同結構（非再換單因子）。
