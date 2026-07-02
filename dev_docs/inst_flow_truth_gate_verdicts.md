# inst_flow 真偽閘判決總表

> 三大法人資金流（inst_flow）候選策略歷次真偽閘（審判庭）判決的單一彙整檔。
> 判決時間線由新到舊；**當前權威狀態在最上方**。每輪含方法 / universe / 關鍵數字 / 失效或成立原因。
> 相關決策：[ADR-024](./adrs/ADR-024-institutional-flow-candidate-strategy.md)（首度 survivorship-clean NO-GO）、
> [ADR-025](./adrs/ADR-025-two-stage-validation-gate-and-paper-promotion.md)（驗證閘兩段化）、
> [ADR-030](./adrs/ADR-030-truth-gate-judgement-fix.md)（審判庭數學缺陷修正）、
> [ADR-032](./adrs/ADR-032-survivorship-universe-workflow.md)（survivorship universe 建構平台化）。

---

## 當前權威狀態（2026-07-02 最終）

**inst_flow = REJECTED。非 paper-ready。**

survivorship-clean 平台化重驗（ADR-032 工作流 + 423 檔含下市 universe + 2010→2024 全史 + OOS holdout 2021→2024）在**真實交易成本**下的判決：

| 指標 | 值 | 門檻 | 判 |
| :--- | :--- | :--- | :--- |
| DSR（n_trials=16 通縮） | **0.908** | ≥ 0.95 | ✗ |
| WFA OOS+ 廣度（5 folds） | 100% | ≥ 60% | ✓ |
| OOS holdout Sharpe（2021-2024 封存段） | 0.892 | > 0 | ✓ |
| K3 滑價壓力 Sharpe（+0.3%/leg） | 0.846 | > 0 | ✓ |
| survivorship_clean | True（cache 證據） | hard | ✓ |
| IS Sharpe（2010-2021，真實成本） | 1.025 | 參考 | — |

唯一 fail 條款是 DSR 通縮顯著性——資金流 edge 方向真實（OOS 廣度 100%、封存段為正）但強度不足以在 16 次試驗通縮後過 0.95 檻，回到「~0.9 Sharpe 牆」。後續選項：(a) 掃描新 edge family；(b) 依 ADR-025 哲學討論「過 K3/OOS 但 DSR 邊緣」候選是否以極小倉位進 paper 收 live OOS（需新決策）。

---

## 判決時間線

| 日期 | 方法 / 審判庭版本 | Universe | 判決 | 關鍵依據 |
|:--|:--|:--|:--:|:--|
| **2026-07-02** | ADR-030 修正後審判庭，現行 `research_config` 路徑 | `_WIDE` 40 檔（survivor-only）| **🔴 REJECTED** | DSR 0.789、WFA OOS+ 33%、survivorship hard-fail |
| 2026-06-15 | ADR-025 兩段閘（審判庭數學未修正）| FinLab 全史 survivorship-clean，78↔423 檔（含下市）| 🟢 REAL | 跨 universe breadth 皆 REAL；OOS Sharpe ~1.5、DSR ≈1.0 |
| 2026-06-14 | ADR-025 兩段閘（審判庭數學未修正）| survivorship-clean 116 檔（含 76 下市，10-survivor cache 之外首度誠實）| 🟢 REAL | WFA OOS>0 83%、DSR 0.982（n_trials=24 去偏）、K3 撐住 |

> ⚠️ 2026-06-14/15 兩輪 REAL 係在 **ADR-030 修正前**的審判庭數學下得出。ADR-030 揭露舊 DSR 因單位錯配恆等於 ~1.0（年化 SR 配日變異數），修正後對同輸入給出誠實值。故兩輪 REAL 的 DSR 數字須以「舊數學」理解；證據鏈的重建以 sub-project ② 為準。

---

## 2026-07-02 · ADR-030 修正後審判庭重驗 → 🔴 REJECTED（當前權威）

- **觸發**：ADR-030（PR #137）修正審判庭四缺陷後，既往判決作廢須重驗。
- **執行路徑**：`python -m backtest_platform.research.cli truth-gate --strategy inst_flow`（ADR-029 標準化工作流，非已刪 `scripts/`）。
- **程式狀態**：main @ PR #145 合入後（含 ADR-030 修正閘 + ADR-028/029 dispatch + WP6 依賴解纏）。

判決：

```
verdict=REJECTED  DSR=0.7887  slip_sharpe=3.605  WFA OOS+=33.33%
✗ survivorship not clean (survivor-only universe inflates edge)
✗ WFA OOS>0 frac 0.333 < 0.6 (out-of-sample breadth too thin)
✗ DSR 0.789 < 0.95 (deflated significance)
```

