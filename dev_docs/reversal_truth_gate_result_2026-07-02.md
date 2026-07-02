# reversal 真偽閘判決（2026-07-02）

> **策略**：短期反轉（`strategies/reversal/`，PR #156）| **判決路徑**：`truth-gate --strategy reversal`（ADR-029 標準工作流 + ADR-030 修正閘 + PR #148 誠實成本）
> **Universe**：survivorship-clean 423 檔含下市（`data/parquet_finlab_universe`）| **窗口**：IS 2010-2021、OOS holdout 2021-2024
> **預註冊 config**：weekly / lookback 5 / skip 1 / decile 0.1 / lump（全文獻標準值，設計時未接觸資料）

## 判決：🔴 REJECTED（四條 hard-fail 全滅）

| 指標 | 值 | 門檻 | 判 |
| :--- | :--- | :--- | :--- |
| K3 滑價 Sharpe（+0.3%/leg） | **-3.62** | > 0 | ✗ |
| OOS holdout Sharpe（2021-2024 封存段） | **-1.90** | > 0 | ✗ |
| WFA OOS+ 廣度（5 folds） | **0%** | ≥ 60% | ✗ |
| DSR（n_trials=12） | **≈ 0** | ≥ 0.95 | ✗ |

## 解讀

1. **不是邊緣失敗，是方向性死亡**：WFA 五折全負 + holdout -1.9 表示 long-only 反轉腿在台股此 universe 的訊號本身為負，成本只是雪上加霜（slip -3.62 顯示週頻 turnover 的成本殺傷如文獻預期）。與 inst_flow 的「真實但不夠強」（Paper-Watch）完全不同級別——reversal 距觀察艙門檻十萬八千里。
2. **預註冊紀律的價值**：config 全部來自文獻、實作於無資料的 worktree——本判決是乾淨的單次假設檢定，n_trials=12 誠實通縮，無 cherry-pick 空間。
3. **候選處置**：廢止。不進 DOE 打撈（在四條全滅的地形上 sweep 參數＝製造過擬合）。`strategies/reversal/` 保留為 registry 對照標本（比照 four_layer 慣例）。

## Edge family 記分板（截至 2026-07-02）

| Family | 判決 | 死因 |
| :--- | :--- | :--- |
| 四層共振 | 廢止（ADR-023） | 負 edge、毀價值（對照診斷） |
| 動能 12-1 | NO-GO（ADR-023） | 真實但未達部署門檻 |
| 多因子 / long-short | NO-GO | landscape PBO 0.46-0.77 |
| 法人資金流 | 🟡 **PAPER_WATCH**（ADR-033） | DSR 0.908 差 0.042——收 live OOS 中 |
| 短期反轉 | REJECTED（本檔） | 訊號為負 + 成本殺傷，四條全滅 |
