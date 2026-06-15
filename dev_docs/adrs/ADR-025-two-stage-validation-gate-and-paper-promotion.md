# ADR-025: 驗證閘兩段化（真偽閘 + 配置閘）+ Paper 前移 — 修正 ADR-016 binary 通關

> **狀態：** 已接受 | **日期：** 2026-06-14 | **決策者：** Self
> **修正（amends）：** [ADR-016](./ADR-016-m2-acceptance-kpi-freeze.md)（M2 KPI binary 凍結）— 本 ADR 即 ADR-016 §4「Sharpe 落在 0.9-1.0 → 評估是否放寬（需新 ADR）」預埋觸發的回應
> **相關：** [ADR-018](./ADR-018-monitoring-to-research-loop-pivot.md)（gate machine / trials→DSR / 晉升狀態機）、[ADR-023](./ADR-023-momentum-no-go-hold-gate.md)（動能 NO-GO）、[ADR-024](./ADR-024-institutional-flow-candidate-strategy.md)（資金流 NO-GO）、[ADR-022](./ADR-022-multi-strategy-fleet-operations.md)（艦隊營運）

---

## 1. 背景與問題

ADR-016 把 M2 acceptance 凍結成三條 **binary 絕對門檻**（K1 CAGR>18% / K2 Sharpe>1.0 / K3 滑點 0.3% 下 Sharpe>1.0），任一不過即觸發退場回 M0。R9（策略 edge）以此為唯一判準，連續驗了 4 個獨立結構：

| 結構 | survivorship-clean 結果 | binary 判 |
| :--- | :--- | :--: |
| 動能（12-1）| OOS 0.63-0.86 / PBO 高 | 🔴 NO-GO（ADR-023）|
| 三大法人資金流 | CAGR 13.1% / Sharpe 0.90 / 全 landscape PBO 42.9% | 🔴 NO-GO（ADR-024）|
| 多因子等權組合 | CAGR 13.2% / Sharpe 0.91 / PBO 77% | 🔴 NO-GO |
| 多因子 long-short（dollar-neutral）| CAGR 10.5% / Sharpe 0.87 / PBO 46% | 🔴 NO-GO |

收斂結論被表述為「**台股大/中型 + 免費資料 + 嚴格 ADR-016 下不存在可部署 edge**」，並進一步推導出「平台已無可往下開發的部分，前端（v0.4）/ paper（v0.5）/ 實盤（v1.0）全 gated 於 edge」。

**問題：以交易系統實務檢視，binary 絕對門檻框架本身有三個設計缺陷，把「策略沒過部署門檻」錯誤放大成「整個專案 blocked」。**

### 缺陷 A — 部署閘與研究迭代閘被混用

真實 quant 營運裡這是兩個不同的閘：**部署閘**守真實資金（該死嚴）、**研究迭代閘**根本不該存在（研究本來就持續流動）。ADR-016 的 binary 門檻被同時拿來當「研究是否繼續」的開關 → 一個候選沒過就宣告專案停擺。但研究平台砍掉 4 個假 edge 是它在**正常工作**，不是被卡住。

### 缺陷 B — 絕對 CAGR 門檻與市場中性策略錯配

K1（CAGR>18% 含 +3% 生存者 buffer）是**絕對單策略報酬門檻**。long-short 刻意拿掉 beta 做 dollar-neutral（CAGR 因此掉到 10.5%，「拿掉的 beta 是正 carry」），再被 K1 判死。但市場中性策略的價值不在絕對 CAGR，而在**低相關性 + 可槓桿 + 可組合**——一個 0.9 Sharpe、對大盤近零相關的 sleeve 在多策略組合裡是可部署的。用 standalone 18% CAGR 量一個故意放棄 beta 的策略，是判準與策略類型錯配。

### 缺陷 C — Gate 排序造成死鎖

ADR-016 + Roadmap 鐵律「edge 未證實前不接 paper/broker」造成：

```
不能上 paper  ←── 因為 backtest 沒過絕對門檻
backtest 永遠補不齊 OOS 真相  ←── 因為不准上 paper 收 live 資料
```

倒因為果。**Live OOS 是品質最高的驗證資料**，paper trading 本身就是驗證機制一環，卻被排在 backtest 絕對門檻之後，形成自鎖。

