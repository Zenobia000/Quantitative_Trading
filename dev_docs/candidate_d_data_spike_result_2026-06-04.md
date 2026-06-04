# Candidate D — §3 資料可得性 spike 結果（2026-06-04）

> **GATING spike**（設計 spec `2026-06-03-candidate-d-smallcap-universe-design.md` §3）。
> 在做任何 Candidate D 實作/回測前先過。腳本：`backtest_platform/scripts/candidate_d_data_spike.py`（live FinMind v4）。

## TL;DR

| 資料組 | 機制層 | 結果 | 來源 |
| :--- | :--- | :--- | :--- |
| OHLCV | L1 結構 / L4 動能 | **🟢 可得**（樣本 85% 平均覆蓋，全歷史檔 ~100%） | FinMind `TaiwanStockPrice` |
| 三大法人 | L2 法人方向 | **🟢 可得**（樣本 86% 平均覆蓋） | FinMind `TaiwanStockInstitutionalInvestorsBuySell` |
| 市值 / 排名 | universe builder 選擇輸入 | **🟡 待解**（試過 3 個 dataset 皆無資料） | 需另尋 / 衍生 / 改用 turnover proxy |
| 券商分點籌碼 | **L3 籌碼強度** | **🔴 user-gated** | **FinLab 付費方案**（最大風險，需使用者授權） |

**結論**：四層機制的 **L1/L2/L4 資料對中小型股充分可得**（2015-2024）。**兩道閘待解**：
(a) universe builder 的市值排名輸入；(b) L3 籌碼層（FinLab 付費）。

## 證據（樣本 12 檔，2015-01-01 ~ 2024-12-31）

- `TaiwanStockInfo`：4135 列 → twse 4 碼 1998 檔 → 排除已知大型後 **1948 檔**小/中型候選池。
- 抽樣（依排序均勻取樣，非 RNG）：0050, 1460, 1727, 2316, 2447, 2702, 3044, 3605, 4934, 6202, 6743, 8045。

| 股票 | OHLCV 列 | span | %cov | INST 列 | %cov | 註 |
|:--|--:|:--|--:|--:|--:|:--|
| 1727 | 2439 | 2015..2024 | 100% | 9076 | 100% | 全歷史 |
| 2702 | 2439 | 2015..2024 | 100% | 9218 | 100% | 全歷史 |
| 3044 | 2439 | 2015..2024 | 100% | 11485 | 100% | 全歷史 |
| 3605 | 2439 | 2015..2024 | 100% | 11468 | 100% | 全歷史 |
| 6202 | 2439 | 2015..2024 | 100% | 11469 | 100% | 全歷史 |
| 1460 / 2316 / 4934 | ~2430 | 2015..2024 | 99% | ~11400 | 100% | 全歷史 |
| 8045 | 1859 | 2017-05.. | 76% | 844 | 34% | 2017 上市 |
| 6743 | 1235 | 2019-12.. | 50% | 5117 | 100% | 2019 上市 |
| **2447** | **0** | — | **0%** | 0 | 0% | **已下市**（anti-survivorship：下市檔確實出現在 info） |
| 0050 | — | — | — | — | — | ETF（樣本漏抓，實跑須排除 ETF） |

- **OHLCV 平均 85% / 法人 86%**；12 檔中 **10 檔兩組都 ≥50%**。
- **市值 probe**：`TaiwanStockMarketValue` / `TaiwanStockMarketValueWeight` / `TaiwanStockPER` 三者皆回空 → 市值輸入**未在常見 dataset 直接可得**。

## 待解閘與選項

### 閘 (a) — universe builder 市值排名輸入 🟡
universe_builder（`data/universe_builder.py`）需 as-of `market_cap` 排名以排除前 50 大、保留 band (50,300]。FinMind 常見 dataset 未直接提供。**選項**：
1. **衍生**：股本（capital）× 收盤價，或流通股數 × 價（需找 FinMind 股本/股數 dataset）。
2. **turnover proxy**：用 `avg_amount_20`（價×量，已可得）當 size 代理排名——偏離設計（market_cap → turnover），但全程 FinMind 免費可得、且 liquidity 與 size 高相關。
3. **FinLab/TEJ**：付費市值 dataset（與 (b) 一併授權）。

### 閘 (b) — L3 籌碼層（券商分點）🔴 user-gated
`top_broker_buy` / `key_broker_buy` 需 **FinLab 付費進階方案**（設計 §3「最大風險」）。現有 large-cap parquet 已是 **chips=0**（FinMind 免費無此欄），故大型股「無 edge」判決本身就是 **L3 退化**下得到的。

**含意**：若**不**取得 FinLab 付費籌碼，Candidate D 也只能在 **L3 退化（chips=0）** 下跑 → 測的是「中小型 universe + L1/L2/L4」是否有 edge，與大型股結論的 L3 條件一致（可比較）。若 chip 層是四層的關鍵 alpha 來源，則 FinMind-only 的中小型實驗也不會翻盤——這本身是一個要使用者決策的分岔（設計 §3 紅燈分支：去 chip 層的機制變體 / 砍策略）。

## 建議下一步（需使用者決策）

1. **籌碼決策**：要不要授權 FinLab 付費取 L3？（決定 Candidate D 是「完整四層」還是「L3 退化三層」實驗）
2. **市值輸入**：選 (a) 衍生 / (b) turnover proxy / (c) 付費——我可實作 turnover-proxy 版讓 universe builder 全 FinMind 跑得起來（最快、零付費）。
3. 二者定案後：建 point-in-time 面板 → universe_builder 選池 → ingest OHLCV+法人 → `run-is --preset v3.1b --stocks <Candidate D> → gate` 雙窗。

**在使用者就 (1)(2) 給方向前，full 重驗不啟動**（避免跑出 survivorship-biased 或 L3 條件未定的誤導性結果）。
