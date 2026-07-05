/*
 * Screenshot / UX audit Playwright config (standalone).
 *
 * Sibling of playwright.config.ts (endpoint-audit). Owns only the screenshot
 * sweep spec. Assumes a vite dev server is already running on AUDIT_PORT
 * (default 5176, strictPort) whose proxy points at the chosen FastAPI backend
 * (DEV_API_PROXY_TARGET, default the shared-host audit backend on :8083).
 * reuseExistingServer=!CI so it reuses whatever vite the auditor already booted;
 * it never kills a parallel session's server (shared-host rule: :5173/:8080 are
 * another session's — the Wave-E rerun uses :5176 + :8083).
 *
 * Run: DEV_API_PROXY_TARGET=http://localhost:8083 AUDIT_PORT=5176 \
 *        npx playwright test --config e2e/audit/screenshot.config.ts
 */
import { defineConfig, devices } from '@playwright/test'
import { fileURLToPath } from 'node:url'

const PORT = Number(process.env.AUDIT_PORT ?? 5176)
const baseURL = process.env.AUDIT_BASE_URL ?? `http://localhost:${PORT}`
const frontendRoot = fileURLToPath(new URL('../..', import.meta.url))
const proxyTarget = process.env.DEV_API_PROXY_TARGET ?? 'http://localhost:8083'

export default defineConfig({
  testDir: '.',
  testMatch: /screenshot-audit\.spec\.ts/,
  fullyParallel: false,
  workers: 1, // single worker — deterministic, one shared backend
  retries: 0,
  timeout: 1_200_000, // 60 loads x 3 viewports; generous ceiling
  reporter: [['list']],
  use: {
    baseURL,
    extraHTTPHeaders: { Authorization: 'Bearer dev-token' },
    trace: 'off',
  },
  webServer: {
    command: `npm run dev -- --port ${PORT} --strictPort`,
    url: baseURL,
    cwd: frontendRoot,
    env: { DEV_API_PROXY_TARGET: proxyTarget },
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