---

## 2. 考量的選項

### 選項一：維持 ADR-016 binary（現狀）
- **描述**：保留三條絕對門檻為唯一通關判準
- **優點**：先驗、不可事後合理化、零變更
- **缺點**：缺陷 A/B/C 不解 → 「專案 blocked」框架錯誤持續、市場中性策略永遠錯配、死鎖無解
- **拒絕**：把研究引擎誤當單策略容器

### 選項二：單純放寬數字（如 Sharpe>0.9 / CAGR>15%）
- **描述**：藉機調鬆門檻
- **優點**：最快讓邊緣候選「過關」
- **缺點**：(1) 違反 ADR-016 先驗原則、(2) 仍是 binary、(3) 治標不治本（缺陷 A/B/C 一個都沒解）、(4) 易淪為自欺
- **拒絕**：放水不是修正

### 選項三：驗證閘兩段化 + Paper 前移 ★採納
- **描述**：把單一 binary 閘拆成「真偽閘（防自欺，binary hard-fail）」+「配置閘（決定 size，連續）」，並把 paper 前移到真偽閘之後而非絕對門檻之後
- **優點**：對齊真實 quant 實務（過真偽閘的策略**配置 size**而非淘汰）、解三缺陷、保留 ADR-016 的統計嚴謹度於真偽閘
- **缺點**：配置閘需新定義 sizing 函數（工作量）；放寬若無紀律會自欺（緩解：真偽閘必須更硬、survivorship-clean 強制）

---

## 3. 決策

**採納選項三。** ADR-016 的三條門檻不廢，而是**重新定位**到兩段閘的對應層級。

### 3.1 真偽閘（Truth Gate）— 防自欺，binary hard-fail

唯一目的：擋掉過擬合 / 生存者膨脹的假陽性。**沒過 = 假的，直接砍，配置閘根本輪不到。**

| 判準 | 門檻 | 適用 |
| :--- | :--- | :--- |
| **survivorship-clean** | 含下市股 point-in-time universe（強制）| 全部 |
| **選股過擬合 PBO** | < 30%（CSCV）| **以 IS 從 sweep 選 config 的策略** |
| **單一 pre-registered config OOS** | WFA OOS Sharpe > 0 比例 ≥ 60% + DSR-deflated 過門檻 | **hypothesis 預登記、不重選 config 的策略** |
| **K3 滑點穩健性** | 0.3% per-leg 下 OOS 不崩號 | 全部 |

> **關鍵區分（缺陷 B 的精修）**：PBO 衡量的是「**從 sweep 選 config**」的過擬合。對一個 **pre-registered（hypothesis 鎖死、不重選）** 的單一 config，landscape PBO 不適用於否定它——該用「OOS>0 比例 + trials-deflated DSR」（ADR-018 trials→DSR）判其真偽。這把 ADR-024 資金流 fixed-config 的「WFA median OOS 1.30 但 landscape PBO 43%」正確拆開：landscape 過擬合 ≠ 該 pre-registered config 無效。

### 3.2 配置閘（Sizing Gate）— 決定資金，連續非二元

過真偽閘的策略**不是 yes/no，而是按風險預算映射到倉位**：

- **主判準**：risk-adjusted（OOS Sharpe）、與現有艦隊相關性、容量（capacity）
- **絕對 CAGR（原 K1）降為參考**，尤其市場中性策略改看**對組合的邊際貢獻**（diversification）而非 standalone CAGR
- **Sharpe 0.9 不是淘汰線而是小倉位線**：高 Sharpe → 大 size、低（但真）Sharpe → 小 size、零相關 sleeve → 給配置以拉組合 Sharpe

### 3.3 Paper 前移

**過真偽閘 + OOS Sharpe > 0 即可用最小倉位進 paper**，收 live OOS 作為下一級驗證資料——不再排在絕對 CAGR 門檻之後。Paper 結果（執行摩擦、容量、實際 OOS）回饋配置閘調整 size 或退場。

### 3.4 對 R9 既有結論的影響（誠實聲明）

**本 ADR 不翻案 ADR-023 / ADR-024 的 NO-GO，也不放水救死策略：**

