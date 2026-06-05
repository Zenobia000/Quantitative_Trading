import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { NewRunPage } from './NewRunPage'

afterEach(() => vi.unstubAllGlobals())

describe('NewRunPage', () => {
  it('填假設 + 提交 → POST /runs', async () => {
    const fetchMock = vi.fn(async () => ({
      status: 200,
      json: async () => ({ success: true, data: { run_id: 'run_new1' }, error: null, meta: {} }),
    }))
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

    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toContain('/runs')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string).hypothesis).toBe('放寬進場驗 Sharpe')
  })
})
