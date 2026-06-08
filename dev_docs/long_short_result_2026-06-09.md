# Long-short 中性化 — survivorship-clean 結果（2026-06-09）：🔴 NO-GO（四結構收斂同牆）

> 承「三 long-only 結構同牆 → 約束疑為市場 beta 天花板」。long-short dollar-neutral
> 拿掉 beta、直接交易 cross-sectional spread（fixed-config OOS 曾 1.0-1.6）。直接在
> 116 檔 survivorship-clean 驗。

## 結果

| 關卡 | multi-factor long-only | **long-short** | 門檻 | 判 |
|:--|:--:|:--:|:--:|:--:|
| WFA median OOS | 1.57 | 1.08 | >1.0 | ✅ |
| PBO | 77% | **45.7%** | <30% | ❌ |
| 全期 CAGR | 13.2% | **10.5%** | >18% | ❌ |
| 全期 Sharpe | 0.91 | **0.87** | >1.0 | ❌ |
| MaxDD | 31% | **26.9%** | — | （唯一改善）|

**判決：🔴 NO-GO。** 假設再次被推翻：L/S **沒有突破**——CAGR 反而更低（10.5% < 13.2%），
因為拿掉的市場 beta 原本是正貢獻（long-only 報酬的主要 carry），而殘餘的 cross-sectional
spread 本身只有 ~0.87 Sharpe。唯一改善是 MaxDD 31%→27%（beta 中性化降回撤）。

## 🎯 收斂 meta 結論：四結構、同一道 ~0.9 Sharpe 牆

| 結構 | 全期 Sharpe | 全期 CAGR | PBO |
|:--|:--:|:--:|:--:|
| 動能（單，long-only）| 0.90 | ~13% | — |
| 資金流（單，long-only）| 0.90 | 13.1% | 43% |
| 多因子（組合，long-only）| 0.91 | 13.2% | 77% |
| 多因子（**long-short**）| 0.87 | 10.5% | 46% |

**四個獨立結構（兩 family × 單/組合 × long-only/long-short）全部落在 Sharpe ~0.87–0.91、
CAGR 10–13%、PBO 高。** 換因子沒用、換組合沒用、換 long/short 結構也沒用。

**結論（強證據）**：在「台股大/中型 universe + 免費資料 + 嚴格 ADR-016（18%+3% buffer）」
這組約束下，**不存在可部署的 cross-sectional 因子 edge**。訊號真實但**一致地 ~0.9 Sharpe**，
系統性低於 1.0 / 18% 門檻——這是該 universe 類別的**結構天花板**，非「還沒試對結構」。

## 真正剩下的槓桿（皆為外部約束，非再寫 code）

1. **換 universe 類別**：中小型（報酬更高，但成本/流動性/借券更難；需重測，非保證）。
2. **重檢 ADR-016 門檻**：18%+3% buffer 對台股大型 long-only 是否過嚴（**政策決策；使用者已表態守不放寬**）。
3. **換市場/資產類別**：門檻假設基於更高報酬環境。
4. **接受結論**：在當前約束下無可部署 edge —— 平台的誠實答案，且在真錢前擋下 ~0.9 Sharpe 的假希望。

## 平台意義（這才是真正的交付）

平台從「驗單一策略」→「對 strategy space 做結構性推論」→ 現在**用 4 個獨立結構的收斂失敗
證明牆是結構性的**。這是嚴謹量化研究該有的樣子：不是無止境試變體，而是用多重正交證據
triangulate 出約束的本質，知道**何時該停**。腳本 `scripts/long_short_gates.py`。
