# 前後端重構 Goal Spec — AI 可執行需求規格

> **日期：** 2026-07-03  
> **依據：** [product_repositioning_research_plan_2026-07-03.md](./product_repositioning_research_plan_2026-07-03.md)、[FinLab Studio feature teardown](./web_design/finlab_studio_feature_teardown_2026-07-03.md)  
> **目的：** 把「以策略研究資產管理系統方向重構前後端」定義成 AI/工程代理能清楚執行的 goals、邊界、交付物與驗收標準。

---

## 1. Mission

把現有 backtest_platform 從「以 runs / gates / promote 為主的工程型研究介面」重構為：

> **策略研究資產管理工作台**：使用者可以建立策略資產、跑可配置 evaluation profile、立即取得 FinLab-style scorecard report、保留好壞策略、比較分支、從候選池勾選 Live OOS，最後才進入部署級嚴格 gate。

本重構不是全部打掉重練。現有後端策略契約、workflow primitives、validation functions、run ledger、paper replay、React shell、路由、測試框架均應盡量復用。最大改版範圍在前端 UX / IA / report experience，以及後端新增 evaluation/candidate/report orchestration layer。

---

## 2. Current-State Audit Is Mandatory

任何前端重設計前，必須先用 Playwright 截圖與路由盤點確認現況。不得只憑程式碼或主觀印象直接重畫 UI。

### 2.1 Existing Tooling

現有可復用：

- `frontend/package.json`
  - `npm run dev`
  - `npm run build`
  - `npm run test:e2e`
- `frontend/e2e/audit/playwright.config.ts`
- `frontend/e2e/audit/endpoint-audit.spec.ts`

現有 audit spec 已能做路由 API call capture；需擴充為 screenshot / UX audit。

### 2.2 Screenshot Audit Scope

必須截圖以下路由：

| Zone | Routes |
| :--- | :--- |
| Home | `/` |
| Research | `/research/strategies`, `/research/runs/new`, `/research/runs`, `/research/runs/:id`, `/research/runs/:id/trades`, `/research/compare`, `/research/sweep`, `/research/validate`, `/research/promote/:strategyId` |
| Monitor | `/monitor`, `/monitor/board`, `/monitor/watch`, `/monitor/performance`, `/monitor/positions`, `/monitor/signals`, `/monitor/risk` |
| System | `/system/data`, `/system/alerts` |

Breakpoints:

- desktop: `1440x900`
- laptop: `1280x800`
- mobile: `390x844`

States to capture where feasible:

- default/data
- loading/skeleton if deterministic
- empty
- error

### 2.3 Screenshot Audit Output

Write outputs to:

```text
dev_docs/ui_audit/current_2026-07-03/
  manifest.json
  screenshots/
    desktop/
    laptop/
    mobile/
  api_capture.json
  ux_findings.md
```

`manifest.json` must include:

- route
- resolved URL
- viewport
- screenshot path
- console errors
- page errors
- API calls on mount
- data source status

`ux_findings.md` must include one row per page:

| Page | Current purpose | UX problems | Data/API problems | Reuse recommendation | Redesign priority |
| :--- | :--- | :--- | :--- | :--- | :--- |

### 2.4 Screenshot Audit Acceptance

Audit is complete only if:

- Every route above has screenshots for all three breakpoints.
- Any route needing runtime IDs resolves real IDs from API or documents fallback.
- All screenshots are visually inspectable and nonblank.
- `ux_findings.md` includes page-level recommendations.
- Existing endpoint audit still writes API call capture.
- The audit does not require production credentials or external paid data.

---

## 3. Reuse Inventory

Before implementation, agents must produce or update a reuse matrix. The expected baseline is below.

### 3.1 Backend Assets To Reuse