**為什麼與 2026-06-15 的 REAL 不同**：

1. **Universe 不同**：現行 `research_config.py` 的 `_WIDE` 是 40 檔存活股——正是 ADR-024 判定假陽性的那個 universe。2026-06-15 用的是 FinLab survivorship-clean 全史 universe（78↔423 檔含下市股），其建構邏輯隨 `scripts/` 刪除，ADR-029 明文延後至 sub-project ②。
2. **審判庭數學不同**：舊 DSR 因單位錯配恆等於 1.0（ADR-030）；修正後對同輸入給出誠實的 0.789。`survivorship_clean` 不再寫死 True，未宣告即 hard-fail——三條 fail 中的第一條正是修正閘拒絕「對存活股 universe 宣稱乾淨」的正確行為。

**結論**：本判決不翻案 2026-06-15 的 FinLab 重驗結論（該輪用的 universe 與方法不同），但確認審查報告的核心指控——「TRUTH GATE REAL」在現行程式路徑無法重現、證據鏈斷裂。inst_flow 的 paper-ready 地位暫停，直到 sub-project ② 重建 universe 建構器 + 用修正後審判庭取得可重現判決。`research_config.py` 的 `_WIDE` 註解已修正為如實描述（survivor-only，truth gate 會正確拒絕）。

---

## 2026-06-15 · FinLab survivorship-clean 全史重驗 → 🟢 REAL（舊數學）

- **子專案**：②（FinLab 資料統一）。**方法不變**（ADR-025 兩段閘 + ADR-016 門檻），只是資料變誠實。
- **動因**：首輪 truth-gate 只用 10 檔大型存活股 cache → CAGR ~33%（survivor-inflated）。付費 FinLab 給全史 2007→今 + 下市股，故在真正 survivorship-clean、全窗（2010-2024）universe 上以真實 WFA OOS 重驗。

結果（fixed config `quarterly / lookback 60 / foreign`，span 2010-2024、3681 bars）：

| Universe（每季 top-N by mcap, union）| 檔數 | 下市 | 全窗 CAGR | 全窗 Sharpe | WFA median OOS | OOS>0 | landscape PBO | DSR | 判決 |
|:--|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| top-40（大型股）| 78 | 3 | 20.6% | 1.36 | 1.54 | 84% | 42.9% | 1.00 | REAL |
| top-200（廣）| 423 | churning | 16.2% | 1.17 | 1.48 | 89% | 42.9% | 1.00 | REAL |
| _ADR-024 ref（116, 76 下市）_ | _116_ | _76_ | _13.1%_ | _0.90_ | _1.30_ | _42.9%_ | _—_ | _(pre-ADR-025 binary NO-GO)_ |

**發現**：

1. **以市值選 universe 本身即帶生存者偏誤**。top-40-by-mcap 挑最大市值、幾乎不下市（3/78 下市）→ CAGR 20.6% ≈ 舊 ADR-024「40 檔 18.9%」的存活數字。放寬到 top-200（423 檔、含 churning 中型段）降到 16.2%，趨向 ADR-024 誠實的 13.1%。**絕對 CAGR 隨 universe 而變**——sizing 應用廣義/誠實數字（~16%），非大型股 20%。
2. **ADR-025 真偽判決對 universe 廣度穩健**。78 檔與 423 檔都回 REAL：WFA median OOS Sharpe 穩在 ~1.5、OOS>0 ≥84%、DSR ≈1.00。判決靠 **pre-registered OOS 廣度 + deflated DSR**，非隨 universe 漂移的絕對 CAGR。
3. **landscape PBO 42.9% 精確重現**（同 ADR-024 的 116 檔）——ADR-025 論點獲實證：landscape PBO 量的是 config-selection 過擬合，對單一 pre-registered config 應正確忽略（該 config 由 OOS + DSR 判）。pre-ADR-025 殺 inst_flow 的 binary-PBO 是錯的測試。

**結論（當時）**：inst_flow paper-ready，在誠實全 FinLab survivorship-clean 資料上確認（非只是 10-survivor cache 的樂觀值）。因子有真實、OOS 穩健的 edge（median OOS Sharpe ~1.5、DSR ≈1.0），跨 universe 定義皆成立；絕對 CAGR（16-20%）視 universe 廣度而定。

> 此輪的 REAL 已被 2026-07-02 的權威判決標記為「現行程式路徑無法重現」——其 universe 建構器（`inst_flow_revalidate_finlab`）需經 sub-project ② / ADR-032 平台化後重跑才有效。

---

