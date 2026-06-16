import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { DataPage } from './DataPage'

function mockApi() {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const path = new URL(url, 'http://x').pathname
      let data: unknown = []
      if (path === '/system/ingest' && init?.method === 'POST') data = { job_id: 'j1', status: 'queued' }
      else if (path.startsWith('/system/ingest/')) data = { job_id: 'j1', status: 'done', result: { requested: 2, ok: ['2330'], failed: ['2317'] } }
      else if (path === '/system/bundles') return { status: 200, json: async () => ({ success: true, data: [], error: null, meta: { data_source: 'pending' } }) }
      return { status: 200, json: async () => ({ success: true, data, error: null, meta: { ttl: 60 } }) }
    }) as unknown as typeof fetch,
  )
}
function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <DataPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
afterEach(() => vi.unstubAllGlobals())

describe('DataPage', () => {
  it('ingest form submits → shows job id + polls status to done', async () => {
    mockApi()
    renderPage()
    fireEvent.click(screen.getByText('開始 Ingest'))
    await waitFor(() => expect(screen.getByText('j1')).toBeInTheDocument())
    await waitFor(() => expect(screen.getByText('done')).toBeInTheDocument())
    expect(screen.getByText(/ok 1 \/ failed 1/)).toBeInTheDocument()
  })

  it('bundle manifest pending → PendingNote', async () => {
    mockApi()
    renderPage()
    await waitFor(() => expect(screen.getByText(/bundle manifest/)).toBeInTheDocument())
  })
})