| Asset | Path | Reuse decision |
| :--- | :--- | :--- |
| Strategy contract / registry | `backtest_platform/src/backtest_platform/strategies/protocol.py` | Reuse. New flows must call registered runners, not direct strategy functions. |
| Workflow configs | `research/workflows/config.py` | Reuse as low-level declarations; add evaluation profile layer above. |
| DOE workflow | `research/workflows/doe.py` | Reuse as optional workflow primitive. |
| GO gates workflow | `research/workflows/go_gates.py` | Reuse as optional WFA/PBO primitive. |
| Truth gate workflow | `research/workflows/truth_gate.py` | Reuse for deployment strict profile; do not make it the only evaluation path. |
| Validation functions | `validation/*` | Reuse metrics, WFA, DSR, PBO, two-stage gate. |
| Run stores / series | `research/runs_store.py`, `run_series_store.py` | Reuse for lineage and existing reports. |
| Paper replay | `research/workflows/paper_replay.py` | Reuse but trigger from selected candidates / Live OOS queue. |
| Watch registry | `research/watch_registry.py` | Reuse concepts; may remain Paper-Watch-specific or be wrapped by broader candidate/live queue. |
| API envelope | `api/envelope.py` | Reuse for all new endpoints. |

### 3.2 Frontend Assets To Reuse

| Asset | Path | Reuse decision |
| :--- | :--- | :--- |
| React/Vite app shell | `frontend/src/layouts/AppShell.tsx` | Reuse if screenshot audit does not show structural navigation failure. |
| Router | `frontend/src/router.tsx` | Reuse, but IA/routes will change. |
| Query/http services | `frontend/src/services/*` | Reuse. |
| i18n foundation | `frontend/src/i18n/*` | Reuse. |
| Design tokens | `frontend/src/styles/*`, `dev_docs/web_design/design-system-specs/*` | Reuse after UX audit; adjust tokens only with design rationale. |
| Existing Research pages | `frontend/src/features/research/pages/*` | Mostly refactor/recompose; current RunReport is insufficient as final report experience. |
| Trade review chart | `CandlestickChart`, `TradeReviewPage` | Reuse as evidence drilldown component. |
| Monitor Watch page | `WatchPage` | Reuse concepts for Live OOS queue/status. |
| Vitest tests | `*.test.tsx` | Reuse and update around new UX contracts. |
| Playwright audit | `frontend/e2e/audit/*` | Extend for screenshots and UX audit. |

### 3.3 Likely Rebuild Areas

| Area | Reason |
| :--- | :--- |
| Research IA | Current IA is run/promote workflow-centric, not strategy asset/report/candidate-centric. |
| Run Report | Current page has 6 KPI cards and pending tear sheet; target needs scorecards, sheets, linked trade evidence, decisions. |
| Strategy Library | Current page is registry/run projection; target needs strategy asset cards with hypothesis, status, reports, next action. |
| Candidate Pool | New core page. |
| Evaluation Profile UI | New configuration surface. |
| Report Viewer | New FinLab-style analysis workspace. |
| Interactive Simulation | New workflow surface. |
| Branch Experiment | New workflow surface; AI optimize can be added after branch mechanics exist. |

---

## 4. Parallel Development Model

Frontend and backend can be developed separately if contracts are explicit.

### 4.1 Backend-First Deliverables

Backend owns:

- evaluation profile schema
- evaluation orchestrator
- report pack manifest
- candidate pool store
- candidate decision audit
- live OOS queue
- API endpoints
- OpenAPI updates
- deterministic fixtures for frontend development

### 4.2 Frontend-First Deliverables

Frontend owns:

- screenshot audit
- new IA and navigation
- report viewer UX
- candidate pool UX
- strategy asset UX
- simulation UX shell
- branch experiment UX shell
- visual regression/audit screenshots

### 4.3 Contract Boundary

Frontend must not wait for full backend implementation. Backend must provide fixture endpoints or JSON fixtures early.

Minimum contract files:

```text
dev_docs/contracts/evaluation_profile.schema.json
dev_docs/contracts/evaluation_result.example.json
dev_docs/contracts/report_pack_manifest.example.json
dev_docs/contracts/candidate_pool.example.json
dev_docs/contracts/live_oos_queue.example.json
```

