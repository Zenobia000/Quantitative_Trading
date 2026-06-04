# ADR-020: 候選 D — escalate 至中小型動能 universe 換池驗證

> **狀態：** 提案中（設計定稿，實證 go/no-go 待資料 spike）| **日期：** 2026-06-03 | **決策者：** Self（使用者授權「根據 WBS 規劃代為決策、適合節點 push」）
> **相關：** [ADR-017](./ADR-017-m2-is-gate-failed-return-to-m0-entry-redesign.md)（§5 退場路徑：重定義 edge 與 universe）、[ADR-019](./ADR-019-v3-entry-redesign-relaxation-and-minimal-exit-pairing.md)（v3 機制定稿 + §3 誠實退場）、[ADR-016](./ADR-016-m2-acceptance-kpi-freeze.md)（gate KPI）、[16 WBS R9](../16_wbs_development_plan.md)、設計 spec：`docs/superpowers/specs/2026-06-03-candidate-d-smallcap-universe-design.md`

---

## 1. 背景與問題

[[ADR-019]] v3 進場重設後，四層共振對 large/mid-cap 10 檔 universe 跑雙窗口 IS——兩窗、兩方向（v3.1a/v3.1b）皆**無強跨窗 edge**（最佳僅 2020-2024 +1.23%/Sharpe 0.41，離 K1 18%/K2 1.0 甚遠；2015-2020 仍負）。診斷收斂：**進場閘已非 bottleneck（dirB 進場乾淨），標的 alpha 不足**。

[[ADR-019]] §3 與 16 WBS R9 的退場路徑明定：問題在 hypothesis / edge 來源，不在進場閘 → **回 M0 換 edge 來源**。三選項：(a) 換中小型動能 universe（候選 D）、(b) 重訂 edge、(c) 砍策略。本 ADR 記錄選 (a) 的決策與設計。

## 2. 決策

**escalate 至候選 D：機制凍結，只把 universe 從大型股換成 point-in-time 中小型動能股票池，重跑雙窗口 IS。** 檢驗 [[ADR-019]] §2.1 核心假說——**dir/chip 籌碼機制在中小型才有鑑別力**（大型股法人流被稀釋、L2⊂L3 籌碼訊號無 edge；中小型「技術突破但法人不認帳」的假突破靠 chip 層擋得住）。

### 2.1 universe 規則（point-in-time，反 survivorship）

- 市值 rank **51–300**（排除前 50 權值股）、季 rebalance、近 20 日日均成交 ≥2,000 萬 TWD。
- 每個 rebalance 日只用當下可得資訊選股、**含已下市股**、成分留痕。
- 詳見設計 spec §2。

### 2.2 機制與成本

- **機制凍結**：v3 六參數 + scoring 四層 + `strong_buy_threshold=5` 等全不動（換 universe 是換 edge 來源，非調機制）。
- **成本上調**（[[ADR-019]] §2.5 預告的中小型校準）：+0.2%×2 buffer、K3 滑點壓測 0.3%→0.5%。

### 2.3 反過擬合（承 [[ADR-019]] §2.4）

v0.1 候選 D 只跑一組先驗預設、不在雙窗 IS sweep；進場數非 edge；綠燈只代表值得進 OOS。

## 3. 資料依賴（GATING）

策略每檔需 OHLCV（FinMind）+ 三大法人（FinMind）+ **券商分點籌碼（FinLab 進階方案，付費）**。候選 D 的 make-or-break＝**~250 檔中小型股、回溯 2015 的券商分點資料覆蓋與成本**，加上 point-in-time 市值/上市下市資料。

**先跑資料 spike（需 FinMind token + FinLab 進階授權）**：抽樣 20 檔驗三組資料 2015-2024 覆蓋；🔴 不足即候選 D 不成立，回 M0 評估去 chip 機制變體或砍。

## 4. 後果

- 正面：機制不動使「同機制兩個池子」的 IS 直接可比；universe builder 為可重用平台件（point-in-time 選股，未來其他策略也用得到）。
- 成本：需付費券商分點資料 + 數小時 ingest；point-in-time 市值/下市資料取得難度未知。
- 風險：換池仍無 edge（機制本身無 alpha）——這正是 IS 要回答的；紅線退場路徑已定（spec §7），不續換池自欺。

## 5. 執行狀態

1. ✅ 設計 spec（`specs/2026-06-03-candidate-d-smallcap-universe-design.md`）
2. ✅ 本 ADR 草案
3. ✅ **universe builder hermetic TDD**（2026-06-04，`data/universe_builder.py` + 14 合成測試）— spec §8 允許在資料 spike 前先建：point-in-time 選股 + 反 survivorship 三鐵律已釘死，與資料解耦。
4. ⏳ 資料 spike（需使用者 token）→ go/no-go。**前置診斷（免費）**：先用現有 FinMind 三大法人量化 chip 層邊際貢獻（IC / ablation），chip 無訊號即不買 FinLab，回 M0；有訊號才付費補券商分點。
5. ⏳ 🟢 後：成本 preset + 中小型 ingest → 雙窗 IS（既有 `run_is`）→ gate review → 本 ADR 補實證 + 升「已接受/已拒絕」

## 6. 待補（IS 跑完後）

- 雙窗口 IS 實證表（CAGR/Sharpe/K3 + chip 反事實對照）。
- gate review 判決：🟢 進 v0.2 OOS / 🔴 回 M0。
- 狀態 提案中 → 已接受（有 edge）/ 已拒絕（無 edge → 砍或重訂）。
