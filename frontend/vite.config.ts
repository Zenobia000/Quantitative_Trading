/// <reference types="vitest/config" />
import { defineConfig, loadEnv } from 'vite'
import type { ProxyOptions } from 'vite'
import { configDefaults } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'node:path'
import type { IncomingMessage } from 'node:http'

// doc 25：後端裸根前綴。dev 期把 API 前綴代理到 FastAPI，前端只打相對路徑。
const API_PREFIXES = ['/runs', '/research', '/monitor', '/system', '/home', '/health', '/gate', '/presets', '/metrics']

// A browser *document* navigation (Accept: text/html) to a SPA route that shares
// an API prefix (/research/validate, /monitor/...) must boot the SPA, NOT be
// proxied to FastAPI (which would 404 {"detail":"Not Found"}). XHR/fetch
// (Accept: application/json) falls through (returns undefined) and is proxied.
// Fixes dev-mode deep-link / hard-refresh on every non-root page.
function spaBypass(req: IncomingMessage): string | undefined {
  const accept = req.headers.accept ?? ''
  if (accept.includes('text/html')) return '/index.html'
  return undefined
}

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Dev-server-only var (not a client `VITE_` var — the browser keeps hitting
  // relative paths so requests flow through this proxy). Lets the FastAPI target
  // port be overridden from an untracked frontend/.env when :8000 is taken on a
  // shared host, without editing this tracked file. Defaults to :8000.
  const env = loadEnv(mode, process.cwd(), '')
  const apiTarget = env.DEV_API_PROXY_TARGET || 'http://localhost:8000'
  const wsTarget = apiTarget.replace(/^http/, 'ws')

  const apiProxy: Record<string, ProxyOptions> = {}
  for (const p of API_PREFIXES) apiProxy[p] = { target: apiTarget, changeOrigin: true, bypass: spaBypass }
  apiProxy['/ws'] = { target: wsTarget, ws: true }

  return {
    plugins: [react()],
    resolve: {
      alias: { '@': path.resolve(__dirname, './src') },
    },
    server: {
      port: 5173,
      proxy: apiProxy,
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: './src/test/setup.ts',
      // e2e/ holds Playwright specs (run via `npm run test:e2e`), not vitest — vitest
      // would try to collect them and fail on Playwright's test() runner.
      exclude: [...configDefaults.exclude, 'e2e/**'],
    },
  }
})
