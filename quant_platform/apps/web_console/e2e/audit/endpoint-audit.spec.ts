/*
 * Frontend endpoint connectivity audit (GET-on-mount sweep).
 *
 * Goal: for every routed page, render it in a real booted SPA and faithfully
 * record EVERY backend API call React Query fires on mount — raw. No judgment
 * here; classification/reconciliation happens downstream (workflow).
 *
 * CRITICAL — why client-side navigation: the vite dev proxy forwards the SPA
 * route prefixes (/research /monitor /system /runs /home) to FastAPI. A direct
 * page.goto('/research/runs') is therefore proxied to the backend as a *document*
 * request (404 / raw JSON) and the SPA never boots. So we boot once at '/', then
 * navigate CLIENT-SIDE (nav-link click, or history pushState for parametric
 * routes). The response listener counts only xhr/fetch, never document loads.
 *
 * Parametric routes (/runs/:id, /promote/:id) resolve a real id at runtime from
 * the live /runs and /research/strategies lists, so detail pages actually load.
 */
import { test, expect, type APIRequestContext } from '@playwright/test'
import { writeFileSync, mkdirSync } from 'node:fs'
import { dirname } from 'node:path'

const API_RE = /^\/(runs|research|monitor|system|home|health|gate|presets|metrics|ws)(\/|\?|$)/

interface ApiCall {
  method: string
  path: string
  resourceType: string
  status: number
  ok: boolean
  success: boolean | null
  error: unknown
  dataSource: string | null
  dataEmpty: boolean | null
  bodySample: string
}
interface RouteResult {
  route: string
  title: string
  zone: string
  resolvedFrom?: string
  navMethod: 'click' | 'pushState'
  finalUrl: string
  urlMatches: boolean
  consoleErrors: string[]
  pageErrors: string[]
  apiCalls: ApiCall[]
}

const SETTLE_MS = 2800

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
    if (Array.isArray(arr) && arr.length > 0) return String(arr[0][key] ?? '')
  } catch {
    /* ignore */
  }
  return null
}

test('endpoint connectivity audit — GET-on-mount sweep over all routes', async ({ page, request }) => {
  test.setTimeout(180_000)

  const runId = (await resolveId(request, '/runs', 'run_id')) ?? 'NO_RUN_SEEDED'
  const strategyId = (await resolveId(request, '/research/strategies', 'strategy_id')) ?? 's1'

  const routes: Array<{ route: string; title: string; zone: string; resolvedFrom?: string }> = [
    { route: '/', title: '首頁 cockpit', zone: 'home' },
    { route: '/research/strategies', title: '策略庫', zone: 'research' },
    { route: '/research/runs/new', title: 'New Run', zone: 'research' },
    { route: '/research/runs', title: 'Runs Table', zone: 'research' },
    { route: `/research/runs/${runId}`, title: 'Run Report', zone: 'research', resolvedFrom: `runId=${runId}` },
    { route: `/research/runs/${runId}/trades`, title: '逐筆覆盤', zone: 'research', resolvedFrom: `runId=${runId}` },
    { route: '/research/compare', title: 'Compare', zone: 'research' },
    { route: '/research/sweep', title: 'Sweep', zone: 'research' },
    { route: '/research/validate', title: 'Validate gate', zone: 'research' },
    { route: `/research/promote/${strategyId}`, title: 'Promote', zone: 'research', resolvedFrom: `strategyId=${strategyId}` },
    { route: '/monitor', title: '艦隊總控', zone: 'monitor' },
    { route: '/monitor/performance', title: '績效總覽', zone: 'monitor' },
    { route: '/monitor/positions', title: '部位狀態', zone: 'monitor' },
    { route: '/monitor/signals', title: '訊號日誌', zone: 'monitor' },
    { route: '/monitor/risk', title: '風控指標', zone: 'monitor' },
    { route: '/system/data', title: '資料管理', zone: 'system' },
    { route: '/system/alerts', title: '告警設定', zone: 'system' },
  ]

  const results: RouteResult[] = []
  let bucket: ApiCall[] = []
  let consoleErrors: string[] = []
  let pageErrors: string[] = []

  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text().slice(0, 200))
  })
  page.on('pageerror', (err) => pageErrors.push(String(err).slice(0, 200)))
  page.on('response', async (res) => {
    const rt = res.request().resourceType()
    if (rt !== 'xhr' && rt !== 'fetch') return // ignore document/script/etc — only real API calls
    let url: URL
    try {
      url = new URL(res.url())
    } catch {
      return
    }
    if (!API_RE.test(url.pathname)) return
    const status = res.status()
    let raw = ''
    let parsed: { success?: boolean; error?: unknown; data?: unknown; meta?: { data_source?: string } } | null = null
    try {
      raw = await res.text()
      parsed = JSON.parse(raw)
    } catch {
      /* non-json */
    }
    bucket.push({
      method: res.request().method(),
      path: url.pathname + url.search,
      resourceType: rt,
      status,
      ok: status >= 200 && status < 300,
      success: parsed?.success ?? null,
      error: parsed?.error ?? null,
      dataSource: parsed?.meta?.data_source ?? null,
      dataEmpty: parsed ? classifyEmpty(parsed.data) : null,
      bodySample: raw.slice(0, 240),
    })
  })

  // Boot the SPA once at root (only un-proxied path), wait for shell + nav.
  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('a[href="/research/runs"]', { timeout: 30_000 })
  await page.waitForTimeout(SETTLE_MS) // capture home's own mount fetches

  // record root result from the boot
  results.push({
    route: '/',
    title: '首頁 cockpit',
    zone: 'home',
    navMethod: 'pushState',
    finalUrl: page.url(),
    urlMatches: new URL(page.url()).pathname === '/',
    consoleErrors: [...consoleErrors],
    pageErrors: [...pageErrors],
    apiCalls: [...bucket],
  })

  for (const r of routes) {
    if (r.route === '/') continue
    bucket = []
    consoleErrors = []
    pageErrors = []

    // prefer a real nav-link click (RRv7 intercepts); fall back to history API
    // for parametric / non-sidebar routes.
    const link = page.locator(`a[href="${r.route}"]`).first()
    let navMethod: 'click' | 'pushState'
    if ((await link.count()) > 0) {
      navMethod = 'click'
      await link.click()
    } else {
      navMethod = 'pushState'
      await page.evaluate((p) => {
        window.history.pushState({}, '', p)
        window.dispatchEvent(new PopStateEvent('popstate'))
      }, r.route)
    }
    await page.waitForTimeout(SETTLE_MS)

    const finalPath = new URL(page.url()).pathname
    results.push({
      route: r.route,
      title: r.title,
      zone: r.zone,
      resolvedFrom: r.resolvedFrom,
      navMethod,
      finalUrl: page.url(),
      urlMatches: finalPath === r.route,
      consoleErrors: [...consoleErrors],
      pageErrors: [...pageErrors],
      apiCalls: [...bucket],
    })
  }

  const out = {
    note: 'client-side-nav capture; only xhr/fetch recorded. Timestamp injected by caller.',
    baseURL: test.info().project.use.baseURL,
    resolvedRunId: runId,
    resolvedStrategyId: strategyId,
    routeCount: routes.length,
    routes: results,
  }
  const outPath = 'e2e/audit/results/capture.json'
  mkdirSync(dirname(outPath), { recursive: true })
  writeFileSync(outPath, JSON.stringify(out, null, 2))

  expect(results.length).toBe(routes.length)
})