Frontend may implement against fixtures first, then switch to API when backend lands.

---

## 5. Goal Structure

### Goal 0 — Current UX / API Audit Baseline

**Objective:** Capture the current frontend and API-on-mount behavior before redesign.

**Owner:** Frontend / QA agent

**Inputs:**

- Current React app.
- Existing Playwright audit config.
- Running backend or documented fixture fallback.

**Tasks:**

1. Extend Playwright audit to capture screenshots for all routes and viewports.
2. Capture console/page errors and API calls.
3. Write `ux_findings.md`.
4. Identify pages/components to reuse, refactor, or replace.

**Out of scope:**

- No UI redesign in this goal.
- No backend schema changes.

**Acceptance:**

- `dev_docs/ui_audit/current_2026-07-03/manifest.json` exists.
- Screenshots exist for all required routes and viewports.
- `ux_findings.md` contains one row per route.
- All blank/broken pages are explicitly marked.
- `npm run build` and audit Playwright command pass or failures are documented with exact blocker.

---

### Goal 1 — Product IA / UX Redesign Specification

**Objective:** Redesign the application information architecture around strategy assets, report packs, candidate pool, and Live OOS selection.

**Owner:** Product / Frontend design agent

**Inputs:**

- Goal 0 screenshots and findings.
- Product repositioning report.
- FinLab Studio teardown.

**Target IA:**

| Zone | Target pages |
| :--- | :--- |
| Research | Strategy Assets, Evaluate, Candidate Pool, Report Viewer, Compare, Profiles, Branch Experiments |
| Live OOS | Queue, Watch Sessions, Review Reports |
| Deployment | Strict Gate, Promote |
| Monitor | Fleet, Positions, Signals, Risk, Performance |
| System | Data, Alerts, Profile/Threshold Settings |

**Tasks:**

1. Produce target sitemap.
2. Define page purpose, primary user action, secondary actions.
3. Define empty/loading/error/data states.
4. Define navigation labels and route paths.
5. Define which current pages are replaced vs retained.

**Out of scope:**

- No production implementation.
- No final visual polish without screenshot baseline.

**Acceptance:**

- `dev_docs/web_design/rebuild_ia_spec_2026-07-03.md` exists.
- Every target route has page purpose, main actions, data needs, and acceptance states.
- Current routes have migration mapping.
- New IA explicitly separates Research Triage, Live OOS, and Deployment.

---

### Goal 2 — Backend Evaluation / Candidate Contracts

**Objective:** Define backend contracts that let frontend and backend develop independently.

**Owner:** Backend agent

**Inputs:**

- Product repositioning report.
- Existing workflow config models.
- Existing API envelope contract.

**Tasks:**

1. Define `EvaluationProfile`.
2. Define `EvaluationResult`.
3. Define `ReportPackManifest`.
4. Define `Candidate`.
5. Define `CandidateDecision`.
6. Define `LiveOOSQueueItem`.
7. Add example JSON fixtures.
8. Draft endpoints and error semantics.

**Out of scope:**

- No full orchestration implementation.
- No DB migration unless needed for contract proof.

**Acceptance:**

- Contract docs/examples exist under `dev_docs/contracts/`.
- All new API responses use existing envelope style.
- Examples are sufficient for frontend fixture mode.
- Each contract states which current backend modules can produce its fields.

---

### Goal 3 — Backend Evaluation Orchestrator MVP

**Objective:** Add a high-level evaluation layer above existing low-level workflows.

**Owner:** Backend agent

**Inputs:**

- Goal 2 contracts.
- Existing `doe/go_gates/truth_gate/paper_replay`.

**Tasks:**

1. Add `research/evaluation/` package.
2. Implement profile registry with `quick_triage`, `fixed_hypothesis_oos`, `grid_search_selection`, `deployment_strict`.
3. Implement `research evaluate --strategy --profile`.
4. Generate report pack files.
5. Persist evaluation result JSONL.
6. Add unit tests.

