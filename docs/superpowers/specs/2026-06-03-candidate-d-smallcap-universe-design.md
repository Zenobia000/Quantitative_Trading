# 候選 D 設計 spec — 中小型動能 universe 換池 + 雙窗口 IS 驗證

> ⚠️ 本文件主題（四層共振）已於 ADR-023 判負 edge 廢止，僅存 audit trail。

> **狀態：** 設計定稿 / 待資料 spike 解鎖後實作
> **日期：** 2026-06-03
> **觸發：** [[ADR-017]] §5「重新定義 edge 與 universe（large-cap 可能非目標，考慮中小型動能股）」+ [[ADR-019]] §3「誠實退場 → 回 M0 換 edge 來源」+ 16 WBS R9「escalate：換中小型動能 universe 候選 D」
> **前置：** v3 進場重設（[[ADR-019]]）已實作且 large/mid-cap 雙窗 IS 判 FAIL（機制無 edge）
> **決策授權：** 使用者授權「根據 WBS 規劃代為決策、適合節點 push」（2026-06-03）
> **相關：** `strategy/v2.md` §2.5（成本）、`dev_docs/21_data_contract.md` §2.1（資料來源）、ADR-016（gate KPI 凍結）

---

## 0. 一句話定調

四層共振 v3 的選股**機制不動**（scoring/signals/config 已釘死、v2 regression 保護），只把掃描的 **universe 從 10 檔權值大型股換成「中小型動能」股票池**，重跑雙窗口 IS，檢驗 [[ADR-019]] §2.1 的核心假說——**dir/chip 籌碼機制在中小型股才有鑑別力**（大型股法人流被稀釋、籌碼訊號無 edge）。

**核心紀律（承 [[ADR-019]] §2.4，不可鬆動）：**
- universe 採 **point-in-time 規則建構**（每個 rebalance 日只用當下可得資訊選股），杜絕 survivorship / look-ahead bias——否則 IS 結果不能當證據。
- 機制凍結：v3 六參數、scoring 四層、`strong_buy_threshold=5` 等全程不動（只換 universe + 校成本）。
- 雙窗口 IS 非 OOS；綠燈只代表「值得進 v0.2 OOS」非「有 edge」。
- 進場數是參與度非 edge；中段進場 <30% / 平均持有 ≥6 / churn <20% 操盤手體檢同步看。

---

## 1. Architecture — 換池發生在哪一層

策略三層（scoring 四層分數 / signals 進出場 gate / config 參數）**完全不動**。候選 D 是**資料層 + 選股池**的事，改動集中在「universe 怎麼產生」這條鏈：

| 層 | 現況 | 候選 D 改動 |
|:--|:--|:--|
| Universe 來源 | `finmind_bundle.DEFAULT_UNIVERSE`＝10 檔手列大型股；可由 `UNIVERSE_FILE` / `UNIVERSE_FINMIND` env 覆寫 | **新增 point-in-time universe builder**：輸入歷史市值/流動性 → 輸出每季成分清單（含已下市股） |
| 資料 ingest | `ingest_universe` 抓 OHLCV→parquet | universe builder 產出的清單餵入既有 ingest（管線不變，只是清單變 ~250 檔） |
| 法人/籌碼資料 | 10 檔大型股已有 FinMind 法人 + FinLab 進階券商分點 | **~250 檔中小型股需補齊三組資料**（見 §3 資料 spike，gating） |
| 策略 | v3 機制 | **不動**（同一份 config/scoring/signals） |
| 成本 | `cost_round_rate=0.671%`、`edge_ok=1.271%`（大型股校準） | **重新校準**（中小型 slip 上調 + 0.2% buffer，見 §4） |

**為何只換 universe 不動機制：** [[ADR-019]] §3 已定「誠實退場 → 問題在 hypothesis 不在進場閘 → 回 M0 換 edge 來源」。換 universe 是「換 edge 來源（標的 alpha）」的最小變動，保留機制可追溯、可對照（同一機制兩個池子的 IS 直接可比）。

---

## 2. Universe 定義 — point-in-time 規則建構

### 2.1 選股規則（決策定稿）

每個 rebalance 日 `t`，只用 `t` 當日及之前可得的資料，依序套用：

