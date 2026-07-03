# Rebuild UX / API Audit — Findings (Wave E rerun, post-redesign)

> **Date:** 2026-07-03
> **Branch / worktree:** `chore/ui-audit-rebuild` @ base `3042b92` (origin/main, rebuild Goal 0-10 all merged; #194 branch-experiments is the tip)
> **Spec:** `rebuild_goal_spec_ai_requirements_2026-07-03.md` §2 (Current-State Audit tooling) + §7 #9 (screenshot audit passes after redesign) + §8 #7 (before/after evidence)
> **Method:** Playwright full-page screenshot sweep + xhr/fetch capture-on-mount. Fresh SPA boot per route via `page.goto` (vite `spaBypass` serves `index.html` for `text/html` deep links). GET-only — no write-action buttons clicked. Redirect routes recorded once (redirect behaviour only), not screenshotted ×3.
> **Frontend:** self-hosted vite dev @ `:5176` (strictPort), `DEV_API_PROXY_TARGET=http://localhost:8083`. Shared-host rule honoured: the parallel session's `:5173` + `:8080` were never touched.
> **Backend:** worktree-local `127.0.0.1:8083` uvicorn (`v0.6.0`), `uv run --extra api`, code = current main (all new endpoints). Stores env-var-isolated + CWD-aligned onto the worktree's gitignored `backtest_platform/reports/` (`EVALUATIONS_PATH` / `CANDIDATES_PATH` / `CANDIDATE_DECISIONS_PATH` / `LIVE_OOS_QUEUE_PATH` / `BRANCHES_PATH` / `BACKTEST_RUNS_PATH`). Main-repo data untouched.
> **Seed (data-state, the Goal-0 "zero-run data starvation" fix):** synthetic 3-file parquet (500 business days × 4 symbols, `tests/research/test_cli_evaluate.py::_gen_parquet` schema) + CLI `research evaluate --strategy {momentum,inst_flow,reversal} --profile quick_triage --data-dir <synth> --symbols 2330,2317,2454,1101 --start 2019-01-01 --end 2020-12-31`, then `candidates decide --candidate cand_momentum --action keep --label promising`, `candidates select-live-oos --candidate cand_inst_flow --override --reason "…"` (→ 1 queue item), `candidates decide --candidate cand_reversal --action keep --label weak`. Result: 3 real candidates (Promising / Weak / Weak), 3 evaluations + report packs, 1 live-OOS queue item.
> **Artifacts:** `manifest.json` (69 entries = 23 screenshot-routes × 3 viewports + `redirects[3]`), `api_capture.json`, `screenshots/{desktop,laptop,mobile}/`.

## Coverage & environment

- **23 screenshot routes × 3 viewports (desktop 1440×900 / laptop 1280×800 / mobile 390×844) = 69 screenshots.** All present, all > 10 KB (smallest 13 KB = mobile `/research/compare`), all visually non-blank (spot-checked flagship pages + mobile).
- **3 redirect routes recorded** (redirect behaviour only): `/research/validate → /deploy/gate` ✓, `/research/promote/:id → /deploy/promote/:id` ✓, `/monitor/watch → /live-oos/watch` ✓. All 3 resolve to their expected target (`matchedExpectedTarget: true`).
- **Observed states are identical across all three viewports** (`data ×11, empty ×8, error_or_degraded ×3, static_no_api ×1`) — the redesign has no viewport-specific breakage. **Zero page (JS) errors** anywhere.
- **Data starvation is materially improved** — see the before/after section. `data ×11 / 23` here vs `data ×8 / 20` at the Goal-0 baseline, and every NEW core page (Candidate Pool, Report Viewer, Live-OOS Queue, Strategy detail) is now screenshottable in a genuine data state.
- **Parametric-id resolution:** Report Viewer `:runId` resolves to an **evaluation id** from `GET /research/candidates → latest_evaluation_id = eval_reversal_quick_triage_9cd53b15afdb` (real); strategy-detail `:name → four_layer` (`GET /strategies[0].name`, real registry catalog); Run-Report `:id → NO_RUN_SEEDED` (runs ledger empty — evaluate seeds evaluations, not the runs ledger); promote `:strategyId → four_layer` (roster empty fallback). All recorded in `manifest.resolvedIds` + per-entry `resolvedFrom`.

## Route reconciliation (spec §2.2 → actual five-zone router)

Spec §2.2 predates the rebuild; reconciled against `src/router.tsx` + `nav.ts` (five zones: research / live-oos / deployment / monitor / system):

| Change vs Goal 0 | Route(s) | Note |
| :--- | :--- | :--- |
| **NEW — Candidate Pool** | `/research/candidates` | The semi-automatic decision surface (Goal 6). In **data** state (3 candidates). |
| **NEW — Report Viewer** | `/research/reports/:runId` | FinLab scorecard report (Goal 5). Main verdict+scorecards in **data**; see P1-a. |
| **NEW — Live OOS zone** | `/live-oos/queue`, `/live-oos/watch` | Queue in **data** (1 item); Watch **empty** (no watch berth seeded). |
| **NEW — Deployment zone** | `/deploy/gate`, `/deploy/promote/:strategyId` | Strict gate + promote relocated out of Research (Goal 1). Both **data**. |
| **FIXED — was dead-404** | `/monitor/board` | Goal-0 baseline rendered `404` (unwired). Now wired → renders **empty** (`pending` telemetry). |
| **Migrated (redirect)** | `/research/validate`, `/research/promote/:id`, `/monitor/watch` | Old paths kept as client redirects → Deployment / Live-OOS. All 3 verified. |
| Retained | 16 prior routes | Present as listed. |

## Per-page findings (one row per actual screenshot route)

| Page (route) | Purpose | Observed state | UX / data notes | Priority |
| :--- | :--- | :--- | :--- | :--- |
| `/` | Cross-zone cockpit + onboarding | **data** (`ledger`) | Renders; ribbon should track the new five-zone IA. | P2 |
| `/research/strategies` | Strategy-asset catalog (registry × runs × watch) | **data** (`ledger`,`watch_registry`) | **Goal-0 P0 fixed** — `/strategies` now proxied; no more red 404 banner. Renders `策略資產` cards. | P2 |
| `/research/strategies/:name` | Per-strategy asset detail | **data** (`ledger`,`watch_registry`) | Resolved to `four_layer` (registry catalog header + verdict timeline + watch pod). No candidate for four_layer, so candidate block is empty; a strategy WITH a candidate would show more. | P2 |
| `/research/candidates` | **Candidate Pool** (decision battlefield) | **data** (`ledger`) | 3 candidate cards w/ state badges (`偏弱`/`已選 Live OOS`/`有潛力`), filter chips (全部 3 / 有潛力 1 / 已選 1 / 偏弱 1), scorecard chips, Sharpe/DSR/MaxDD, links (查看報告/策略資產/決策軌跡), actions (保留/進入 Live OOS/重跑/封存). **This is the strongest new surface.** | — |
| `/research/runs/new` | Run authoring form | **data** | Form renders; strategy picker now populated (proxy fix). | P2 |
| `/research/runs` | Verdict ledger table | **empty** | Runs ledger empty (evaluate does not append to it). Clean empty state. | P2 |
| `/research/runs/:id` | **Old** Run Report | **error_or_degraded** | `NO_RUN_SEEDED` → graceful 404. Superseded by Report Viewer; not seeded. | P2 |
| `/research/reports/:runId` | **Report Viewer** (flagship) | **error_or_degraded**\* | \*Main `GET /research/evaluations/{id}` → **200 data**: verdict banner (reversal / Weak / needs_more_research), 6 headline metrics, all **5 scorecards** (pass/warn/fail per metric), sheet tabs, decision action bar. Degraded flag is ONLY the secondary legacy `GET /runs/{run_id}/report` → 404 (linked-trade-log). First screen answers all three Goal-5 questions. | P1-a |
| `/research/runs/:id/trades` | Trade drilldown | **error_or_degraded** | `candles` 404 on unseeded run id. `CandlestickChart` intact. | P2 |
| `/research/compare` | Multi-run delta | **static_no_api** | Inert on bare mount (waits for `?run_ids=`) — same as baseline; enter from report/candidate. | P2 |
| `/research/sweep` | Parameter-sweep config | **data** | `/runs/estimate` OK. | P2 |
| `/live-oos/queue` | **Live-OOS Queue** | **data** (`watch_registry`) | 1 queue item (inst_flow, `paper_replay`, `queued`) w/ audit reason + links back to candidate/eval. Journey-2 surface works. | — |
| `/live-oos/watch` | Paper-Watch observation | **empty** (`watch_registry`) | Renders; no watch berth seeded (would need a `truth_gate` PAPER_WATCH verdict). | P2 |
| `/deploy/gate` | Strict deployment gate | **data** | Two-stage gate spec viewer, relocated out of Research (Goal 1 / spec §8 #8 — strict gate no longer the first research experience). | — |
| `/deploy/promote/:strategyId` | Promote flow | **data** | Renders `晉升流程`; now in Deployment zone. | P2 |
| `/monitor` | Fleet control | **empty** (`pending`) | No daemon telemetry. | P2 |
| `/monitor/board` | Run board | **empty** (`pending`) | **Goal-0 dead-404 FIXED** — route now wired, renders. | P2 |
| `/monitor/performance` · `/positions` · `/signals` · `/risk` | Monitor telemetry | **empty** (`pending`) | All render empty (no daemon feed) — honest onboarding, not broken. | P2 |
| `/system/data` | Data dictionary / card wall | **data** (`catalog`,`parquet_scan`) | Richest config-driven page; the seeded synthetic bundles now show as scanned parquet. | P2 |
| `/system/alerts` | Alert rules + channels | **data** | Renders fully. | P2 |

## Before / after vs Goal 0 baseline (`current_2026-07-03/`)

| Dimension | Goal 0 baseline | Wave E rebuild | Verdict |
| :--- | :--- | :--- | :--- |
| Screenshot routes × viewports | 20 × 3 = 60 | 23 × 3 = 69 (+ 3 redirect records) | wider IA, fully covered |
| Desktop **data**-state pages | **8 / 20** | **11 / 23** | +3 on a larger set; core pages now data |
| Strategy Hub list | **P0 hard red 404** (`/strategies` proxy gap) | **data** — catalog renders | **fixed** |
| `/monitor/board` | **dead 404** (unwired nav link) | **empty** — wired, renders | **fixed** |
| Flagship report | **only 404 error state** (zero runs) | **Report Viewer in data** — verdict + 5 scorecards + decision bar | **fixed** |
| Candidate Pool / Live-OOS Queue | did not exist | **data** — 3 candidates, 1 queue item | **new, working** |
| Research vs Live-OOS vs Deployment | one workflow-centric zone; validate/promote as primary Research nav | **three separate journeys** (5 zones); strict gate demoted to Deployment | **journeys separated** (§7 #4/#8) |

### Five biggest improvements
1. **Report Viewer went from un-screenshottable (only a 404) to a full FinLab-style data render** — headline verdict + recommendation + 6 headline metrics + five pass/warn/fail scorecards + sheet tabs + decision action bar, first-screen-complete (Goal 5 / §7 #6).
2. **Candidate Pool exists and is the decision battlefield** — good/weak/negative/live-oos-selected all discoverable, per-card Keep/Archive/Rerun/Select-Live-OOS, override-reason path, links to report + asset (Goal 6 / §7 #7).
3. **Data starvation broken** — the Goal-0 "zero runs" blocker is resolved by CLI `evaluate`-seeded candidates/evaluations/queue; data-state pages 8→11 and every new core surface has real content.
4. **Two Goal-0 defects fixed**: `/strategies` dev-proxy 404 (Strategy Hub no longer a red error) and `/monitor/board` dead-404 (now wired).
5. **Journeys are physically separated** into five zones (Research triage / Live OOS / Deployment / Monitor / Fleet / System); strict gate + promote relocated out of Research to Deployment, and the three legacy paths redirect cleanly.

## Residual issues (honest, for the next round)

- **P1-a — Report Viewer linked-trade-log fetches the legacy `/runs/{run_id}/report` (404 under evaluate-only seed).** The evaluate path writes an evaluation + report pack (`series.json` with equity/drawdown/trades) but NOT the runs ledger / run-series sidecar, so the Report Viewer's secondary linked-trade/equity fetch 404s and the whole page is classified `error_or_degraded` even though the scorecard first-screen is fully data. Fix options: (a) point LinkedTradeLog at the report pack `series.json` instead of `/runs/{id}/report`, or (b) have `evaluate` also persist a runs-ledger record + series sidecar. **Recorded, not fixed (src/ out of scope).**
- **P1-b — Strategy-asset detail resolves to `four_layer`, which has no candidate/run**, so its candidate/report block is empty even though three other strategies DO have candidates. The audit resolves `:name` from `GET /strategies[0]`; a deterministic "prefer a strategy with a candidate" resolver would make the detail page's data state more representative. Audit-spec-only improvement (in scope for a follow-up).
- **P2-a — Runs ledger family (`/research/runs`, `/research/runs/:id`, `/trades`, `/research/compare`) stays empty/degraded** because evaluate does not populate the runs ledger. These are the pre-rebuild surfaces; low priority, but seeding a run via `run-is` (needs `data/parquet` + would attempt a DB mirror) would light them up if desired.
- **P2-b — All Monitor telemetry pages are `empty` (`data_source: pending`)** — no daemon feed in this environment. Honest onboarding state; not a redesign defect.
- **P2-c — `/live-oos/watch` empty** — no Paper-Watch berth seeded (would need a `deployment_strict` / `truth_gate` PAPER_WATCH verdict, which is minutes-scale and out of the quick-triage seed).

## Verification status

- Audit Playwright run (`e2e/audit/screenshot.config.ts`) → **PASS**, 69/69 screenshot entries + 3/3 redirect records (9.4 min).
- `npx tsc --noEmit` (incl. updated audit spec) → **0 errors**.
- All 69 screenshots > 10 KB, non-blank; zero JS page errors; states identical across all three viewports.
- **Global acceptance #9 (screenshot audit passes after redesign for desktop/laptop/mobile) — PASS.**
