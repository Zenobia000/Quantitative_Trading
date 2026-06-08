# 多因子組合 — survivorship-clean 結果（2026-06-09）：🔴 NO-GO（三結構同牆）

> 承動能、資金流兩個**單因子**皆死於 survivorship-clean（真實但弱 + config landscape
> 過擬合）。假設：**固定等權多因子組合** DoF 較少 → PBO 較低，且因子分散 → OOS 較穩。
> 直接在 116 檔 survivorship-clean universe 從頭驗（無 survivor-only 樂觀）。

## 因子（皆免費、皆 lagged / point-in-time）
- momentum（12-1）、inst_flow（net-buy/volume，lag 1）、low_vol（−trailing vol）
- 每再平衡：橫斷面 z-score 各因子 → **固定等權平均** → rank → long top。

## 結果（116 檔 = 40 survivors + 76 下市）

| 關卡 | inst_flow 單因子 | **多因子組合** | 門檻 | 判 |
|:--|:--:|:--:|:--:|:--:|
| WFA median OOS | 1.30 | **1.57** | >1.0 | ✅ |
| **PBO** | 42.9% | **77.1%** | <30% | ❌（更差）|
| 全期 CAGR | 13.1% | **13.2%** | >18% | ❌ |
| 全期 Sharpe | 0.90 | **0.91** | >1.0 | ❌ |

**判決：🔴 NO-GO。** 假設被推翻——組合**沒有**降低過擬合（PBO 43%→77% 反而更糟），
headline 撞**完全相同的牆**（~13%/0.90）。WFA fixed-config OOS 1.57 仍好（分散確實讓
單一 a priori config 的 OOS 更穩），但 (1) config landscape 過擬合更嚴重 (2) 絕對 headline
不夠。

## 🎯 Meta 結論：三結構同牆 → 約束是「結構×門檻」非「因子」

平台至今嚴格驗過**三個不同結構**，全倒在同一處：

| 結構 | WFA fixed-config OOS | 全期 Sharpe | 全期 CAGR | PBO |
|:--|:--:|:--:|:--:|:--:|
| 動能（單）| ~0.86 | 0.90 | ~13% | — |
| 資金流（單）| 1.30 | 0.90 | 13.1% | 43% |
| 多因子（組合）| 1.57 | 0.91 | 13.2% | 77% |

**共同特徵**：fixed-config OOS 都有真實訊號（median 0.86–1.57），但 (a) 全期 Sharpe 卡在
~0.90、CAGR 卡在 ~13%（<18% buffer 門檻）(b) config landscape 過擬合（PBO 高）。

**這不是「沒找到對的因子」，是結構性約束**：
- **台股大型/中型 long-only ≈ 市場報酬（~13%）**，難跨 ADR-016 的 18%（含 +3% 生存者 buffer）CAGR 牆。
- 真實 alpha 存在但弱（OOS Sharpe ~1.0-1.6 fixed config），**被「絕對報酬門檻 + 長期只做多」的天花板壓住**。

**下一步不該再換因子/組合**（已證同牆）。真正的槓桿是換**約束維度**：
1. **long-short 中性化** —— 拿掉 beta/市場天花板，直接放大「弱但真」的 cross-sectional 訊號（OOS 1.0-1.6 暗示 spread 可交易）。
2. 或重新檢視 **18% CAGR + survivor buffer 門檻**對台股 long-only 是否過嚴（屬 ADR-016 政策決策，使用者已表態守不放寬）。
3. 或換**資產類別/市場**（門檻假設基於更高報酬環境）。

## 平台意義

第三次驗證 + 第一次「**用收斂的多重證據定位結構性約束**」：不是逐一試因子的瞎子摸象，
而是三個獨立結構的一致失敗 triangulate 出「牆在哪」。平台從「驗單一策略」進化到「能對
strategy space 做結構性推論」。腳本 `scripts/multi_factor_gates.py`。
