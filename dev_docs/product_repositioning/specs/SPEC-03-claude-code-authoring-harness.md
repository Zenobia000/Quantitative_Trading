# SPEC-03：Claude Code 研究撰寫 Harness（dev-time accelerator）

> 狀態: Draft | 日期: 2026-07-06 | 關聯: ADR-009、ADR-008、ADR-R06、ADR-002（Research 邊界）、ADR-005（Risk fail closed）、ADR-006（Contract-first）
>
> 觸發來源: 產品重定位討論——參照 Nyrobrain「AI 量化 Agent」範式，評估「以 coding agent（Claude Code）作為策略研究底層 harness、UI 前端只做視覺化」的可行性。地毯掃描（見 `.claude/context/decisions/explore-2026-07-06-0158-research-surface-agent-feasibility.md`）證實現況架構已是 CLI-first / importable / filesystem-ledger，天然支援此形狀。

---

## 1. 問題陳述

Nyrobrain 式 AI 量化平台最貴、最脆的一塊，是自建 `自然語言 → AST → code → sandbox 預編譯` 的中介層；其真正死穴是「消除程式碼壁壘 ≠ 消除量化知識壁壘」——使用者不懂統計套利就給不出好 prompt，工具只會產出無預測力的 data mining。

本平台的處境相反：

- **編譯器不用自建**：Claude Code 本身就是工業級 coding agent，已解決幻覺 / sandbox / tool-use。
- **知識壁壘有解**：平台已有 `conformance` / `gate_state` / `dsr`(trials deflation) / `pbo` / `wfa` / `two_stage_gate` 一整套防過擬合閘門；把量化紀律編碼成 skill + `CLAUDE.md`，知識落在 agent 身上而非使用者。
- **撰寫 seam 已就緒**：ADR-008 / ADR-R06 已拍板「策略是 repo 內 Strategy Package，AI coding/IDE 撰寫，UI 只消費 read model」。

核心決策：**以 Claude Code 作為 dev-time 研究撰寫 harness——操作者在 repo 內驅動 agent 撰寫策略、跑既有研究閉環、產出證據；agent 停在 governance 閘門前等人拍板。不自建 NL→code 編譯器，不做 runtime 引擎，不做多租戶 SaaS。**

---

## 2. 目標

1. 定義 Claude Code 取用平台能力的**四個面**與其邊界（撰寫 / 積木 / 管道 / 紀律）。
2. 明確「無 MCP」的整合形狀：**agent 用 Python 直譯器 + finlab SDK + 既有 `research.cli`**，而非專蓋 MCP tool 層。
3. 把地毯掃描的 🟢/🟡/🔴/⚪ 能力分級固化為 agent 授權矩陣（§5）。
4. 定義三條不可違反的邊界鐵律 + trials 誠實計數鐵律（§6），供 skill / `CLAUDE.md` 承載。
5. 給出零基建優先的落地波次（§7），P0 不需任何新基建。

---

## 3. 非目標

- **不自建** NL→AST→code→sandbox 編譯器（Claude Code 即是）。
- **不做 runtime 引擎**：UI 不在背後起 headless agent session 幫終端使用者寫策略（Nyrobrain 式；已於重定位討論排除）。
- **不做多租戶 SaaS**：不做隔離 project folder / 計費 / 租戶安全。
- **不蓋 MCP server**：降為 optional backlog，僅當未來需要「agent 與 UI 共用唯讀結構化狀態面」時再評估；即使屆時，「agent 跑與 API 同一支 CLI」通常仍較簡單。
- **不把任意 Python 編輯器嵌進 backtest 服務**（重申 ADR-008 後果）。
- 本切片不改任何既有策略契約或 API 契約。

---

## 4. Harness 四面架構

repo 即專案資料夾。Claude Code 透過四個面取用平台，UI 前端完全不動、維持營運/治理台角色。

```text
repo（= 專案資料夾）
├── ① 撰寫面 (filesystem)   agent 寫 strategies/<pkg>/{strategy,runner,research_config}.py + tests
├── ② 積木面 (authoring SDK) 策略碼 import 的現成積木（common/panel、common/mechanics、validation.metrics …）
├── ③ 管道面 (Python + CLI)  agent 用 python -m backtest_platform.research.cli <cmd> / 直接 import 呼叫
└── ④ 紀律面 (skills + CLAUDE.md) 量化紀律、注意事項、邊界鐵律編碼為護欄
```

| 面 | 機制 | 為何不是 MCP |
| :--- | :--- | :--- |
| ① 撰寫 | filesystem；agent 就在 repo 寫檔 | 寫檔本來就沒 MCP 的事 |
| ② 積木 | 一包可 import 的 lib（多數已在 `strategies/common/`、`research/domain/`、`validation/`） | SDK 是「策略碼 import 的積木」，與取用管道不同層 |
| ③ 管道 | `research.cli`（18 子命令）+ 可 import 的 application/workflow 函式 | 資料字典本身即 finlab SDK（`data.search()` 離線可用）；回測即可 import 的 Python。MCP 只會多包一層與 agent 本能重疊 |
| ④ 紀律 | Claude Code skill + `strategies/CLAUDE.md` | 護欄是文字規範，非 tool |

> 邊界安全**不靠** MCP：Claude Code 有 Bash、能寫任意 Python，本就非 sandbox。真正擋住 `Research ⊄ broker` 的是 **import-linter（CI 靜態）+ 人 review PR**（見 ADR-002、refactor WBS W1.1）。

