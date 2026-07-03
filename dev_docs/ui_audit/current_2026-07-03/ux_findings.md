# Current UX / API Audit — Findings (rebuild Goal 0)

> **Date:** 2026-07-03  
> **Branch / worktree:** `chore/ui-audit-baseline` @ base `d3971ca` (origin/main, F-wave strategy-hub #181 merged)  
> **Spec:** `rebuild_goal_spec_ai_requirements_2026-07-03.md` §2 (Current-State Audit) + §8 (operating rules)  
> **Method:** Playwright full-page screenshot sweep + xhr/fetch capture-on-mount. Fresh SPA boot per route via `page.goto` (vite `spaBypass` serves `index.html` for `text/html` deep links). GET-only — no write-action buttons clicked.  
> **Frontend:** self-hosted vite dev @ `:5174` (strictPort), relative paths → vite proxy.  
> **Backend:** shared `127.0.0.1:8080` uvicorn (`v0.6.0`). Its `api/` code is **byte-identical** to this worktree (`git diff d3971ca f057db2 -- .../api/` is empty), so the API surface matches the audited frontend.  
> **Artifacts:** `manifest.json` (60 entries = 20 routes × 3 viewports), `api_capture.json`, `screenshots/{desktop,laptop,mobile}/`, plus the pre-existing endpoint audit at `frontend/e2e/audit/results/capture.json`.

## Coverage & environment caveats

- **20 routes × 3 viewports (desktop 1440×900 / laptop 1280×800 / mobile 390×844) = 60 screenshots.** All present, all > 10 KB, all visually non-blank (spot-checked).
- **Observed states** (desktop pass): `data` ×8, `empty` ×6, `error_or_degraded` ×5, `not_found` ×1 (`/monitor/board`), `static_no_api` ×1 (`/research/compare`). Full per-viewport in `manifest.json`.
- **Data starvation is the dominant caveat.** The backend has **zero runs** (`GET /runs` → `[]`), **zero ingested bundles** (`GET /system/bundles` → `[]`), and monitor telemetry is `data_source: "pending"` (no daemon feed). So most "default" states are genuinely empty/onboarding, and the flagship **Run Report cannot be screenshotted in a data state** — only its 404/error state exists. This is honestly recorded, not an audit-tool failure. Populated content only exists on config-driven pages (`system/data`, `system/alerts`, `research/validate`, `research/sweep`) and the home onboarding shell.
- **Parametric-id resolution:** `run_id` → fallback `NO_RUN_SEEDED` (ledger empty); strategy-detail `:name` → fallback `four_layer` (see finding #1 — `GET /strategies` is unreachable through the dev proxy); promote `:strategyId` → fallback `four_layer` (roster empty). All fallbacks recorded in `manifest.resolvedIds` + per-entry `resolvedFrom`.

## Spec route list vs. actual router (mapping deltas)

The spec §2.2 predates the F-wave merge. Reconciled against `src/router.tsx`:

| Spec route | Actual state | Note |
| :--- | :--- | :--- |
| `/research/strategies` | **Renamed component** → `StrategyHubListPage` | `StrategyLibraryPage` **retired** in #181. Same path; data source is now the **registry catalog** (`GET /strategies`) × runs × watch, not a pure run projection. |
| — (not in spec) | **NEW route** `/research/strategies/:name` → `StrategyHubDetailPage` | Strategy-asset detail surface (the Goal 7 direction) **partially already exists**. |
| `/monitor/board` | **DEAD ROUTE → renders 404** | `nav.ts` + the `REAL` element map both reference `BoardPage`, but the router's `ROUTES` array **omits `monitor/board`**, so the nav link falls through to `NotFoundPage`. Bug, not a redesign choice. |
| `/research/runs/:id` (Run Report) | Endpoints exist, data-state **unverifiable** | Run-Report v1 aggregate (`/runs/:id/report`) shipped, but no seeded run → only the 404 error state is observable. Spec §3.3's "weak Run Report" is directionally still true but **cannot be confirmed** from this baseline. |
| other 16 routes | Present as listed | — |

**Outdated spec §3.3 assumptions:** (a) "Strategy Library is a registry/run projection" — the F-wave hub is now **strategy-axis / registry-catalog-driven**, so the IA shift the spec calls for has *started*; it still lacks hypothesis/mechanism/next-action, so Goal 7 remains valid. (b) "Run Report has 6 KPI + pending tear sheet" — the report *endpoint* now exists (v1), but strength is unverifiable here.

## Per-page findings (one row per actual route)

| Page (route) | Current purpose | UX problems | Data / API problems | Reuse recommendation | Priority |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/` | Cross-zone cockpit + "start first strategy" onboarding | Ribbon is workflow-centric (`假設→回測→比較→守門→晉升`), not asset/report/candidate-centric per rebuild mission | `/home/recent` + `/home/research-status` OK (`ledger`, empty→onboarding) | **reuse** — shell + onboarding are good; re-point CTAs to new IA | P2 |
| `/research/strategies` | Strategy-axis catalog (registry × runs × watch) | **Renders a hard red error banner** (`策略載入失敗 404`), so the strategy entry point looks broken in dev | **`GET /strategies` → 404 via dev proxy** (see #1); list cannot populate at all | **refactor** — IA direction is right; fix proxy, then add hypothesis/status/next-action (Goal 7) | **P0 (dev-broken)** / P1 redesign |
| `/research/strategies/:name` | Per-strategy aggregate: catalog header + verdict timeline + watch pod | Degrades gracefully (`不在型錄中` + `尚無 run`), but header/config/hypothesis are blank | `GET /strategies` 404 → no title/config/schema; `/runs` empty → empty timeline; `/monitor/watch` empty | **refactor** — solid skeleton for the Goal 7 strategy-asset detail; needs registry + report + candidate wiring | P1 |
| `/research/runs/new` | Run authoring form (hypothesis → strategy → params → cost → period) | Strategy field falls back to a manual text default because the picker's catalog 404s; two `待後端` placeholder bands (config-schema param form, cost model) | `GET /strategies` 404 → catalog picker degraded (form still usable) | **reuse/refactor** — form is strong; wire `config_schema` params; will be wrapped by evaluation-profile surface (Goal 3) | P1 |
| `/research/runs` | Verdict ledger table | Clean empty state, no issues | `GET /runs` → `[]` | **reuse** — fine as ledger; becomes secondary evidence in new IA | P2 |
| `/research/runs/:id` | **Run Report** (the rebuild's flagship report experience) | Only the 404/error state is observable (no seeded run); graceful `載入失敗 找不到資源 (404)` | `/runs/:id`, `/runs/:id/report` → 404 on fallback id; `/equity` `pending` | **replace/refactor** — this is the Goal 5 Report Viewer rebuild target (scorecards / sheets / linked trades / decisions) | **P0 (core rebuild)** |
| `/research/runs/:id/trades` | Per-trade drilldown (candles + equity + trades) | Only error state observable | `/runs/:id/candles` → 404 on fallback id | **reuse** — `CandlestickChart` is the evidence-drilldown component (spec §3.2) | P2 |
| `/research/compare` | Multi-run delta comparison | **Inert on bare mount — zero API calls** (waits for `?run_ids=`); a blank shell if entered from nav | none until `run_ids` supplied | **reuse/refactor** — fine, but should be entered from report/candidate, not bare nav | P2 |
| `/research/sweep` | Parameter-sweep config + estimate | Renders; no issues | `/runs/estimate` OK | **reuse** — optional `grid_search` primitive (spec §3.1) | P2 |
| `/research/validate` | Two-stage gate spec viewer | Surfaced as a **primary Research nav item**; spec §6/§8 say the strict gate must not be the first research experience | `/gate/spec` OK | **reuse but reposition** — move under a Deployment profile, not front-and-center | P1 (reposition) |
| `/research/promote/:strategyId` | Promotion flow + audit trail | Renders default `晉升流程`; promote framing sits inside Research | `/research/promote/:id` + `/audit` OK (default); roster empty | **reuse but reposition** — belongs in a separate Deployment zone (Goal 1) | P1 (reposition) |
| `/monitor` | Strategy fleet control | Empty; no issues | `/monitor/fleet` + `/portfolio-summary` `pending` (no daemon) | **reuse** | P2 |
| `/monitor/board` | (intended run board) | **BROKEN — renders `找不到頁面 / 404`**; nav highlights `運行看板` but no page loads | none (route not wired) | **fix wiring** — add `monitor/board` to router `ROUTES`, or remove the nav item | **P1 (visible broken link)** |
| `/monitor/watch` | Paper-Watch observation pods | Empty; no issues | `/monitor/watch` `watch_registry`, empty | **reuse** — concepts feed the Live-OOS queue (Goal 10) | P1 (feeds Live OOS) |
| `/monitor/performance` | Equity / KPI performance overview | Empty | `/performance/equity` + `/kpi` `pending` | **reuse** | P2 |
| `/monitor/positions` | Position snapshot | Empty | `/positions/snapshot` `pending` | **reuse** | P2 |
| `/monitor/signals` | Signal / fill log | Empty | `/signals` + `/fills` `pending` | **reuse** | P2 |
| `/monitor/risk` | Risk metrics | Empty | `/risk/metrics` `pending` | **reuse** | P2 |
| `/system/data` | Data dictionary / **data-card wall** | **Richest data-state page** — cards, search, category filters, `本地已有` status, strategy-usage tags | `/system/datasets` (`catalog`) OK; `/system/bundles` (`parquet_scan`) empty | **reuse** — strong; aligns with authoring-first "data card = strategy-author dictionary" | P2 |
| `/system/alerts` | Alert rules + channels + risk spec | Renders fully | `/alerts/rules` + `/alerts/channels` + `/risk/spec` OK | **reuse** | P2 |

## Top 5 cross-cutting UX problems

1. **`/strategies` 404 through the dev proxy breaks the whole strategy-authoring entry in local dev.** `vite.config.ts` `API_PREFIXES` omits `/strategies` (it lists `/runs /research /monitor /system /home /health /gate /presets /metrics`). The backend serves `GET /strategies` fine (11 KB), but the browser hits a relative path that vite doesn't proxy → 404. This kills the Strategy Hub list (hard error banner), blanks the strategy-detail header, and degrades the NewRun strategy picker. *Masked in production only if the deploy proxy / `VITE_API_BASE` forwards `/strategies`.* **Out of scope to patch here** (audit may not edit `vite.config.ts`); recorded as the top defect. Fix = add `/strategies` to `API_PREFIXES`.
2. **`/monitor/board` is a dead nav link → 404.** `nav.ts` and the `REAL` element map reference `BoardPage`, but the router's `ROUTES` array never registers `monitor/board`, so it falls to `NotFoundPage`. One-line wiring fix or remove the nav item.
3. **The flagship Run Report has no data-state baseline.** With zero seeded runs, only the graceful 404 error state is observable. The Goal 5 Report Viewer rebuild proceeds without a current before-image — seed at least one run (or ship deterministic fixtures per spec §4.3) before/while redesigning so the "after" is comparable.
4. **The app is data-starved (12/20 routes render empty/onboarding).** No runs, no ingested bundle, monitor telemetry `pending`. Redesign screenshots will be unconvincing until seeded fixtures exist; this also means empty/loading/error states are currently the *only* states for much of Monitor + Research detail.
5. **IA is still workflow/gate-centric, not asset/report/candidate-centric.** Home's `假設→回測→比較→守門→晉升` ribbon, plus `validate` and `promote` sitting as primary Research nav items, contradict the rebuild mission (spec §5–§6: strict gate must be repositioned as a deployment profile, not the first research experience). The F-wave strategy hub is the one place the new axis has started.

## Blockers (explicit, per spec §8.6)

- **`/strategies` dev-proxy 404** — cannot capture Strategy Hub list / NewRun picker in a true data state without editing `vite.config.ts` (out of scope for this audit). `not_available` reason: proxy prefix gap.
- **Zero seeded runs + no ingested bundle** — Run Report, Trade Review, Runs Table, Compare, and all Monitor telemetry pages `not_available` in data state. Reason: empty ledger / no daemon / no parquet bundle. Config-driven pages and onboarding are unaffected.
- Both are **environment/data limits, not tool failures**, and are recorded per-route in `manifest.json` (`observedState` + `dataSources` + `apiCalls[].status`).

## Verification status

- `npm run build` → **pass** (`tsc --noEmit` 0 errors + `vite build` OK).
- `npx tsc --noEmit` (incl. new audit specs) → **0 errors**.
- Existing endpoint audit (`e2e/audit/playwright.config.ts`) → **still passes** (17 routes captured to `results/capture.json`).
- New screenshot audit (`e2e/audit/screenshot.config.ts`) → **passes**, 60/60 entries.
