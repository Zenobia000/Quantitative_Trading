/*
 * Screenshot / UX audit Playwright config (standalone, rebuild Goal 0).
 *
 * Sibling of playwright.config.ts (endpoint-audit). Owns only the screenshot
 * sweep spec. Assumes a vite dev server is already running on AUDIT_PORT
 * (default 5174, strictPort) whose proxy points at the chosen FastAPI backend.
 * reuseExistingServer=!CI so it reuses whatever vite the auditor already booted;
 * it never kills a parallel session's server.
 *
 * Run: AUDIT_BASE_URL=http://localhost:5174 \
 *        npx playwright test --config e2e/audit/screenshot.config.ts
 */
import { defineConfig, devices } from '@playwright/test'
import { fileURLToPath } from 'node:url'

const PORT = Number(process.env.AUDIT_PORT ?? 5174)
const baseURL = process.env.AUDIT_BASE_URL ?? `http://localhost:${PORT}`
const frontendRoot = fileURLToPath(new URL('../..', import.meta.url))

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
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
