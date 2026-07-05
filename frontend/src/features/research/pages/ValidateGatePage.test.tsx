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

  it('run_id 選定後渲染 13 指標健康表（green/na 燈號、缺漏不判綠）', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        const u = String(url)
        let data: unknown = {}
        if (u.includes('/health')) {
          data = {
            rows: [
              { key: 'sharpe', label: 'Sharpe Ratio', value: 1.3, light: 'green' },
              { key: 'win_rate', label: '勝率', value: null, light: 'na' },
            ],
            counts: { green: 1, yellow: 0, red: 0, na: 1 },
            all_green: false,
          }
        } else if (u.includes('/wfa')) {
          data = { folds: [], scatter: [], criteria: {} }
        } else if (u.includes('/gate-state')) {
          data = { validation_status: 'DRAFT', stage: 'IS', history: [] }
        } else {
          data = { criteria: [] } // /gate/spec
        }
        return { status: 200, json: async () => ({ success: true, data, error: null, meta: {} }) }
      }) as unknown as typeof fetch,
    )
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={['/deploy/gate?run_id=run_x']}>
          <ValidateGatePage />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    // 真實 health 投影：Sharpe 綠燈、缺漏的勝率顯示 NA（不靜默判綠）
    await waitFor(() => expect(screen.getByText('Sharpe Ratio')).toBeInTheDocument())
    expect(screen.getByText('GREEN')).toBeInTheDocument()
    expect(screen.getByText('NA')).toBeInTheDocument()
  })
})
