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
      if (String(url).includes('/strategies') && (!init || init.method !== 'POST'))
        return {
          status: 200,
          json: async () => ({
            success: true,
            data: [{ name: 'four_layer', title: 'Four-Layer Resonance', description: '', config_schema: {} }],
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
    expect(body).not.toHaveProperty('preset') // ADR-028：廢棄欄位不得再送
    // Slice 2：預設股票池 → 不送 stocks / universe（後端解析系統預設）
    expect(body).not.toHaveProperty('stocks')
    expect(body).not.toHaveProperty('universe')
  })

  it('選具名股票池 → body 帶 universe id（ADR-007 Slice 2）', async () => {
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      const u = String(url)
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
})
