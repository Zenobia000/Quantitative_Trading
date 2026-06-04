# 動能 — 大 universe 重驗結果（2026-06-04，a→b→c 的 c）

> 承 `momentum_strategy_result_2026-06-04.md`：動能在 29 檔小倖存 universe 上 WFA OOS Sharpe 0.84（未達部署）、且 (b) vol-target 風控沒救到。**兩者都指向同一個 binding 限制：universe 太小 + 倖存偏誤。** (c) 直接放大 universe 驗證此假設。

## 做法
- `scripts/momentum_universe_ingest.py`：FinMind 抓 **+100 檔**新中小型股（adjusted OHLCV 2014-2024）→ parquet。universe **29 → 130 檔**（~4.5x）。
- 重跑同一條完整防過擬合（30-config grid + PBO + DSR + WFA），vanilla 12-1，all universe（129 檔，扣 0050）。

## 結果（29 vs 129 對照）

| 指標 | 29 檔（小） | **129 檔（大）** |
|:--|:--|:--|
| best full-span Sharpe | 1.125 | 0.990（更低、更實際）|
| PBO | 21.4% ✅ | 30.3% ❌（卡在 30% 門檻邊）|
| DSR | 1.00 ✅ | 1.00 ✅ |
| **WFA OOS Sharpe** | **0.84 ❌** | **1.28 ✅** |
| **OOS/IS** | 0.62 | **0.99** |
| 2022 崩盤 fold | −1.26 | **−0.66**（崩盤約砍半）|
| OOS folds > 1.0 | 2/6 | **5/6** |

WFA 逐 fold OOS Sharpe（大）：1.61 / 1.05 / 2.27 / 1.97 / **−0.66** / 1.42。

## 🎯 判決：universe **確實是** binding 限制——動能在大 universe **OOS-robust**

- **WFA（真 OOS 測試）從 0.84 → 1.28，跨門檻**；**OOS/IS 0.62 → 0.99**（IS 選出的 config 幾乎完美 generalize OOS）——這是 29 檔做不到的。
- **動能崩盤被分散度馴服**（−1.26 → −0.66，砍半）——正合理論：更多檔 → 崩盤更可分散。
- 證實前述「小 + 倖存 universe 才是問題、非動能本身」的假設。**這是整條紀律 arc 的正向 payoff：砍四層後，平台用嚴謹驗證浮現出一個真正 OOS-robust 的候選。**

## 仍要誠實的 caveat

1. **129 檔仍是現存上市（survivorship-biased）**。真正乾淨的 verdict 需 **point-in-time 會員（含下市股，universe_builder + 多小時全 ingest）**——下市輸家會拉低，可能吃掉部分 OOS 優勢。29→129 的劇烈改善強烈暗示 universe size 是主因，但**最終可部署判決仍需 survivorship-clean 大 universe**。
2. **PBO 30.3% 卡門檻邊**：參數選擇仍有輕微過擬合 → 部署應用**固定的合理 config（非 IS-best）**，而非每次挑最佳。
3. **2022 崩盤 fold 仍負（−0.66）**：動能崩盤風險仍在（只是砍半）。(b) 的 vol-target 在小 universe 沒用，但**大 universe 上值得重試**（崩盤已較淺、估計噪音較低）——列 follow-up，勿在此急調（過擬合警示）。

## 下一步（建議）
1. **動能升為主力候選方向**（取代四層）：固定一個合理 config（如 lb=252/skip=21/top=0.33），在 129 檔上鎖定 OOS 表現。
2. **survivorship-clean 終驗**：universe_builder point-in-time 面板（含下市）+ 全 ingest → 最終可部署判決。
3. 之後才談 paper trading（平台 7.A PaperBroker + 7.C Risk Gate + 7.D orchestration 已備）。