**Out of scope:**

- No AI optimize.
- No full interactive simulation.
- No production DB migration.

**Acceptance:**

- CLI can evaluate at least one existing strategy with `quick_triage`.
- Failed/weak strategies persist results and are not discarded.
- Report pack includes `summary.json`, `metrics.json`, `scorecards.json`, `report.md`.
- Existing workflow tests continue to pass.

---

### Goal 4 — Candidate Pool Backend MVP

**Objective:** Store all evaluation outcomes and support human decisions.

**Owner:** Backend agent

**Tasks:**

1. Implement `candidate_store.py`.
2. Implement append-only `candidate_decisions.jsonl`.
3. Implement CLI:
   - `research candidates list`
   - `research candidates decide`
   - `research candidates select-live-oos`
4. Implement API:
   - `GET /research/candidates`
   - `POST /research/candidates/{id}/decision`
   - `POST /research/candidates/{id}/select-live-oos`

**Acceptance:**

- Every evaluation can create/update a candidate.
- Decisions require a reason for override paths.
- Candidate state transitions are deterministic and tested.
- Live OOS selected candidates are queryable.

---

### Goal 5 — Frontend Report Viewer MVP

**Objective:** Replace the current weak Run Report experience with a FinLab-style research report shell.

**Owner:** Frontend agent

**Inputs:**

- Goal 0 screenshot baseline.
- Goal 2 fixture JSON.
- FinLab Studio teardown.

**Tasks:**

1. Build `/research/reports/:runId`.
2. Render headline metrics banner.
3. Render five scorecards:
   - Profitability
   - Risk
   - Risk-Adjusted
   - Win Rate
   - Liquidity
4. Render sheet tabs per scorecard.
5. Render linked trade log section.
6. Render evidence/gate checks.
7. Render decision action bar.

**Out of scope:**

- No AI optimize.
- No live trading controls.
- Interactive simulation may be disabled until Goal 8.

**UX Acceptance:**

- The first viewport answers: what strategy/run is this, how did it perform, what is the recommended next action.
- Scorecards show pass/warn/fail per metric, not only raw numbers.
- No page section is an unexplained placeholder if fixture data exists.
- Mobile view remains usable; no text overlap.
- Screenshots after implementation show improvement over Goal 0 baseline.

**Technical Acceptance:**

- Vitest coverage for report rendering.
- Build passes.
- Playwright screenshot audit includes the new report route.

---

### Goal 6 — Frontend Candidate Pool MVP

**Objective:** Make Candidate Pool the main semi-automatic decision surface.

**Owner:** Frontend agent

**Tasks:**

1. Build `/research/candidates`.
2. Show candidates table/cards with filters.
3. Surface latest scorecard status.
4. Support Keep / Archive / Rerun / Select Live OOS actions.
5. Require reason on override.
6. Link to Report Viewer.

**Acceptance:**

- User can identify promising, weak, negative, data-issue, and live-oos-selected strategies.
- User can select eligible candidates for Live OOS without visiting low-level gate pages.
- Deployment/promote is not the primary action in Candidate Pool.
- Mobile and desktop screenshots pass visual sanity check.

---

### Goal 7 — Frontend Strategy Asset UX

**Objective:** Convert Strategy Library from a run projection into a strategy research asset workspace.

**Owner:** Frontend agent

**Tasks:**

1. Redesign `/research/strategies`.
2. Add strategy asset detail route.
3. Show hypothesis, mechanism, latest profile, latest report, candidate state, next action.
4. Keep links to runs/history as secondary evidence.

**Acceptance:**

- Strategy cards are understandable before any gate/promote status.
- Bad/archived strategies remain discoverable.
- User can start `Evaluate` from a strategy asset.

---

### Goal 8 — Interactive Simulation Workflow

**Objective:** Add research-only what-if simulation for stop-loss, take-profit, cost, and capacity.

**Owner:** Full-stack agent

**Tasks:**