| 結構 | 在新框架下 | 結果 |
| :--- | :--- | :--- |
| 動能 / 多因子組合 / long-short | PBO 43-77%（landscape）或 OOS 不過 | **死在真偽閘**，NO-GO 不變 |
| 資金流 fixed-config | survivorship-clean WFA median OOS **1.30**（pre-registered、不重選）、survivorship-clean | **可能過真偽閘**（PBO 屬選股過擬合、不適用於此 pre-registered config）→ 進配置閘 → **進 paper 收 live OOS** |

> 新框架**真正改變的不是讓死策略復活**，而是：(1) 解除「專案 blocked」框架錯誤，研究/開發工具持續運轉；(2) 修正 gate 排序死鎖，未來過真偽閘的候選直接進 paper；(3) 修正絕對 CAGR 對市場中性策略的錯配；(4) 把資金流 pre-registered fixed-config 從「被 landscape PBO 連坐」中釋放，成為**第一個可進 paper 的具體候選**。

---

## 4. 後果

### 正面
- **解死鎖**：研究前端（v0.4）/ paper（v0.5）脫離 binary edge-gate；「平台已無可開發部分」結論被修正為「平台持續運轉、研究迭代不停」
- **對齊實務**：配置（sizing）取代淘汰（binary），符合真實 quant book 的 risk-budget 配置
- **具體下一步**：資金流 fixed-config（survivorship-clean WFA OOS 1.30）可進 paper，收最高品質的 live OOS 證據
- **保留嚴謹**：真偽閘把 ADR-016 的統計防自欺（PBO/DSR/WFA/survivorship-clean）全數承接並強化（survivorship-clean 升為強制）

### 負面 / 風險
- 配置閘需定義 sizing 函數（新工作；疊在 24 風控 spec + 8.G gate_machine）
- 放寬若無紀律 = 自欺。**緩解**：真偽閘 hard-fail 不可繞、survivorship-clean 強制、pre-registered config 必須真的事前鎖死（hypothesis 系統鎖，ADR-018 8.G.2-full）
- paper 最小倉位仍有時間 / 執行成本；live OOS 需數月才有統計意義

### 影響範圍
- `dev_docs/16_wbs_development_plan.md`：§1 banner、§4 ADR 計數、§5 R9 列、§6 版本 Roadmap edge-gated 框架（paper 前移）
- `dev_docs/INDEX.md`：ADR-025 row + 更新 banner
- `validation/gate_machine.py`：`ValidationGate` 拆 `TruthGate`（binary）+ `SizingGate`（連續）兩段（後續實作工項）
- `24_risk_management_spec.md`：配置閘 sizing 函數（倉位 = f(Sharpe, 相關性, capacity)）
- 7.A PaperBroker：接「過真偽閘」候選的 paper 前移路徑

### 重新評估觸發
- 配置閘 sizing 函數實跑後發現無法穩定 size → 回退檢視
- 資金流 fixed-config paper 期 live OOS 崩號 → 退場（真偽閘事後否決）
- 出現第三家 edge family 同樣 pre-registered OOS 強但 landscape PBO 高 → 驗證本框架的可重複性

---

## 5. 執行計畫

1. ✅ **本 ADR**：兩段閘 + paper 前移定案
2. **WBS / INDEX 同步**（本 PR）：Roadmap edge-gated 框架改寫、R9 列補新框架、ADR 計數
3. **gate_machine 拆兩段**（後續）：`TruthGate`（survivorship-clean + PBO/OOS/DSR hard-fail）+ `SizingGate`（Sharpe/相關性/capacity → 倉位）
4. **配置閘 sizing 函數 spec**（24 §疊加）：定義 risk-budget 倉位映射
5. **資金流 fixed-config 進 paper**（7.A）：survivorship-clean pre-registered config 收 live OOS；paper 報告回饋配置閘

---

| 日期 | 審核人 | 備註 |
| :--- | :--- | :--- |
| 2026-06-14 | Self | 初版 — 修正 ADR-016 binary 通關為真偽閘 + 配置閘兩段 + paper 前移；不翻案 ADR-023/024（死於真偽閘），解專案 blocked 框架錯誤 |
