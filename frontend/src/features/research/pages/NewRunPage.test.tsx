import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { NewRunPage } from './NewRunPage'

afterEach(() => vi.unstubAllGlobals())

describe('NewRunPage', () => {
  it('填假設 + 提交 → POST /runs（strategy+params，ADR-028；無 preset）', async () => {
    // GET /strategies → 型錄陣列；POST /runs → run_id（依 URL/method 路由）
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      const u = String(url)
      if (u.includes('/optimization-schema'))
        return {
          status: 200,
          json: async () => ({ success: true, data: { strategy: 'four_layer', config_schema: {}, optimization: null }, error: null, meta: {} }),
        }
      if (u.includes('/strategies') && (!init || init.method !== 'POST'))
        return {
          status: 200,
          json: async () => ({
            success: true,
            data: [
              {
                name: 'four_layer',
                title: 'Four-Layer Resonance',
                description: '',
                config_schema: {
                  properties: {
                    box_period: { type: 'integer', default: 60, description: 'box window' },
                    ranking_mode: {
                      anyOf: [{ const: 'long_only' }, { const: 'market_neutral' }, { type: 'null' }],
                      default: 'long_only',
                    },
                  },
                },
              },
            ],
            error: null,
            meta: {},
          }),
        }
      return {
        status: 200,
        json: async () => ({ success: true, data: { run_id: 'run_new1' }, error: null, meta: {} }),
      }
    })
    vi.stubGlobal('fetch', fetchMock as unknown as typeof fetch)

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={['/research/runs/new']}>
          <NewRunPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    fireEvent.change(screen.getByPlaceholderText(/N-of-4/), { target: { value: '放寬進場驗 Sharpe' } })
    await screen.findByText('box_period')
    fireEvent.change(screen.getByDisplayValue('60'), { target: { value: '80' } })
    fireEvent.change(screen.getByDisplayValue('long_only'), { target: { value: 'market_neutral' } })
    fireEvent.click(screen.getByText('提交回測'))

    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([, init]) => (init as RequestInit)?.method === 'POST')).toBe(true),
    )
    const postCall = fetchMock.mock.calls.find(([, init]) => (init as RequestInit)?.method === 'POST') as unknown as [
      string,
      RequestInit,
    ]
    expect(postCall[0]).toContain('/runs')
    const body = JSON.parse(postCall[1].body as string)
    expect(body.hypothesis).toBe('放寬進場驗 Sharpe')
    expect(body.strategy).toBe('four_layer')
    expect(body.params).toEqual({ box_period: 80, ranking_mode: 'market_neutral' })
    expect(body).not.toHaveProperty('preset') // ADR-028：廢棄欄位不得再送
    // Slice 2：預設股票池 → 不送 stocks / universe（後端解析系統預設）
    expect(body).not.toHaveProperty('stocks')
    expect(body).not.toHaveProperty('universe')
  })

  it('選具名股票池 → body 帶 universe id（ADR-007 Slice 2）', async () => {
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      const u = String(url)
      if (u.includes('/optimization-schema'))
        return {
          status: 200,
          json: async () => ({ success: true, data: { strategy: 'four_layer', config_schema: {}, optimization: null }, error: null, meta: {} }),
        }
      if (u.includes('/system/universes'))
        return {
          status: 200,
          json: async () => ({
            success: true,
            data: [{ id: 'parquet_finlab_universe', name: 'liquid-top200', symbols_count: 200, strategies: [] }],
            error: null,
            meta: {},
          }),
        }
      if (u.includes('/strategies') && (!init || init.method !== 'POST'))
        return {
          status: 200,
          json: async () => ({ success: true, data: [{ name: 'four_layer', title: 'FL', description: '', config_schema: {} }], error: null, meta: {} }),
        }
      return { status: 200, json: async () => ({ success: true, data: { run_id: 'run_u1' }, error: null, meta: {} }) }
    })
    vi.stubGlobal('fetch', fetchMock as unknown as typeof fetch)

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={['/research/runs/new']}>
          <NewRunPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    fireEvent.change(screen.getByPlaceholderText(/N-of-4/), { target: { value: 'h' } })
    await screen.findByRole('option', { name: /liquid-top200/ })
    fireEvent.change(screen.getByDisplayValue(/系統預設股票池/), { target: { value: 'parquet_finlab_universe' } })
    fireEvent.click(screen.getByText('提交回測'))

    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([, init]) => (init as RequestInit)?.method === 'POST')).toBe(true),
    )
    const postCall = fetchMock.mock.calls.find(([, init]) => (init as RequestInit)?.method === 'POST') as unknown as [string, RequestInit]
    const body = JSON.parse(postCall[1].body as string)
    expect(body.universe).toBe('parquet_finlab_universe')
    expect(body).not.toHaveProperty('stocks')
  })

  it('讀 DOE optimization schema → 可覆寫 grid 後提交 workflow job', async () => {
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      const u = String(url)
      if (u.includes('/optimization-schema'))
        return {
          status: 200,
          json: async () => ({
            success: true,
            data: {
              strategy: 'momentum',
              config_schema: {},
              optimization: {
                workflow: 'doe',
                grid: { lookback_days: [126, 252], skip_days: [0, 21] },
                n_configs: 4,
                is_start: '2020-01-01',
                is_end: '2024-12-31',
                symbols_count: 3,
                symbols_preview: ['2330'],
              },
            },
            error: null,
            meta: {},
          }),
        }
      if (u.includes('/strategies') && (!init || init.method !== 'POST'))
        return {
          status: 200,
          json: async () => ({ success: true, data: [{ name: 'momentum', title: 'Momentum', description: '', config_schema: {} }], error: null, meta: {} }),
        }
      return { status: 202, json: async () => ({ success: true, data: { job_id: 'job_doe', status: 'queued' }, error: null, meta: {} }) }
    })
    vi.stubGlobal('fetch', fetchMock as unknown as typeof fetch)

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={['/research/runs/new?strategy=momentum']}>
          <NewRunPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    await screen.findByText('參數最佳化 · DOE grid')
    fireEvent.change(screen.getByDisplayValue('126,252'), { target: { value: '63,126,252' } })
    fireEvent.click(screen.getByText('提交 DOE 最佳化'))

    await waitFor(() => expect(screen.getByText(/job_doe/)).toBeInTheDocument())
    const postCall = fetchMock.mock.calls.find(([url, init]) => String(url).includes('/research/workflows/doe') && (init as RequestInit)?.method === 'POST') as unknown as [string, RequestInit]
    const body = JSON.parse(postCall[1].body as string)
    expect(body.strategy).toBe('momentum')
    expect(body.overrides.grid.lookback_days).toEqual([63, 126, 252])
    expect(body.overrides.grid.skip_days).toEqual([0, 21])
  })
})
