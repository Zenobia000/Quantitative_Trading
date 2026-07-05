/*
 * Full-site screenshot + UX audit sweep.
 *
 * Two waves share this spec:
 *   - Goal 0 baseline (current-state, 20 routes) → dev_docs/ui_audit/current_2026-07-03/
 *   - Wave E rebuild rerun (post-redesign, all actual routes) → dev_docs/ui_audit/rebuild_2026-07-03/
 * The output dir is AUDIT_OUT_DIR-overridable (default = the rebuild dir), so the same
 * spec re-runs against either baseline without an edit.
 *
 * For every ACTUAL route in src/router.tsx (reconciled against the five-zone IA:
 * research / live-oos / deployment / monitor / system), at three viewports, this boots
 * a fresh SPA via a real document navigation (vite's spaBypass serves index.html for
 * text/html Accept on API-prefixed deep links) and records, per route×viewport:
 *   - resolved URL, viewport
 *   - a full-page screenshot (nonblank, visually inspectable)
 *   - console errors, page errors
 *   - every xhr/fetch API call on mount (method/path/status/success/data_source/empty)
 *   - a derived data-source + observed-state summary
 *
 * Redirect routes (research/validate → deploy/gate, research/promote/:id →
 * deploy/promote/:id, monitor/watch → live-oos/watch) are recorded once (redirect
 * behaviour only) in `manifest.redirects`, NOT screenshotted × 3 (they render the
 * same page as their target).
 *
 * Parametric routes resolve real ids from the live API (GET /runs → run_id,
 * GET /strategies → registry name, GET /research/candidates → latest_evaluation_id for
 * the Report Viewer); unresolved ids fall back and are recorded.
 *
 * Output → AUDIT_OUT_DIR (manifest.json, api_capture.json, screenshots/{desktop,laptop,
 * mobile}/). GET-only: no write-action buttons are clicked. This spec never edits src or
 * app config.
 */
import { test, expect, type APIRequestContext, type Page } from '@playwright/test'
import { writeFileSync, mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { join } from 'node:path'

const OUT_DIR =
  process.env.AUDIT_OUT_DIR ??
  fileURLToPath(new URL('../../../dev_docs/ui_audit/rebuild_2026-07-03/', import.meta.url))

const VIEWPORTS = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'laptop', width: 1280, height: 800 },
  { name: 'mobile', width: 390, height: 844 },
] as const

// xhr/fetch paths that count as "API on mount" (backend bare-root prefixes).
const API_RE = /^\/(runs|research|monitor|system|home|health|gate|presets|metrics|strategies|ws)(\/|\?|$)/
const SETTLE_MS = 2600

interface ApiCall {
  method: string
  path: string
  status: number
  ok: boolean
  success: boolean | null
  error: unknown
  dataSource: string | null
  dataEmpty: boolean | null
}
interface ManifestEntry {
  route: string
  slug: string
  title: string
  resolvedUrl: string
  urlMatches: boolean
  viewport: string
  viewportSize: { width: number; height: number }
  screenshot: string
  headingText: string | null
  observedState: string
  isNotFound: boolean
  dataSources: string[]
  consoleErrors: string[]
  pageErrors: string[]
  apiCalls: ApiCall[]
  resolvedFrom?: string
}
interface RedirectRecord {
  route: string
  slug: string
  title: string
  expectedTarget: string
  resolvedUrl: string
  resolvedPath: string
  redirected: boolean
  matchedExpectedTarget: boolean
  resolvedFrom?: string
}

function classifyEmpty(data: unknown): boolean | null {
  if (data === undefined) return null
  if (data === null) return true
  if (Array.isArray(data)) return data.length === 0
  if (typeof data === 'object') return Object.keys(data as object).length === 0
  return false
}

async function resolveId(req: APIRequestContext, path: string, key: string): Promise<string | null> {
  try {
    const r = await req.get(path)
    const j = await r.json()
    const arr = j?.data
    if (Array.isArray(arr) && arr.length > 0) {
      const v = arr[0][key]
      return v == null ? null : String(v)
    }
  } catch {
    /* ignore */
  }
  return null
}

