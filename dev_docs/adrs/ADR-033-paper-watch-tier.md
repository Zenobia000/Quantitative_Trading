# ADR-033: Paper-Watch 觀察艙 — 真偽閘新增零資本第三態，收 DSR ∈ [0.90, 0.95) 邊緣候選的 live OOS

> **狀態：** 已接受 | **日期：** 2026-07-02 | **決策者：** Self
> **擴充（extends）：** [ADR-025](./ADR-025-two-stage-validation-gate-and-paper-promotion.md)（驗證閘兩段化）— 本 ADR 在真偽閘的 REAL/REJECTED 二分之間新增 `PAPER_WATCH` 觀察艙態，**不改動 ADR-025 判準、不放寬 ADR-016 部署門檻**
> **相關：** [ADR-016](./ADR-016-m2-acceptance-kpi-freeze.md)（DSR ≥ 0.95 部署門檻，維持不變）、[ADR-024](./ADR-024-institutional-flow-candidate-strategy.md)（inst_flow 候選）、[ADR-030](./ADR-030-truth-gate-judgement-fix.md)（審判庭數學修正）、[ADR-032](./ADR-032-survivorship-universe-workflow.md)（survivorship universe 工作流）

---

## 1. 背景與問題

### 1.1 inst_flow 的判決形狀 — 「證據不夠強」非「假 edge」

inst_flow 在 survivorship-clean 平台化重驗（ADR-032 工作流 + 423 檔含下市 universe + 2010→2024 全史 + OOS holdout 2021→2024）並修復模擬器成本吞噬 bug（PR #148）後，於**真實交易成本**下的最終判決為 REJECTED：

| 真偽閘條款 | 值 | 門檻 | 判 |
| :--- | :--- | :--- | :--- |
| survivorship_clean | True（cache 證據）| hard | ✓ |
| pre_registered | True（fixed config 事前鎖死）| hard | ✓ |
| WFA OOS+ 廣度（5 folds）| **100%** | ≥ 60% | ✓ |
| OOS holdout Sharpe（2021-2024 封存段）| **0.892** | > 0 | ✓ |
| K3 滑價壓力 Sharpe（+0.3%/leg）| **0.846** | > 0 | ✓ |
| DSR（n_trials=16 通縮）| **0.908** | ≥ 0.95 | ✗ |

**唯一 fail 條款是 DSR 通縮顯著性**（0.908 < 0.95）。所有 hard-fail 條款全過——資金流 edge 方向真實（OOS 廣度 100%、封存段為正、K3 撐住），但強度不足以在 16 次試驗通縮後跨越 0.95 部署檻，回到「~0.9 Sharpe 牆」。這是「**證據不夠強**」的形狀，不是「假 edge」——與動能/多因子/long-short 死於 landscape PBO 或 survivorship 的假陽性形狀本質不同。

### 1.2 唯一能補強的資料是 live OOS — 重演 ADR-025 缺陷 C 的死鎖

DSR 0.908 想補到 0.95，唯一誠實的路徑是**更多樣本外證據**。但 backtest 樣本外已用盡（全史 + 封存 holdout 都跑過），唯一未取用的 OOS 是**未來的 live 資料**。而在現行 binary 真偽閘下：

- 沒過真偽閘（REJECTED）→ 不准進 paper → 拿不到 live OOS → DSR 永遠補不上 → 永遠 REJECTED。

這正是 ADR-025 §背景所列**缺陷 C「gate 排序死鎖」**（沒 edge 不准 paper／不 paper 拿不到 live OOS）的重演——只是這次卡在 DSR 邊緣而非絕對 CAGR。inst_flow_truth_gate_verdicts.md 的結論段亦已預留「(b) 依 ADR-025 哲學討論『過 K3/OOS 但 DSR 邊緣』候選是否以極小倉位進 paper 收 live OOS（需新決策）」。本 ADR 即該新決策。

### 1.3 平台需要 paper 端到端實戰

平台的 paper 通道（`paper_replay` 工作流、晉升狀態機 draft→paper→live）至今無真實候選跑完整條晉升鏈路。一個「證據高但未達部署檻」的候選，正是驗證 paper 端到端管線的理想標的——且零資本下無任何資金風險。

---

## 2. 考量的選項

