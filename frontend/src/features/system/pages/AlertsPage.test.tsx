import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { AlertsPage } from './AlertsPage'

function mockByPath(byPath: Record<string, unknown>) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const path = new URL(url, 'http://x').pathname
      const data = Object.entries(byPath).find(([p]) => path.endsWith(p))?.[1] ?? []
      return { status: 200, json: async () => ({ success: true, data, error: null, meta: { ttl: 300 } }) }
    }) as unknown as typeof fetch,
  )
}
function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AlertsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
afterEach(() => vi.unstubAllGlobals())

describe('AlertsPage', () => {
  it('renders built-in alert rules + risk-spec count + masked channel', async () => {
    mockByPath({
      '/system/alerts/rules': [{ rule_id: 'EX-001', level: 'CRITICAL', title: '單筆上限' }],
      '/system/risk/spec': { rules: new Array(12).fill({}) },
      // shipped：channels GET 回傳遮罩後的 discord 設定（bot_token 一律 ***）
      '/system/alerts/channels': { discord: { enabled: false, bot_token: '***' } },
    })
    renderPage()
    await waitFor(() => expect(screen.getByText('EX-001')).toBeInTheDocument())
    expect(screen.getByText('CRITICAL')).toBeInTheDocument()
    expect(screen.getByText('風控規格 12 條')).toBeInTheDocument()
    expect(screen.getByText(/Discord 未啟用/)).toBeInTheDocument()
    expect(screen.getByText(/bot_token: \*\*\*/)).toBeInTheDocument()
  })
})