---

## 5. Agent 授權矩陣（地毯掃描結論）

🟢 後台自主可做 · 🟡 技術可做但屬治理決策/需金鑰（人審或走 env） · 🔴 off-limits（execution） · ⚪ 平台未實作

| 能力 | 入口 | 級別 |
| :--- | :--- | :---: |
| 策略撰寫 | `strategies/<pkg>/*`（filesystem） | 🟢 |
| 契約自檢 | `research.cli validate-strategy` | 🟢 |
| 單次/批次回測 | `research.cli run-is` / `run-batch`（`research.is_harness`） | 🟢 |
| 參數探索 | `research.cli sweep` / `doe`（`research.sweep` / `workflows.doe`） | 🟢 |
| 防過擬合驗證 | `go-gates` / `truth-gate` / `validate` / `health`（`validation.*`） | 🟢 |
| 評估 profiles | `research.cli evaluate`（`research.evaluation.evaluate`） | 🟢 |
| 分支實驗 | `research.cli branches create/evaluate/compare` | 🟢 |
| 比較/報表/視覺料 | `compare` / run report / candles / notebook | 🟢 |
| 候選管理 | `research.cli candidates list/decide` | 🟢 |
| Trials 計數 | `trials increment` / `trials_counter_store` | 🟢（見 §6.4 鐵律） |
| 選入 Live-OOS | `candidates select-live-oos`（enqueue governance 佇列） | 🟡 |
| 推進狀態機 | `research.cli promote-check` / promotion_service | 🟡 |
| 資料準備 | `build-universe` / `system/ingest`（需 finlab 金鑰） | 🟡 |
| 每日實盤管線 | `orchestration.cli run --real` | 🔴 |
| 收盤後排程 | `orchestration.cli after-close` | 🔴 |
| Paper-Watch 排程 | `orchestration.cli watch *` / `live-oos consume` | 🔴 |
| broker / live DB sink | `adapters.brokers.*` / TimescaleDB live | 🔴 |
| 風控/告警端點 | `system/risk/evaluate`、`system/alerts/*` | ⚪ stub |

---

## 6. 邊界鐵律（skill / CLAUDE.md 必承載）

### 6.1 Execution 全線 off-limits

research agent **一律不碰** `orchestration.cli` / `services.strategy_runtime.*` / `adapters.brokers.*` / live DB sink。這是 golden anti-decision（ADR-002/ADR-003），import-linter 已在 CI 擋，agent 多守一層。

### 6.2 Governance 閘門是人類決策

`select-live-oos` / `promote` / release / candidate keep：agent **產證據，人拍板**（PRD `US-GOV` 要 audit reason）。agent 可準備、可建議，不可自行跨閘。

### 6.3 金鑰不入 agent

`build-universe` / `ingest` 需 finlab 金鑰——走 env / secret manager，**agent 不持有**。agent 可觸發流程，金鑰注入在 env 邊界。

### 6.4 Trials 誠實計數（防過擬合的最後防線）

agent 每多跑一輪 `sweep` / `doe` trial，**必須誠實 increment trials counter**（`trials_counter_store` / `POST /research/trials/increment`），否則 `dsr.py` 的 DSR deflation 會被 agent「多試幾組挑最好的」本能繞過——這正是 Nyrobrain 死穴（data mining）本身。此為 skill 第一鐵律。

---

## 7. 落地波次（零基建優先）

| 階段 | 工作 | 新基建 | 驗收 |
| :--- | :--- | :---: | :--- |
| **P0** | 寫 skills（策略撰寫規格 / 防過擬合紀律 / 資料字典判讀）+ `strategies/CLAUDE.md`；純 filesystem + `research.cli` 端到端讓 Claude Code 撰寫並驗證一個新策略 package | **零** | agent 從零產出通過 `test_conformance` 的策略，並跑完 evaluate 產出 report pack |
| **P1** | 把「保留候選」動作接到既有 run pipeline（agent 走 `research.cli`，evidence ledger 與 UI 一致） | 零～薄 | agent 產生的 run 在 UI runs ledger 可見 |
| **P2** | 從 agent 反覆手刻的 pattern 抽出/硬化 authoring SDK 積木 | 一包 lib | 常用積木有測試、有文件、agent 優先復用 |
| ~~MCP~~ | 降為 optional backlog（§3 非目標） | — | 僅當需「UI 共用唯讀結構化狀態面」時再評估 |

P0 零基建即有產出，且先驗證最不確定的**紀律層**：若 skills 能讓 Claude Code 誠實地在閘門內產出合格策略，後續純屬加速；若不能，成本僅為幾份 md。

---

## 8. UI 角色重定位（連帶結論）

若 agent 後台能驅動整條研究閉環（撰寫→conformance→run-is→doe→go-gates→truth-gate→evaluate→candidate→停在 governance），則 **UI 前端不是「研究驅動台」，而是「治理 + 證據審閱台」**：人在 UI 讀 evidence ledger、truth-gate verdict，按 approve/reject。此與 `17_frontend_information_architecture.md` 的營運台定位一致，不需改前端 IA。

---

## 9. 落地清單

- [ ] SPEC-03（本檔）
- [ ] ADR-009（`04_architecture_decision_records.md`）
- [ ] `00_INDEX.md` specs 列 + 決策摘要同步
- [ ] `16_wbs_development_plan.md` WP 12
- [ ] P0：skills + `strategies/CLAUDE.md`（後續 PR）
