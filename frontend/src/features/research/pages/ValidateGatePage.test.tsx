import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { ValidateGatePage } from './ValidateGatePage'

afterEach(() => vi.unstubAllGlobals())

describe('ValidateGatePage', () => {
  it('GET /gate/spec → 渲染 IS gate 硬門檻 criteria', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        status: 200,
        json: async () => ({
          success: true,
          data: {
            criteria: [{ key: 'sharpe', op: '>', threshold: 1.0, kind: 'edge', label: 'K2 Sharpe>1.0' }],
          },
          error: null,
          meta: {},
        }),
      })) as unknown as typeof fetch,
    )
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <ValidateGatePage />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    await waitFor(() => expect(screen.getByText('K2 Sharpe>1.0')).toBeInTheDocument())
    expect(screen.getByText(/sharpe > 1/)).toBeInTheDocument()
  })
})
