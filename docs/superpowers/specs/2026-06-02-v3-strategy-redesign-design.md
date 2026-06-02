# v3 策略重設計 — 補齊 v2.md §2.1 + 中小型 universe

> **狀態：** Draft（待使用者核准）
> **日期：** 2026-06-02
> **觸發：** [[ADR-017]] M2 IS gate FAIL → 回 M0 重設進場
> **相關：** `strategy/v2.md` §2.1-2.2、[16 WBS R9](../../../dev_docs/16_wbs_development_plan.md)、[[m2-is-gate-failed-m0-entry-redesign]]、M0 scope `2026-06-02-m0-entry-redesign-scope.md`

---

## 1. 目標（Goal）

把 v2.md §2.1 設計但**從未實作**的核心元件補齊，並在其**設計指定的中小型股 universe**（非先前誤用的大型股）上重跑 ADR-016 gate，確認「完整實作的原假設」是否有 edge —— 而非先前在不完整實作 + 錯 universe 上得到的偽 no-edge 結論。

**核心重新框架**：M2 IS FAIL 不是因為 hypothesis 死，而是因為：
1. 測在**大型股**（edge 源弱），但 v2.md §2.1.1 明指**中小型股**
2. 缺 **min-2-day hold**（§2.1.3 "避免假突破洗單"）→ 3 天 churn
3. 缺 **time-stop**（§2.1.3 max 60 天）與 **regime filter**（§2.1.2 大盤 20MA 斜率）

## 2. 設計決策（已與使用者確認 2026-06-02）

| 決策 | 值 | 來源 |
|:--|:--|:--|
| 候選 universe 市值帶 | 全市場市值**排名 30-70 百分位**（中段）| 使用者拍板（v2.md §2.2 原為 ❌ 未定義）|
| Universe 重平衡 | **動態月頻重篩**（point-in-time，避生存者偏誤）| 使用者拍板 |
| 並行持倉上限 | **最多 10 檔、等權**（~10%/檔）| 使用者拍板 + v2.md §2.1.4 |
| min hold | **2 bars**（hard stoploss 例外）| v2.md §2.1.3 |
| max hold | **60 bars**（time-stop）| v2.md §2.1.3 |
| regime filter | 大盤 20MA 斜率 < 0 → 只持有不新增 | v2.md §2.1.2 |

**關鍵概念解耦**（回應「檔數多 = 買指數」疑慮）：
- **掃描池**（候選 universe）廣 = 給選股訊號更多機會（解進場太稀）
- **持倉**集中 = 由四層共振選股 + 10 檔上限決定 = 集中度來源
- 廣掃描 + 嚴選股 + 限持倉 ≠ closet indexing

## 3. 架構：三條工作流（建議按序，各自 Phase 2 plan）

### WS1 — 補齊 §2.1 持倉控制元件（最高槓桿、可先在現有資料快驗）

**檔案：** `config/strategy_config.py`、`strategies/four_layer_resonance/signals.py`、`engines/zipline_adapter/algorithms/four_layer_resonance.py`

- `StrategyConfig` 新增：`min_hold_bars: int = 2`、`max_hold_bars: int = 60`
- 出場 gate：`evaluate_bar` / `_evaluate_priority` 需知道「已持有幾 bar」→ 由呼叫端（algorithm 讀 zipline position、regression harness 自維護）傳入 `bars_held`
  - `flameout` / `exit` / `reduce` / `takeprofit`：`bars_held >= min_hold_bars` 才可觸發
  - `stoploss`（跌破箱底/swing low）：**不受 min-hold 約束**（風險信號優先，v2.md §2.5.3）
  - `bars_held >= max_hold_bars`：強制 time-stop 出場（新 action 或併入 exit）
- **介面變更**：`EvaluateBar` 加 `bars_held: int`；`evaluate_window_with_state(..., bars_held)`；algorithm 從 `context.portfolio.positions[asset]` 推算持有 bar 數（需記錄 entry bar index per asset）

### WS2 — 中小型 universe 建置 pipeline（點時市值資料 + 月頻重篩）

**檔案：** `data/universe.py`（擴充）、新 `data/universe_builder.py` 或 CLI、`config`

- `UniverseConfig` 改市值篩選為**百分位**（`market_cap_pct_low=0.30, market_cap_pct_high=0.70`），需全市場橫斷面市值排名（非絕對門檻）
- 月頻 snapshot：每月初用 point-in-time 市值 + 60 日均量/額排名 → 取中段 + 流動性過濾 → 該月候選清單
- 資料源：FinMind 全市場 `TaiwanStockInfo` + 市值（`TaiwanStockPrice` × shares 或 FinMind 市值 dataset）
- ingest：候選池（跨所有月份的聯集，去重）批次 ingest 進 parquet + zipline bundle（沿用 `ingest_universe` / `ingest` CLI）
- **生存者偏誤**：月頻 point-in-time 重篩已大幅緩解；下市股若 FinMind 免費版無資料則接受殘餘偏誤（記為已知限制，R7）