### 選項一：維持 binary REJECTED
- **描述**：真偽閘維持 REAL/REJECTED 二分，DSR < 0.95 一律 REJECTED、不准進 paper。
- **缺點**：把「證據不夠強」與「假 edge」一視同仁殺死，且製造 §1.2 的死鎖——邊緣候選永遠拿不到能翻案的 live OOS。與 ADR-025 揭示的缺陷 C 相同錯誤。**拒絕。**

### 選項二：直接放寬 DSR 門檻到 0.90
- **描述**：把 `DSR_MIN` 從 0.95 降到 0.90，讓 inst_flow 直接 REAL 並配置資本。
- **缺點**：這是**門檻購物（threshold shopping）**——因為一個候選差 0.042 就搬動部署門檻，等於用資本冒險換一次過關，正是 ADR-016 凍結門檻要防的自欺。0.95 的部署檻有其統計理由（max-of-N-trials 噪音基準下的高信心），不因單一候選而動。**拒絕。**

### 選項三（★採納）：Paper-Watch 觀察艙 — 零資本資訊收集通道
- **描述**：在真偽閘新增第三態 `PAPER_WATCH`。進艙硬條件＝**全部 hard-fail 條款通過** 且 **DSR ∈ [0.90, 0.95)**；進艙後**倉位恆 0.0**（零資本），只收 live OOS 觀察，3 個月到期。晉升條件不動——任何 sizing 仍需（含 live 證據重評後）完整過真偽閘 DSR ≥ 0.95。
- **優點**：把「證據不夠強」與「假 edge」誠實分開（前者觀察、後者殺死）；解 §1.2 死鎖而**不動部署門檻**（零資本 ≠ 放寬）；給 paper 管線一個真實端到端標的。這是**資訊收集通道，不是門檻放寬**。**採納。**

---

## 3. 決策

**採納選項三。** 在 `validation/two_stage_gate.py` 真偽閘的 REAL/REJECTED 之外新增 `PAPER_WATCH` 態。

### 3.1 進艙硬條件

以下**全部**成立才進艙，任一 hard-fail 不過 → 照舊 REJECTED（絕不進艙）：

1. `survivorship_clean == True`
2. `pre_registered == True`（DSR 路徑；selected config 走 PBO，不適用觀察艙）
3. `wfa_oos_positive_frac ≥ WFA_OOS_POSITIVE_MIN`（0.60）
4. `oos_holdout_sharpe > OOS_HOLDOUT_SHARPE_MIN`（0，若有提供）
5. `slippage_sharpe > SLIPPAGE_SHARPE_MIN`（0）
6. `dsr ∈ [PAPER_WATCH_DSR_MIN, DSR_MIN)` 即 **[0.90, 0.95)**

判決優先序：**REJECTED ≻ INCOMPLETE ≻ PAPER_WATCH ≻ REAL**。任一 hard-fail 條款 reject 即 REJECTED；任一必要指標缺失即 INCOMPLETE（不得進艙）；上述六條全過即 PAPER_WATCH；`dsr ≥ 0.95` 則 REAL（不變）。

### 3.2 零資本

`PAPER_WATCH` **不是** `is_real`，故 `evaluate_two_stage` 對其 `position_size` 恆為 `0.0`——無論 sizing 輸入多強。本通道永不產生資本配置；live OOS 在零倉位下收集。

### 3.3 艙位上限與觀察期

- 同時最多 **2** 個觀察艙位。
- **3 個月**觀察期，到期一次性結算：無新證據不得再入艙。

### 3.4 晉升條件不動

任何 sizing（含 live 證據重評後）仍需完整過真偽閘 **DSR ≥ 0.95**。觀察艙不是晉升捷徑，是重評前的證據累積期。晉升狀態機（`promotion_service` draft→paper→live）本身**不消費**真偽閘 verdict（其由 ADR-016 IS gate 驅動），零資本保證由 sizing 層 `position_size == 0.0` 硬性落地——`PAPER_WATCH` 在任何情況下都不可能導出 live sizing。

### 3.5 具名常數

band 下限具名為 `PAPER_WATCH_DSR_MIN = 0.90`（data，非邏輯），與 `DSR_MIN = 0.95` 並列。調整 band 是可見、可記錄的決策。

### 3.6 防自欺聲明 — 為何 band 下限是 0.90