1. **排除權值股**：剔除市值排名前 50（清掉台積電那類權重股，這是大型股池已證無 edge 的部分）。
2. **市值帶**：取市值排名 **51–300 名**（約 250 檔）為母集——「中型偏小」的標準操盤定義：夠小到籌碼有鑑別、又夠大到買得進賣得出。
3. **流動性下限**：剔除近 20 日**日均成交金額 < 2,000 萬 TWD** 的股票（避免回測假成交 / 過度樂觀的滑價假設）。
4. **動能排序（可選收斂）**：若母集仍過大，按過去 6 個月報酬率排序取前 N（先驗 N＝母集全取，不另設動能門檻，避免雙窗 in-sample 調參；動能濾網列為 v0.2 sweep 候選）。
5. **rebalance 頻率**：**每季**（季初依當時資料重選），季中不動成分。

> **凍結（v0.1 不調）：** top-50 排除、51–300 帶、2,000 萬流動性門檻、季 rebalance。任何在雙窗 IS 內調這些＝ in-sample 調參，禁止。

### 2.2 反 survivorship / look-ahead 三鐵律

1. **含已下市股**：每個 rebalance 日的成分必須包含「當時存在、之後才下市」的股票，否則只選到幸存者＝高估報酬。builder 需吃 point-in-time 上市/下市狀態。
2. **只用過去資訊**：市值、流動性、動能皆以 `t` 當日及之前計算，禁用未來資料定義過去的池子。
3. **成分留痕**：每季成分清單落檔（`universe_membership__{YYYYQ}.csv`），IS 結果可重現、可審計。

---

## 3. 資料依賴與可得性 spike（GATING — 做任何實作前先過）

候選 D 的 make-or-break。策略每檔需三組資料（`is_harness.load_merged_parquet`）：

| 資料組 | 欄位 | 來源 | 中小型 ~250 檔 / 2015+ 可得性 |
|:--|:--|:--|:--|
| OHLCV | open/high/low/close/volume | FinMind `taiwan_stock_daily` | 多半可得（**spike 驗**）|
| 三大法人 | foreign_buy / trust_buy / dealer_buy | FinMind `institutional_investors_trading_summary` | 多半可得（**spike 驗**）|
| **券商分點籌碼** | top_broker_buy / key_broker_buy | **FinLab 進階方案（付費）** | **未知——最大風險**（成本 + 小型股覆蓋 + 2015 回溯）|
| 市值 / 上市狀態 | market_value / 上市日 / 下市日 | FinMind `taiwan_stock_info` + 市值 dataset | **需確認**（point-in-time builder 的輸入）|

**spike 任務（需使用者提供 FinMind token + FinLab 進階授權）：**
- 抽樣 20 檔中小型股，驗三組資料 2015-01 ~ 2024-12 的**覆蓋率 + 缺漏型態**。
- 特別確認：**FinLab 進階券商分點對小型股 + 2015 回溯的覆蓋與單次抓取成本**。
- 確認市值 / 上市下市 dataset 能餵 point-in-time builder。

**spike 結論分支：**
- 🟢 三組資料中小型覆蓋足 → 進 §8 實作。
- 🔴 券商分點對小型股覆蓋不足 / 成本不可行 → **機制的 chip 層在候選 D 失效**，候選 D 不成立 → 回 M0 評估「去 chip 層的機制變體」或砍策略（[[ADR-017]] §5 退場路徑）。

---

## 4. 成本重新校準（中小型）

[[ADR-019]] §2.5 已預告「0.2% buffer 及中小型 slip 上調留換 universe 時處理」＝現在。

| 項 | 大型股（現況） | 中小型（候選 D 先驗值） |
|:--|:--|:--|
| 手續費 + 證交稅 round | 0.671% | 0.671%（不變）|
| 滑價 buffer | 0%（code 未含）| **+0.2%×2 = 0.4%**（[[ADR-019]] §2.5 預告）|
| 流動性滑價 | 內含於 K3 壓測 0.3% | **K3 壓測上調至 0.5%**（小型股衝擊成本）|

→ `edge_ok` 門檻同步上抬。**先驗值，不在雙窗 IS 調**；實際滑價分布待 spike 的成交金額資料校準。

---

## 5. 預登記 hypothesis（RunConfig 強制欄）

> **H-D：** 四層共振 v3（dir/chip 必含、機制凍結）套用於 point-in-time 中小型動能 universe（市值 rank 51–300、季 rebalance、流動性 ≥2000 萬），在 2015-2020 與 2020-2024 **雙窗口 IS 皆**達 ADR-016 gate（K1 CAGR>18% / K2 Sharpe>1.0 / K3 滑點 0.5% 下 Sharpe>1.0 / min_trades），**且**「含 chip 背書」邊際單 fwd5 報酬顯著優於「丟 chip」反事實組——證實 dir/chip 機制在中小型的鑑別力。