### WS3 — 整合回測 + 重跑 ADR-016 gate

**檔案：** `engines/zipline_adapter/algorithms/four_layer_resonance.py`、CLI、`validation/`

- algorithm 支援：月頻 universe 切換（每月更新 `context.assets` / 候選池）、並行持倉上限 10 檔（超過時依 total_score 排序取前 10）、regime filter（大盤 20MA 斜率閘）
- regime 資料：大盤指數（TAIEX 發行量加權 or 0050）日線 → 20MA 斜率；斜率 < 0 → `evaluate_and_trade` 跳過新進場（只允許出場/持有）
- 重跑 ADR-016 gate：2015-2020 + 2020-2024 雙窗口，K1/K2/K3 對照
- 探針保留：與 v2 baseline 對照（證明 v3 改善幅度）

## 4. 資料流

```
月初 → universe_builder（point-in-time 市值排名 30-70% + 流動性）→ 當月候選清單
     → ingest（parquet + zipline bundle，候選聯集）
backtest（run_algorithm）每日：
  regime check（大盤 20MA 斜率）→ 若 <0 禁新進場
  for asset in 當月候選:
    score → evaluate_bar(含 bars_held, min/max hold gate) → action
  進場候選排序 → 受 10 檔上限 + 等權約束下單
→ perf → ADR-016 K1/K2/K3 對照
```

## 5. 錯誤處理 / 邊界

- 月頻重篩時某 asset 退出候選但仍持倉 → 允許持有至出場訊號（不強制平倉），但不再加碼
- point-in-time 市值資料缺失月份 → 沿用上月清單 + log 警告
- regime 指數資料缺失 → 預設允許進場（fail-open）+ log
- min-hold 與 stoploss 衝突 → stoploss 永遠優先（風險不可被 min-hold 阻擋）

## 6. 測試策略（TDD）

| 元件 | 測試 |
|:--|:--|
| min-hold gate | 持有 1 bar 時 flameout 不出場、2 bar 時可出場；stoploss 不受 min-hold 限制 |
| max-hold time-stop | 持有 60 bar 強制出場 |
| regime filter | 大盤斜率 <0 時新進場被擋、出場不受影響 |
| universe percentile | 給定市值橫斷面，30-70% 正確取中段 |
| 月頻重篩 | 跨月清單變化、持倉 grandfathering |
| 持倉上限 | >10 進場候選時依分數取前 10、等權 |
| 整合 | v3 雙窗口回測跑通 + 與 v2 baseline 對照 |

CI 全 mock（不打 FinMind）；live 回測為一次性 acceptance（沿用 runbook 模式）。

## 7. 範圍與分解（Phase 2 多 plan）

本 spec 涵蓋 3 個子系統，**Phase 2 應拆為 3 個循序 plan**：
1. **Plan A = WS1**（持倉控制元件）— 可先在現有大型股 cache 快驗「3 天 churn 是否被 min-hold 修正」
2. **Plan B = WS2**（universe pipeline）— 較重的資料工程
3. **Plan C = WS3**（整合 + 重跑 gate）— 依賴 A + B

建議先做 Plan A（最高槓桿、最低成本），其結果可能影響 B/C 的細節。

## 8. 驗收條件

- [ ] WS1-3 各自 plan 的測試全綠、coverage ≥ 80
- [ ] v3 在中小型 universe 雙窗口 IS 回測跑通
- [ ] 對照 ADR-016 K1/K2/K3：通過 → M2 復活；未過 → 帶證據回 M0 評估是否砍策略（R9 致命路徑）
- [ ] v2.md §2.1/2.2/2.4 同步更新為 v3 落地版本（§6.3 changelog）
- [ ] 16 WBS / ADR（v3 結果新 ADR）/ INDEX 同步

## 9. 不做（YAGNI / 紀律）

- 不在 v3 未驗證前跑 M3 DOE/WFA/PBO
- 不一次塞「放寬進場 AND」+「換 universe」+「補元件」全部變數（先補元件 + 換 universe；進場 AND 是否放寬留待 v3 baseline 出來再評估，避免無法歸因）
- 不入版控 parquet / zipline bundle（沿用 .gitignore + runbook）
