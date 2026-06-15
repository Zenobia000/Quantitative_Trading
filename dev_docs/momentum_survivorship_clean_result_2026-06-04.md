# 動能 — survivorship-clean 終驗結果（2026-06-04）

> 承 `momentum_large_universe_result_2026-06-04.md`：動能在 129 檔大 universe OOS-robust（WFA 1.28），但**仍是現存上市（survivorship-biased）**。本文加入**下市股（消失的輸家）**做 survivorship 修正——這是可部署前最關鍵的一關。

## 為何 + 怎麼做

survivorship 偏誤的來源＝universe 只含「活到今天」的股票，**漏掉中途下市的輸家**（它們通常因表現差而下市）。
- FinMind **`TaiwanStockDelisting`** 資料集列出下市股（id + 下市日，共 340）；其**截斷的歷史價格仍可取**。
- **關鍵**：`backtest_momentum` 本就 point-in-time 排名（每次再平衡 `mom.dropna()`）→ 下市股**活著時被排名、下市後自動掉出**，無需改回測。所以 survivorship 修正＝**把下市股加進 universe**。
- `scripts/delisted_universe_ingest.py`：篩 4 碼、非 ETF(00)、2014-06 後下市的 **95 檔**；實際 ingest **47 檔**（FinMind 時限擋住其餘）→ universe **130 → 176 檔**（survivors + 下市輸家）。

## 結果（129 survivors → 176 survivorship-aware）

| 指標 | 129 檔（survivors） | **176 檔（survivorship-aware）** |
|:--|:--|:--|
| best full-span Sharpe | 0.990 | **0.894**（加輸家 → 拉低，符預期）|
| **PBO** | 30.3% | **29.2% ✅**（反而過門檻）|
| **DSR** | 1.00 ✅ | **1.00 ✅** |
| **WFA OOS Sharpe** | 1.28 | **1.07 ✅**（仍 > 1.0）|
| **OOS/IS** | 0.99 | **0.91** |
| 2022 崩盤 fold | −0.66 | −0.54 |
| OOS folds > 1.0 | 5/6 | **5/6** |

WFA 逐 fold OOS Sharpe：1.57 / 0.59 / 1.94 / 1.65 / **−0.54** / 1.21。

## 判決：動能 edge **撐過 survivorship 修正**

- 加入下市輸家後，所有數字**如預期被拉低**（best Sharpe 0.99→0.89、WFA OOS 1.28→1.07、OOS/IS 0.99→0.91）——證實 survivorship **確實有在膨脹**結果。
- **但三道防過擬合 gate 全數仍過**：PBO 29.2% ✅、DSR 1.00 ✅、WFA OOS 1.07 ✅（> 1.0）。
- **每加一層嚴謹度（對抗→量化→大 universe→survivorship）數字都被拉低，但都站在門檻上方——這正是「真 edge」的特徵**（假 edge 會崩，真 edge 優雅退化）。

**這是專案至今最強的證據：動能是 survivorship-robust、OOS-validated 的可部署候選**——歷經對抗式驗證、PBO/DSR/WFA、大 universe generalize、survivorship 修正四關仍站著。

## 仍要誠實的 caveat（離 final go 還差這些）

1. **只 ingest 47/95 下市股**（FinMind 時限）。趨勢向下（1.28→1.07），補齊剩 ~48 檔**可能把 OOS Sharpe 推向 ~1.0 邊際**。→ follow-up：時限重置後重跑 idempotent ingest。
2. **非完整 point-in-time band 選股**：survivors 仍是現存挑選、無逐季市值 band（FinMind 無乾淨市值源）。這是「survivorship-aware」非「完整 point-in-time membership」。
3. **成本模型 Sharpe-optimistic**（`strategy.py` 已註）→ 修了 OOS Sharpe 可能再降一點。
4. **PBO 29% 卡門檻邊** → 部署鎖**固定 config**（lb=252/skip=21/top=0.33），非每次挑 IS-best。

## final go/no-go 清單
- [ ] 補齊 95 檔下市股全 ingest（時限重置後）
- [ ] 真實攤提式成本模型
- [ ] 鎖固定 config，跑 paper trading（7.A/7.C/7.D 已備）
- 若上述後 OOS Sharpe 仍 ≥ 1.0 + PBO < 30% → **可進 paper**。