## 2026-06-14 · 兩段閘首度真偽判決 → 🟢 REAL（舊數學，首個 paper-ready 候選）

- **背景**：binary ADR-016 曾判資金流 NO-GO（ADR-024：survivorship-clean CAGR 13.1% < 18%、landscape PBO 42.9% > 30%）。本輪把**同一份 survivorship-clean 數據**餵 ADR-025 真偽閘——對 pre-registered fixed config，landscape PBO 不適用，真偽改由 OOS breadth + DSR 判。
- **設定（pre-registered，誠實）**：固定 config（事前鎖死，不逐 fold / 不從 sweep 選）`quarterly / lookback=60 / foreign net-buy`；survivorship-clean universe 116 檔（survivors + 下市，point-in-time）；DSR 誠實去偏 `n_trials=24`（研究實際掃過的 config landscape）。

結果：

| 真偽閘判準 | 值 | 門檻 | 判 |
|:--|:--|:--|:--:|
| survivorship-clean | 116 檔（含下市）| 強制 | ✅ |
| WFA OOS>0 比例 | 83%（12 folds，median OOS 1.30）| ≥ 60% | ✅ |
| landscape PBO | 42.9% | — | 忽略（pre-registered，PBO 量的是選股過擬合）|
| DSR（deflated, n_trials=24）| 0.982 | ≥ 0.95 | ✅ |
| K3 滑點 Sharpe（+0.3%/leg）| 0.90 | > 0 | ✅ |

WFA OOS 逐 fold：1.62 / 1.80 / 0.69 / −0.25 / 1.57 / 0.83 / 2.63 / 0.94 / −0.51 / 1.03 / 2.57 / 2.14（10/12 > 0）。fixed config full-span：CAGR 13.1% / Sharpe 0.90。

**為什麼 binary 殺它、兩段閘救它（且非放水）**：binary 死於絕對 CAGR 13.1% < 18%（市場中性報酬被絕對門檻錯殺）+ landscape PBO 43%（量錯對象）。兩段閘救回的依據是 DSR 0.982（扣掉 24-config 選擇偏誤後的誠實機率，仍過 0.95）+ OOS>0 83% ≫ 60% + K3 撐住；landscape PBO 對事前鎖死的單一 config 不適用（ADR-025 §3.1）。

**與既有 NO-GO 不矛盾**：動能/多因子/long-short 仍 NO-GO（selected config、landscape PBO 0.43-0.77，死於真偽閘 PBO 檢查）。資金流獨特處：唯一有「pre-registered fixed config + survivorship-clean WFA median OOS 1.30」的候選。

> ⚠️ Caveat（當時已標）：仍是 backtest 證據；DSR 0.982 vs 0.95、12 folds 有 2 負，margin 不寬。此結果＝「值得 paper」，非「上 25%」。此 DSR 係 ADR-030 修正前的舊數學。

---

## 判決過程記錄（2026-07-02 平台化重驗）

ADR-029 刻意延後的 universe 建構器已由 [ADR-032](./adrs/ADR-032-survivorship-universe-workflow.md) 重建為平台工作流（`build-universe` CLI/HTTP、`TruthGateConfig.parquet_dir`、inst_flow 宣告跟著 cache 證據走）。重驗用磁碟上仍存活的 2026-06-15 ingest 快取（`data/parquet_finlab_universe`，423 檔含下市股），經三步收斂到最終判決：

1. **fallback REJECTED**（40 檔 survivor-only `_WIDE`）：DSR 0.789、WFA OOS+ 33%、survivorship hard-fail——修正閘拒絕自欺宣告的正確行為。
2. **免成本 REAL（作廢）**：423 檔重驗初判 REAL（DSR 0.970），但 `slippage_sharpe` 與 `sharpe_is` 到小數點後 16 位完全相同 → 追出模擬器判決級 bug：rebalance 段重疊 + `groupby.first()` 去重把 lump 交易成本列系統性吞掉——panel 策略歷史數字全屬免成本高估、K3 壓力為靜默 no-op。**2026-06-15 的舊 REAL（同一 backtest 函式）同屬免成本假陽性。**
3. **真實成本 REJECTED（最終）**：修復（`strategies/common/mechanics.trim_overlap` + `_add_slippage` 契約化，PR #148）後重跑 → 成本吃掉 ~0.19 Sharpe，DSR 0.970→0.908 跌破 0.95。

歷史 NO-GO 判決（動能/多因子/long-short）在真實成本下只會更 NO-GO，不翻案。本記錄同時是審判庭第三次抓出假陽性的存證（四層共振 → 免 survivorship inst_flow → 免成本 inst_flow）——「驗證信心」護城河的實戰證據。
