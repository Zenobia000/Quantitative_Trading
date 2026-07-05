/*
 * Endpoint-audit Playwright config (standalone).
 *
 * Local (multi-session): assumes uvicorn:8000 + vite are already running. The
 * webServer below has `reuseExistingServer: !CI`, so locally it reuses whatever
 * vite is already on AUDIT_PORT (no port collision, matching prior behaviour).
 * CI: `process.env.CI` is set, so Playwright boots a fresh vite dev server on
 * AUDIT_PORT and waits for it before running specs. The backend (uvicorn:8000)
 * must still be provided separately by the E2E job — this config only owns vite.
 *
 * Run: AUDIT_BASE_URL=http://localhost:5174 npx playwright test \
 *        --config e2e/audit/playwright.config.ts
 */
import { defineConfig, devices } from '@playwright/test'
import { fileURLToPath } from 'node:url'

// 5173 is often held by a parallel dev session, so the audit lane defaults to 5174.
const PORT = Number(process.env.AUDIT_PORT ?? 5174)
const baseURL = process.env.AUDIT_BASE_URL ?? `http://localhost:${PORT}`
// vite lives in frontend/; this config is frontend/e2e/audit/ → up two levels.
const frontendRoot = fileURLToPath(new URL('../..', import.meta.url))

export default defineConfig({
  testDir: '.',
  testMatch: /endpoint-audit\.spec\.ts/,
  fullyParallel: false,
  workers: 1, // single worker — deterministic, shared backend state
  retries: 0,
  timeout: 60_000,
  reporter: [['list'], ['json', { outputFile: 'results/playwright-report.json' }]],
  use: {
    baseURL,
    extraHTTPHeaders: { Authorization: 'Bearer dev-token' },
    trace: 'retain-on-failure',
  },
  webServer: {
    command: `npm run dev -- --port ${PORT} --strictPort`,
    url: baseURL,
    cwd: frontendRoot,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