band 下限 0.90 的獨立理由是：DSR 0.90＝「**90% 機率真 Sharpe 超越 max-of-N-trials 噪音基準**」，仍屬**高證據水位**，僅低於資本部署檻（0.95）。低於 0.90 者證據水位不足以稱「值得觀察」，照舊 REJECTED。本 ADR 明文**不放寬部署門檻**：DSR_MIN（0.95）仍 gate 每一分資本配置。

---

## 4. 影響與後果

### 4.1 對 inst_flow 的影響

inst_flow（DSR 0.908 ∈ [0.90, 0.95)、hard-fail 全過）依本 ADR **具 Paper-Watch 資格**——可進零資本觀察艙收 3 個月 live OOS，據以重評 DSR。其 REJECTED 的部署地位不變（未達 0.95），觀察艙不改變「非 paper-ready 部署」的結論。

### 4.2 防護欄 — 防門檻購物（threshold shopping）

- **零資本 ≠ 放寬門檻**：觀察艙不配置資本，故不是「用資本冒險換過關」；部署門檻 0.95 原封不動。
- **band 下限有獨立統計理由**（§3.6），非為單一候選量身訂做；未來任何候選同一標準適用。
- **艙位上限 2 + 3 個月硬到期 + 無新證據不得再入艙**：防止觀察艙淪為「無限期掛著等運氣」的後門。
- **晉升仍須 DSR ≥ 0.95**：live OOS 重評後未達檻者，離艙、不晉升。

### 4.3 破壞性變更

- `TruthVerdict` 新增列舉值 `PAPER_WATCH`：任何**窮舉** verdict 的消費者（`if/elif` 未涵蓋新態、或 `match` 無 default）需補一路。本 repo 已審計：`promotion_service` / `gate_machine` 不消費此 verdict；CLI / API 以字串透出，新態自然流過。
- `TruthGateResult` 新增 `is_paper_watch` property：僅新增，向後相容。
- 既有 REAL/REJECTED 判決**零改變**：DSR ≥ 0.95 仍 REAL、DSR < 0.90 仍 REJECTED、其餘 hard-fail 仍 REJECTED。唯一新行為是 DSR ∈ [0.90, 0.95) 且 hard-fail 全過的候選由 REJECTED 改判 PAPER_WATCH。

### 4.4 受影響模組

`validation/two_stage_gate.py`（新態 + `PAPER_WATCH_DSR_MIN` + `_classify_dsr` band 判定）、`research/workflows/truth_gate.py`（verdict 自然透出）、`research/cli.py`（PAPER_WATCH 觀察艙 banner）及對應測試。未觸 `orchestration/`、`runtime/`、`api/routers/research_workflows.py`、`config/settings.py`、`data/db_*`、`strategies/`（其他工作包擁有）。

### 4.5 後續動作

- [x] **艙位管理 enforcement 落地（本 PR）**：§3.3 的「上限 2 / 3 個月（90 日曆天）到期 / 一次性再入」由 `research/watch_registry.py`（append-only event-sourced JSONL）機器落地——`enroll` 驗 DSR band（[0.90, 0.95)）+ 艙位上限 + 一次性 bar，`expire_due` 冪等到期，`active_watches`/`status` 純讀取（預留 GUI/HTTP 讀取介面）。after-close 排程（`orchestration/after_close.py`）整合為守門：real session 執行前查艙位，未進艙 / 已到期拒跑（exit 1），成功後掃到期推「觀察期滿」Discord。CLI `orchestration.cli watch enroll/status`。同步補資料品質前置：近似日曆誤判平日假期 → `check_panel_freshness` 攔「無今日資料」→ `NO_DATA` skip + info（非假告警）。詳 [14 §3](../14_deployment_and_operations_guide.md)、[24 §8.4](../24_risk_management_spec.md)。
- [ ] inst_flow 工作包：實際安排零資本觀察艙位（`watch enroll --strategy inst_flow --dsr 0.908`）。
- [ ] paper 管線：以 inst_flow 為首個端到端 paper 標的，驗證 draft→paper 鏈路。
- [ ] 3 個月到期後：用累積 live OOS 重算 DSR，過 0.95 → 走正常 sizing、`watch` 離艙；未過 → 離艙不晉升。
