/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 5173,
    // doc 25：後端裸根 5 前綴。dev 期把 API 前綴代理到 FastAPI，前端只打相對路徑。
    proxy: {
      '/runs': 'http://localhost:8000',
      '/research': 'http://localhost:8000',
      '/monitor': 'http://localhost:8000',
      '/system': 'http://localhost:8000',
      '/home': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      // bare-root prefixes that also serve real endpoints (doc 25). Without these,
      // FE fetches to /gate/spec etc. hit the SPA fallback (HTML/404) — see e2e
      // endpoint-audit F1: /research/validate was dead on /gate/spec 404.
      '/gate': 'http://localhost:8000',
      '/presets': 'http://localhost:8000',
      '/metrics': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
})
