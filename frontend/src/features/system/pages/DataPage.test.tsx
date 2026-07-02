import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { DataPage } from './DataPage'

const BUNDLE_ROWS = [
  {
    id: 'parquet',
    path: 'data/parquet',
    kind: 'default',
    stock_count: 10,
    coverage_start: '2020-01-02',
    coverage_end: '2024-12-31',
    strategy: null,
  },
  {
    id: 'parquet_finlab_universe',
    path: 'data/parquet_finlab_universe',
    kind: 'universe',
    stock_count: 423,
    coverage_start: '2010-01-01',
    coverage_end: '2024-12-31',
    strategy: 'inst_flow',
  },
]

function mockApi(bundles: unknown[] = BUNDLE_ROWS) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const path = new URL(url, 'http://x').pathname
      let data: unknown = []
      if (path === '/system/ingest' && init?.method === 'POST') data = { job_id: 'j1', status: 'queued' }
      else if (path.startsWith('/system/ingest/'))
        data = { job_id: 'j1', status: 'done', result: { requested: 2, ok: ['2330'], failed: ['2317'] } }
      else if (path === '/system/universe/build' && init?.method === 'POST') data = { job_id: 'u1', status: 'queued' }
      else if (path.startsWith('/system/universe/build/'))
        data = { job_id: 'u1', status: 'done', result: { n_symbols: 423, n_alive: 400, n_delisted: 23 } }
      else if (path === '/system/bundles')
        return {
          status: 200,
          json: async () => ({ success: true, data: bundles, error: null, meta: { data_source: 'parquet_scan', total: bundles.length } }),
        }
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

  it('universe build form submits → shows job id + polls status to done', async () => {
    mockApi()
    renderPage()
    fireEvent.click(screen.getByText('開始建置'))
    await waitFor(() => expect(screen.getByText('u1')).toBeInTheDocument())
    await waitFor(() => expect(screen.getByText('done')).toBeInTheDocument())
    expect(screen.getByText(/423 檔/)).toBeInTheDocument()
  })

  it('bundle list renders real scanned rows (default + universe)', async () => {
    mockApi()
    renderPage()
    await waitFor(() => expect(screen.getByText('parquet_finlab_universe')).toBeInTheDocument())
    expect(screen.getByText('inst_flow')).toBeInTheDocument()
    expect(screen.getByText('423')).toBeInTheDocument()
  })

  it('empty bundle scan → typed-empty label, no fabricated rows', async () => {
    mockApi([])
    renderPage()
    await waitFor(() => expect(screen.getByText(/尚無 bundle/)).toBeInTheDocument())
  })
})
