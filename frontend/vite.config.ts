/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import type { ProxyOptions } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'
import type { IncomingMessage } from 'node:http'

// doc 25：後端裸根前綴。dev 期把 API 前綴代理到 FastAPI，前端只打相對路徑。
const API_TARGET = 'http://localhost:8000'
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

const apiProxy: Record<string, ProxyOptions> = {}
for (const p of API_PREFIXES) apiProxy[p] = { target: API_TARGET, changeOrigin: true, bypass: spaBypass }
apiProxy['/ws'] = { target: 'ws://localhost:8000', ws: true }

// https://vitejs.dev/config/
export default defineConfig({
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
  },
})