test('screenshot + UX audit — all routes x 3 viewports', async ({ browser, request }) => {
  test.setTimeout(1_200_000)

  // --- resolve parametric ids from the live API (or documented fallback) ------
  const runIdReal = await resolveId(request, '/runs', 'run_id')
  const runId = runIdReal ?? 'NO_RUN_SEEDED'
  // Report Viewer (/research/reports/:runId) keys on an EVALUATION id, resolved from the
  // seeded candidate pool's latest_evaluation_id (evaluate CLI writes evaluations.jsonl).
  const reportIdReal = await resolveId(request, '/research/candidates', 'latest_evaluation_id')
  const reportId = reportIdReal ?? 'NO_EVAL_SEEDED'
  // strategy hub detail keys on the registry catalog name (GET /strategies).
  const stratNameReal = await resolveId(request, '/strategies', 'name')
  const stratName = stratNameReal ?? 'momentum'
  // promote keys on strategy_id from the runs-projection roster (empty w/o runs).
  const promoteIdReal = await resolveId(request, '/research/strategies', 'strategy_id')
  const promoteId = promoteIdReal ?? stratName

  const runFrom = runIdReal ? `GET /runs → run_id=${runId}` : `fallback (GET /runs empty) → ${runId}`
  const reportFrom = reportIdReal
    ? `GET /research/candidates → latest_evaluation_id=${reportId}`
    : `fallback (candidate pool empty) → ${reportId}`
  const nameFrom = stratNameReal
    ? `GET /strategies → name=${stratName}`
    : `fallback (GET /strategies unreachable) → ${stratName}`
  const promoteFrom = promoteIdReal
    ? `GET /research/strategies → strategy_id=${promoteId}`
    : `fallback (roster empty) → strategy_id=${promoteId}`

  // --- the ACTUAL screenshot route table (reconciled against src/router.tsx) --
  // Five-zone IA: research / live-oos / deployment / monitor / system. Redirect
  // routes are handled separately (see redirectRoutes below).
  const routes: Array<{ slug: string; route: string; title: string; resolvedFrom?: string }> = [
    { slug: 'home', route: '/', title: '首頁 cockpit' },
    // Research zone
    { slug: 'research_strategies', route: '/research/strategies', title: '策略中心（Strategy Hub list）' },
    {
      slug: 'research_strategies_detail',
      route: `/research/strategies/${encodeURIComponent(stratName)}`,
      title: '策略中心 · 詳情（策略資產 detail）',
      resolvedFrom: nameFrom,
    },
    { slug: 'research_candidates', route: '/research/candidates', title: '候選池 Candidate Pool（NEW — 決策主戰場）' },
    { slug: 'research_runs_new', route: '/research/runs/new', title: 'New Run 設定' },
    { slug: 'research_runs', route: '/research/runs', title: 'Runs Table' },
    { slug: 'research_runs_id', route: `/research/runs/${encodeURIComponent(runId)}`, title: 'Run Report（舊）', resolvedFrom: runFrom },
    {
      slug: 'research_reports_id',
      route: `/research/reports/${encodeURIComponent(reportId)}`,
      title: 'Report Viewer（NEW — FinLab scorecard 報告）',
      resolvedFrom: reportFrom,
    },
    {
      slug: 'research_runs_id_trades',
      route: `/research/runs/${encodeURIComponent(runId)}/trades`,
      title: '逐筆覆盤 Trade Review',
      resolvedFrom: runFrom,
    },
    { slug: 'research_compare', route: '/research/compare', title: 'Compare' },
    { slug: 'research_sweep', route: '/research/sweep', title: 'Sweep' },
    // Live OOS zone (NEW — human-selected expensive OOS journey)
    { slug: 'live_oos_queue', route: '/live-oos/queue', title: 'OOS 佇列 Live-OOS Queue（NEW）' },
    { slug: 'live_oos_watch', route: '/live-oos/watch', title: 'Paper-Watch 觀察艙（moved from monitor）' },
    // Deployment zone (NEW — strict gate + capital promotion, journey 3)
    { slug: 'deploy_gate', route: '/deploy/gate', title: '部署嚴格閘 Strict Gate（NEW zone）' },
    {
      slug: 'deploy_promote_id',
      route: `/deploy/promote/${encodeURIComponent(promoteId)}`,
      title: '晉升 Promote（NEW zone）',
      resolvedFrom: promoteFrom,
    },
    // Monitor zone
    { slug: 'monitor', route: '/monitor', title: '策略艦隊總控 Fleet' },
    { slug: 'monitor_board', route: '/monitor/board', title: '運行看板 Board（now wired — was dead-404 in Goal 0）' },
    { slug: 'monitor_performance', route: '/monitor/performance', title: '績效總覽' },
    { slug: 'monitor_positions', route: '/monitor/positions', title: '部位狀態' },
    { slug: 'monitor_signals', route: '/monitor/signals', title: '訊號日誌' },
    { slug: 'monitor_risk', route: '/monitor/risk', title: '風控指標' },
    // System zone
    { slug: 'system_data', route: '/system/data', title: '資料管理 Data' },
    { slug: 'system_alerts', route: '/system/alerts', title: '告警設定 Alerts' },
  ]

  // Redirect routes — recorded once (redirect behaviour only), not screenshotted × 3.
  const redirectRoutes: Array<{ slug: string; route: string; title: string; expectedTarget: string; resolvedFrom?: string }> = [
    { slug: 'redirect_research_validate', route: '/research/validate', title: 'Validate → Deployment', expectedTarget: '/deploy/gate' },
    {
      slug: 'redirect_research_promote',
      route: `/research/promote/${encodeURIComponent(promoteId)}`,
      title: 'Promote → Deployment',
      expectedTarget: `/deploy/promote/${promoteId}`,
      resolvedFrom: promoteFrom,
    },
    { slug: 'redirect_monitor_watch', route: '/monitor/watch', title: 'Paper-Watch → Live OOS', expectedTarget: '/live-oos/watch' },
  ]

  const manifest: {
    generatedAt: string
    baseURL: string | undefined
    backend: string
    resolvedIds: { runId: string; reportEvaluationId: string; strategyName: string; promoteId: string }
    viewports: typeof VIEWPORTS
    screenshotRouteCount: number
    redirectRouteCount: number
    entries: ManifestEntry[]
    redirects: RedirectRecord[]
  } = {
    generatedAt: new Date().toISOString(),
    baseURL: test.info().project.use.baseURL,
    backend: process.env.AUDIT_BACKEND ?? 'http://127.0.0.1:8083 (worktree uvicorn, seeded reports/) via vite proxy',
    resolvedIds: { runId, reportEvaluationId: reportId, strategyName: stratName, promoteId },
    viewports: VIEWPORTS,
    screenshotRouteCount: routes.length,
    redirectRouteCount: redirectRoutes.length,
    entries: [],
    redirects: [],
  }

  mkdirSync(OUT_DIR, { recursive: true })
  for (const vp of VIEWPORTS) mkdirSync(join(OUT_DIR, 'screenshots', vp.name), { recursive: true })

  const writeManifest = () => writeFileSync(join(OUT_DIR, 'manifest.json'), JSON.stringify(manifest, null, 2))

  for (const vp of VIEWPORTS) {
    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
      deviceScaleFactor: 1,
      extraHTTPHeaders: { Authorization: 'Bearer dev-token' },
    })
    const page: Page = await context.newPage()

    let bucket: ApiCall[] = []
    let consoleErrors: string[] = []
    let pageErrors: string[] = []

    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text().slice(0, 240))
    })
    page.on('pageerror', (err) => pageErrors.push(String(err).slice(0, 240)))
    page.on('response', async (res) => {
      const rt = res.request().resourceType()
      if (rt !== 'xhr' && rt !== 'fetch') return
      let url: URL
      try {
        url = new URL(res.url())
      } catch {
        return
      }
      if (!API_RE.test(url.pathname)) return
      const status = res.status()
      let parsed: { success?: boolean; error?: unknown; data?: unknown; meta?: { data_source?: string } } | null = null
      try {
        parsed = JSON.parse(await res.text())
      } catch {
        /* non-json (e.g. proxy 404 html) */
      }
      bucket.push({
        method: res.request().method(),
        path: url.pathname + url.search,
        status,
        ok: status >= 200 && status < 300,
        success: parsed?.success ?? null,
        error: parsed?.error ?? null,
        dataSource: parsed?.meta?.data_source ?? null,
        dataEmpty: parsed ? classifyEmpty(parsed.data) : null,
      })
    })

    for (const r of routes) {
      bucket = []
      consoleErrors = []
      pageErrors = []

      await page.goto(r.route, { waitUntil: 'domcontentloaded' })
      // shell nav proves the SPA booted (vs. a proxied backend document)
      await page.waitForSelector('nav a', { timeout: 15_000 }).catch(() => {})
      await page.waitForLoadState('networkidle', { timeout: 8_000 }).catch(() => {})
      await page.waitForTimeout(SETTLE_MS)

      const probe = await page.evaluate(() => {
        const h1 = document.querySelector('h1')?.textContent?.trim() ?? null
        // NotFoundPage renders a Placeholder whose route line text is exactly "404"
        const notFound = Array.from(document.querySelectorAll('p')).some((p) => p.textContent?.trim() === '404')
        return { h1, notFound }
      })

      const shot = join('screenshots', vp.name, `${r.slug}.png`)
      await page.screenshot({ path: join(OUT_DIR, shot), fullPage: true })

      const dataSources = [...new Set(bucket.map((c) => c.dataSource).filter((s): s is string => !!s))]
      const anyErr = bucket.some((c) => !c.ok || c.success === false)
      const allEmpty = bucket.length > 0 && bucket.every((c) => c.dataEmpty === true || c.dataEmpty === null)
      const observedState = probe.notFound
        ? 'not_found'
        : anyErr
          ? 'error_or_degraded'
          : bucket.length === 0
            ? 'static_no_api'
            : allEmpty
              ? 'empty'
              : 'data'

      const finalPath = new URL(page.url()).pathname
      manifest.entries.push({
        route: r.route,
        slug: r.slug,
        title: r.title,
        resolvedUrl: page.url(),
        urlMatches: finalPath === r.route,
        viewport: vp.name,
        viewportSize: { width: vp.width, height: vp.height },
        screenshot: shot,
        headingText: probe.h1,
        observedState,
        isNotFound: probe.notFound,
        dataSources,
        consoleErrors: [...consoleErrors],
        pageErrors: [...pageErrors],
        apiCalls: [...bucket],
        resolvedFrom: r.resolvedFrom,
      })
      writeManifest()
    }

    // Redirect routes — desktop context only: record the redirect target, no screenshot.
    if (vp.name === 'desktop') {
      for (const rr of redirectRoutes) {
        await page.goto(rr.route, { waitUntil: 'domcontentloaded' })
        await page.waitForSelector('nav a', { timeout: 15_000 }).catch(() => {})
        await page.waitForLoadState('networkidle', { timeout: 8_000 }).catch(() => {})
        await page.waitForTimeout(800)
        const resolvedPath = new URL(page.url()).pathname
        manifest.redirects.push({
          route: rr.route,
          slug: rr.slug,
          title: rr.title,
          expectedTarget: rr.expectedTarget,
          resolvedUrl: page.url(),
          resolvedPath,
          redirected: resolvedPath !== rr.route,
          matchedExpectedTarget: resolvedPath === rr.expectedTarget,
          resolvedFrom: rr.resolvedFrom,
        })
        writeManifest()
      }
    }

    await context.close()
  }

  // api_capture.json: route → api-calls-on-mount (desktop pass = canonical),
  // preserving the "endpoint audit" artifact shape alongside the richer manifest.
  const desktop = manifest.entries.filter((e) => e.viewport === 'desktop')
  const apiCapture = {
    generatedAt: manifest.generatedAt,
    baseURL: manifest.baseURL,
    backend: manifest.backend,
    note: 'API-on-mount capture from the desktop screenshot pass; xhr/fetch only.',
    resolvedIds: manifest.resolvedIds,
    routes: desktop.map((e) => ({
      route: e.route,
      title: e.title,
      resolvedUrl: e.resolvedUrl,
      observedState: e.observedState,
      dataSources: e.dataSources,
      apiCalls: e.apiCalls,
    })),
  }
  writeFileSync(join(OUT_DIR, 'api_capture.json'), JSON.stringify(apiCapture, null, 2))

  writeManifest()
  expect(manifest.entries.length).toBe(routes.length * VIEWPORTS.length)
  expect(manifest.redirects.length).toBe(redirectRoutes.length)
})