falsifiable：雙窗任一 FAIL、或符號不一致、或 chip 反事實無差異 → 假說駁回。

---

## 6. 反過擬合硬約束（承 [[ADR-019]] §2.4）

- v0.1 候選 D **只跑一組先驗預設、不在雙窗 IS sweep**（universe 規則 + 成本 + 機制全凍結）。
- 進場數 >40 嚴禁當成功指標，只當樣本健全下限（30–80 筆/股/5 年）。
- 操盤手體檢：平均持有 ≥6 bar、中段進場 <30%、churn <20%。
- 凍結清單：v3 六參數 + scoring 四層 + universe 四規則 + 成本三項，全程不動。

---

## 7. 誠實退場判準（candidate D 的紅線）

| 結果 | 判決 | 下一步 |
|:--|:--|:--|
| 雙窗皆 PASS + chip 反事實有差異 + 體檢過 | 🟢 機制在中小型有 edge | 進 v0.2 OOS（[[ADR-019]] 流程）|
| 雙窗符號不一致 / 邊際單劣化 / 體檢不過 | 🔴 中小型也無一致 edge | 回 M0：問題在 hypothesis 本身，評估重訂 edge 或砍策略 |
| 券商分點資料不可得（§3 spike 🔴）| 🔴 機制 chip 層無法在候選 D 落地 | 回 M0：評估去 chip 機制變體或砍 |

**綠燈≠有 edge，只代表值得進 OOS。** 紅燈即依 [[ADR-017]] 退場路徑回 M0，不續換池自欺。

---

## 8. 實作單元與檔案結構（spike 🟢 後）

| 單元 | 檔案 | 職責 |
|:--|:--|:--|
| Universe builder | `src/backtest_platform/data/universe_builder.py`（新）| point-in-time 規則 → 每季成分清單（純函式，吃市值/流動性/上市狀態 DataFrame，吐 `{季: [stock_id]}`）|
| 成分落檔 | 同上 | `universe_membership__{YYYYQ}.csv` 留痕 |
| 成本 preset | `config/strategy_config.py` | 新增中小型成本 preset（不動 v2/v3 機制參數）|
| IS 串接 | `research/is_harness.py` | universe builder → ingest → 雙窗 run_is（既有管線，只換清單來源）|
| 測試 | `tests/data/test_universe_builder.py`（新）| 合成資料 TDD：含下市股、point-in-time 不洩漏未來、流動性門檻、季 rebalance、成分留痕 |

universe builder 可**純合成資料 TDD（hermetic）**，不需真實資料即可完成並釘死正確性；真實 IS 待 §3 spike 提供資料。

---

## 9. 執行計畫（spike-gated）

1. **本 spec + ADR-020 草案**（本次，docs-only，可 commit/push）。
2. **資料 spike**（需使用者 token）→ 結論決定 go/no-go。
3. 🟢 後：universe builder TDD 實作（hermetic）→ commit。
4. 中小型成分 ingest（需資料）→ 雙窗 IS run → gate review → ADR-020 補實證 + 判決。
5. 文件同步：16 WBS R9 / 候選 D 狀態、21 資料契約（市值/上市狀態 dataset）、ADR-020。

---

## 10. 風險

| 風險 | 等級 | 緩解 |
|:--|:--|:--|
| 券商分點付費資料對小型股覆蓋不足 / 成本爆 | 🔴 致命 | §3 spike 先驗；不足即退場，不硬上 |
| point-in-time 市值/下市資料難取 → survivorship 漏洞 | 🟠 高 | builder 強制吃上市狀態；取不到則 universe 規則降級並在 IS 結果明確標 bias 警語 |
| 中小型滑價遠超先驗 0.5% → 實務無法執行 | 🟠 高 | 用 spike 成交金額分布校準；流動性門檻可上調 |
| 換池仍無 edge（機制本身無 alpha）| 🟡 中 | 這正是 IS 要回答的；紅線退場路徑已定（§7），不續換池自欺 |

---

## 附：本 spec 自審

- [x] 無 TBD / 佔位；資料 spike 的未知明確標為 gating 風險而非佔位
- [x] 內部一致：機制凍結貫穿 §1/§6/§8；反 survivorship 貫穿 §2.2/§8/§10
- [x] scope 聚焦：單一可實作單元（換 universe + builder），未夾帶無關重構
- [x] 無歧義：universe 四規則給定具體數值（51-300 / 2000萬 / 季）；退場紅線三分支明確
