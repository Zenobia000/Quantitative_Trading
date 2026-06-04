# Candidate D — 初步 edge 探針結果（2026-06-04）

> **一面倒探針**（NOT 最終判決）。腳本：`backtest_platform/scripts/candidate_d_probe.py`。
> 操作決策（使用者授權代理）：**先跑 free、不買 FinLab 的 L3 退化探針**，再決定是否值得做 survivorship-clean 全跑 / 付費補籌碼。

## 操作決策（為何這樣跑）

1. **不先買 FinLab**：四層的 L3 籌碼（券商分點）需 FinLab 付費；先用既有 free 資料（chips=0，與 large-cap 無 edge 判決同條件）跑探針，避免 edge 未證先燒 ~10k（承 R9 row「免費診斷先行」紀律）。
2. **一面倒設計**：樣本＝**現存上市**中小型股（survivorship-biased）。生存者偏誤是**樂觀**偏誤（活下來的本就表現好），所以——
   - 連偏誤樣本都**無 edge** → **robust negative**（四層在中小型大概率也無）。
   - 偏誤樣本**有 edge** → inconclusive，才值得做 survivorship-clean 點時序全跑。

## 設定

- 樣本：FinMind `TaiwanStockInfo` 池（twse 4 碼、排除大型）等距抽 20 → 實際可用 **17 檔**：
  0050, 1337, 1507, 1702, 2012, 2314, 2465, 2597, 3040, 3413, 3686, 5285, 6189, 6504, 6792, 7736, 8427。
- 引擎：offline portfolio sim（`run_is`，與 zipline 校準 Sharpe ~0.01，gate review §6）。chips=0（FinMind free）。
- preset：**v2**（baseline）vs **v3.1b**（dirB，目前最佳進場）。雙窗 2015-2020 / 2020-2024。

## 結果

| preset | window | trades | cagr | sharpe | slip Sharpe | struct1% | gate |
|:--|:--|--:|--:|--:|--:|--:|:--|
| v2 | 2015-2020 | 125 | −0.38% | −0.159 | −0.407 | 0.0% | FAIL |
| v2 | 2020-2024 | 127 | −1.11% | −0.332 | −0.551 | 0.0% | FAIL |
| v3.1b | 2015-2020 | 186 | −1.61% | −0.368 | −0.570 | 0.0% | FAIL |
| v3.1b | 2020-2024 | 197 | −3.05% | −0.631 | −0.862 | 0.0% | FAIL |

## 判讀：🔴 ROBUST NEGATIVE

- **四窗四 run 全負、全 gate FAIL**——連 survivorship-biased（樂觀偏誤）中小型樣本都無 edge。
- **v3.1b 比 v2 更差**（兩窗皆然）——與 large-cap 結論一致：v3 放寬傷績效、進場閘非 bottleneck。
- `struct1%=0`（進場乾淨，健檢這維過）→ 問題不在進場品質，是**標的 + 機制本身無 alpha**。

**結論**：四層共振在中小型 universe（L3 退化條件下）**大概率也無 edge**。生存者偏誤本應助長 edge，其缺席是強訊號。Candidate D 的 large/mid → small/mid universe 切換，**未翻盤**。

## 限制（誠實揭露）

- 樣本 N=17 偏小、為**現存上市股（survivorship-biased）**、**chips=0（L3 退化）**、offline sim。
- 唯一未測：**完整 L3（FinLab 付費券商分點）**是否翻盤。但本探針的 robust negative 讓「為了 L3 燒 ~10k」更難正當化。

## 建議下一步（交還使用者決策）

1. **不買 FinLab**（探針不支持籌碼層會翻盤的假設）。
2. 三選一：
   - (a) **去 chip 層機制變體**（L1/L2/L4 三層）再驗一輪——但探針已含此條件且 FAIL，邊際機會低；
   - (b) **重訂 edge 來源 / factor**（非四層共振）——ADR-017 §5 退場路徑；
   - (c) **砍四層共振策略**，平台轉接下一個候選假設（平台已 strategy-agnostic，可直接驗）。
3. 若仍要 survivorship-clean 定論：turnover-proxy `universe_builder` + 點時序全 ingest（多小時資料工）+ 重跑——但 ROI 在上述 robust negative 後偏低。
