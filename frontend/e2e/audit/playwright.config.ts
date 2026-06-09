/*
 * Endpoint-audit Playwright config (standalone).
 * Assumes uvicorn:8000 + vite are already running (multi-session safe — does NOT
 * spawn its own webServer to avoid port collisions). Target the running vite via
 * AUDIT_BASE_URL; defaults to 5174 (5173 is often held by a parallel session).
 *
 * Run: AUDIT_BASE_URL=http://localhost:5174 npx playwright test \
 *        --config e2e/audit/playwright.config.ts
 */
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: '.',
  testMatch: /endpoint-audit\.spec\.ts/,
  fullyParallel: false,
  workers: 1, // single worker — deterministic, shared backend state
  retries: 0,
  timeout: 60_000,
  reporter: [['list'], ['json', { outputFile: 'results/playwright-report.json' }]],
  use: {
    baseURL: process.env.AUDIT_BASE_URL ?? 'http://localhost:5174',
    extraHTTPHeaders: { Authorization: 'Bearer dev-token' },
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