1. Define simulation result contract.
2. Implement backend simulation from existing trades/equity data.
3. Add frontend slider controls.
4. Output branch suggestion, not automatic config mutation.

**Acceptance:**

- Simulations do not modify original strategy config.
- Results include before/after metrics and affected trades count.
- UI clearly labels simulation as research-only.

---

### Goal 9 — Branch Experiment / AI Optimize Lite

**Objective:** Support strategy iteration as explicit branches with lineage and comparison.

**Owner:** Full-stack agent

**Tasks:**

1. Add branch model and parent-child lineage.
2. Add branch suggestion from report findings or simulation.
3. Add diff manifest for config/code changes.
4. Run evaluation on branch.
5. Compare branch vs parent.

**Acceptance:**

- Every branch has parent run/strategy link.
- Compare view shows delta metrics and decision.
- No branch can overwrite the parent silently.

---

### Goal 10 — Live OOS Queue Integration

**Objective:** Ensure expensive paper/live OOS workflows only run after human selection.

**Owner:** Backend + Frontend agents

**Tasks:**

1. Implement queue persistence.
2. Connect Candidate Pool selection to queue.
3. Make paper replay / after-close consume queue or document compatibility wrapper.
4. Build queue/status UI.

**Acceptance:**

- Non-selected candidates do not run paper replay automatically.
- Selected candidate has audit reason.
- Queue item links back to report, candidate, and strategy asset.
- Expired/paused/completed statuses are visible.

---

## 6. Non-Goals

Do not do these during the first rebuild pass:

- Do not rewrite strategy runner contract.
- Do not delete existing low-level workflows.
- Do not remove strict truth gate; reposition it as deployment profile.
- Do not build real AI agent before branch experiment lineage exists.
- Do not introduce multi-user auth/RBAC.
- Do not require paid data or broker credentials for UI development.
- Do not start with a large DB migration; JSONL/fixtures are acceptable for MVP.
- Do not redesign UI without screenshot baseline.

---

## 7. Global Acceptance Criteria

The rebuild is acceptable only when:

1. Current-state Playwright screenshots and UX findings exist.
2. A reuse matrix identifies what is reused, refactored, replaced.
3. Frontend and backend can develop against documented contracts/fixtures.
4. Research Triage, Live OOS, and Deployment are separate user journeys.
5. Every evaluated strategy is persisted, including failed/negative strategies.
6. Initial report output includes scorecards, not just a binary verdict.
7. Candidate Pool lets the user select Live OOS manually.
8. Strict deployment gate remains available but is no longer the first user-facing research experience.
9. Playwright screenshot audit passes after redesign for desktop/laptop/mobile.
10. `npm run build` and relevant backend tests pass, or exact blockers are documented.

---

## 8. AI Agent Operating Rules

Any AI agent implementing this rebuild must follow these rules:

1. **Start with audit.** No UI redesign before Playwright screenshots and UX findings.
2. **State write scope.** Each task must list files it will edit.
3. **Preserve unrelated changes.** Do not revert user files or untracked files outside scope.
4. **Use contracts.** Frontend may use fixtures, but fixtures must match documented backend contracts.
5. **Keep low-level workflows intact.** New high-level flows wrap `doe/go_gates/truth_gate/paper_replay`; they do not break them.
6. **Report gaps explicitly.** If a metric/sheet cannot be produced from existing data, mark it `not_available` with reason.
7. **Screenshot before and after.** UI tasks require visual before/after evidence.
8. **No hidden deployment relaxation.** Changing UI flow must not silently loosen deployment strict gate.

---

## 9. Suggested First Sprint

The first sprint should be narrow and proof-oriented:

1. Extend Playwright audit to screenshot all current pages.
2. Produce `ux_findings.md`.
3. Define contract examples for evaluation result, report pack, candidate pool.
4. Build static/fixture-backed Report Viewer shell with five scorecards.
5. Build static/fixture-backed Candidate Pool shell.
6. Review screenshots and only then wire real backend MVP.

This sprint proves the new product direction without risking core validation logic.
