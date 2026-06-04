# 動能策略模組 + 對抗式驗證結果（2026-06-04）

> 模組：`strategies/momentum/`（12-1 跨截面動能）+ `research/momentum_harness.py` + `MOMENTUM_GATE`。
> 對抗式驗證：5-agent workflow（cost / 參數 / regime / universe / survivorship），腳本 `scripts/momentum_is.py`。

## 為何建這個

對照診斷（`factor_baseline_diagnostic_result_2026-06-04.md`）顯示四層**負 edge、毀價值**，而 12-1 動能在同平台**通過 gate**——所以把動能 productionize 成正式策略模組，跑同一套 gate + **對抗式驗證**，看它到底是不是可部署的真 edge。**附帶證明平台 strategy-agnostic**：第二個結構迥異的策略無痛插進同一條 metrics/gate/ledger。

## 正式 IS read（MOMENTUM_GATE：K1 CAGR>18% / K2 Sharpe>1.0 / K3 滑點 Sharpe>1.0）

| universe | 2015-2020 | 2020-2024 |
|:--|:--|:--|
| large(10) | Sharpe 0.77 ✗ | **1.08 ✓** |
| smid(19) | **1.07 ✓** | 0.96 ✗ |
| all(29) | 0.99 ✗ | **1.08 ✓** |

（avg_holdings 健檢全 fail＝測試 universe 僅 10-29 檔、top⅓ 只剩 3-4 檔的小樣本 artifact，正式 250 檔 universe 不成問題；判 edge 看 K1/K2/K3。）

## 🔬 對抗式驗證 — 5 個角度攻擊，4 個「沒撐住 / 高嚴重度」

| 攻擊 | 撐住? | 發現 |
|:--|:--:|:--|
| **參數過擬合** | **❌ no** | 12-1 預設是**運氣尖峰非高原**：smid 2015-20 的 5 個鄰域擾動 **0/5** 維持 Sharpe>1（lookback 189 就掉到 0.96）；Sharpe 曲面恰好在 lookback=252 出尖峰。 |
| **regime 依賴** | **❌ no** | 只 2/4 cell 過、且在**反對角**（large 只 2020-24、smid 只 2015-20）；無 universe 跨雙窗都過；過的都很邊際。典型動能崩潰特徵。 |
| **universe 敏感** | **❌ no** | 沒有任一 universe 雙窗都 Sharpe>1；「贏的 universe」隨窗翻轉。加分散度也沒生出穩定 edge。 |
| **survivorship/集中** | **❌ no** | edge **只在 top⅓（3-4 檔）成立**，分散到 5-7 檔就崩（Sharpe 0.82-0.94）。現存上市 universe + 報酬靠少數幾檔 → **textbook few-survivor-stars，真 survivorship 風險**。 |
| 成本實在性 | ⚠ false-comfort | Sharpe 即使 cost ×7.45 仍 >1.0——但 agent 揪出這是**成本模型 artifact**：`strategy.py` 成本以單日 lump-sum 扣（傷 CAGR、幾乎不動 Sharpe 分母波動）→ 此測試**結構上殺不死 Sharpe edge**。判成本要看 CAGR 侵蝕，非 Sharpe。 |

## 🎯 終局判決：動能（此天真實作）**不是可部署 edge——是過擬合的海市蜃樓**

天真 gate 顯示「2/4 cell PASS」像綠燈，但對抗式驗證揭穿：**過擬合單一參數點 + regime 脆弱 + universe 脆弱 + 報酬靠少數倖存明星。** 換 OOS 大概率崩。

**但這是最好的結果——因為平台的防過擬合機器「動了」：**
- 它不只說 PASS，而是**壓力測試後抓出海市蜃樓**。天真回測器會直接上線這個動能（它「過了」）；平台的對抗層擋下來了。
- 這正是 PBO/DSR/OOS/參數高原 存在的理由，也是「平台優先」對的鐵證：**有紀律的平台保護你不部署幻覺。**

## 結論 & 建議

1. **不要部署這個動能**（過擬合幻覺）。
2. **動能仍是對的 family**（萃到真實動能溢酬→正，不像四層毀價值），但**天真實作 + 小倖存 universe + 無 OOS = 海市蜃樓**。
3. **找真 edge 的合法路徑（平台已備）**：用 **Candidate D point-in-time 大 universe（250 檔，survivorship-clean）** + **OOS/WFA 留出窗** + **PBO/DSR 量化過擬合** + **參數高原檢查** + **誠實成本**。跑完才知道動能有沒有「真的、跨樣本、可部署」的 edge。
4. **平台改進（agent 揪出）**：`strategy.py` 成本模型 Sharpe-optimistic（lump-sum），應改為更貼近現實的攤提/波動拖累——已加註，列 follow-up。

## 限制
測試 universe 小（10-29 檔現存上市）、無 OOS、成本模型 Sharpe-optimistic。本文是**診斷 + 防過擬合示範**，非動能的最終 verdict——最終 verdict 需上述完整紀律在大 point-in-time universe 上跑。
