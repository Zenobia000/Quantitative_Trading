import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { DatasetCatalog } from './DatasetCatalog'

// mock cards use the real /system/datasets shape (api.gen.ts DatasetCard):
// {key, name_zh, category, freq, history_start, description, local, used_by}
const CARDS = [
  {
    key: 'etl:adj_close',
    name_zh: '還原收盤價',
    category: 'price_volume',
    freq: '日',
    history_start: '2007',
    description: '除權息還原後收盤價',
    local: 'cached',
    used_by: ['four_layer', 'momentum'],
  },
  {
    key: 'institutional_investors_trading_summary:投信買賣超股數',
    name_zh: '投信買賣超',
    category: 'institutional',
    freq: '日',
    history_start: '2012',
    description: '投信買賣超股數',
    local: 'not_cached',
    used_by: [],
  },
  {
    key: 'monthly_revenue:當月營收',
    name_zh: '當月營收',
    category: 'monthly_revenue',
    freq: '月',
    history_start: '2007',
    description: '每月10日前公告之單月營收',
    local: 'cached',
    used_by: ['revenue_growth'],
  },
]

function mockApi(cards: unknown[] = CARDS) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const path = new URL(url, 'http://x').pathname
      if (path === '/system/datasets')
        return {
          status: 200,
          json: async () => ({ success: true, data: cards, error: null, meta: { data_source: 'catalog', ttl: 300 } }),
        }
      return { status: 200, json: async () => ({ success: true, data: [], error: null, meta: { ttl: 60 } }) }
    }) as unknown as typeof fetch,
  )
}

function renderCatalog() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <DatasetCatalog />
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('DatasetCatalog', () => {
  it('renders every catalog card from the full snapshot', async () => {
    mockApi()
    renderCatalog()
    await waitFor(() => expect(screen.getByText('還原收盤價')).toBeInTheDocument())
    expect(screen.getByText('etl:adj_close')).toBeInTheDocument()
    expect(screen.getByText('投信買賣超')).toBeInTheDocument()
    expect(screen.getByText('當月營收')).toBeInTheDocument()
  })

  it('category chip filters to a single category (client-side)', async () => {
    mockApi()
    renderCatalog()
    await waitFor(() => expect(screen.getByText('還原收盤價')).toBeInTheDocument())
    // 法人 chip → only the institutional card remains
    fireEvent.click(screen.getByRole('button', { name: '法人' }))
    expect(screen.getByText('投信買賣超')).toBeInTheDocument()
    expect(screen.queryByText('還原收盤價')).not.toBeInTheDocument()
    expect(screen.queryByText('當月營收')).not.toBeInTheDocument()
  })

  it('search matches description (not just key/name)', async () => {
    mockApi()
    renderCatalog()
    await waitFor(() => expect(screen.getByText('還原收盤價')).toBeInTheDocument())
    // "公告" appears only in the monthly-revenue *description*, nowhere in key/name
    fireEvent.change(screen.getByLabelText('搜尋資料 key、名稱或說明…'), { target: { value: '公告' } })
    expect(screen.getByText('當月營收')).toBeInTheDocument()
    expect(screen.queryByText('還原收盤價')).not.toBeInTheDocument()
    expect(screen.queryByText('投信買賣超')).not.toBeInTheDocument()
  })

  it('shows cached vs not_cached states honestly (no fake download button)', async () => {
    mockApi()
    renderCatalog()
    await waitFor(() => expect(screen.getByText('投信買賣超')).toBeInTheDocument())
    expect(screen.getAllByText('本地已有').length).toBeGreaterThan(0) // cached cards
    expect(screen.getByText('未下載')).toBeInTheDocument() // not_cached card
    // honest UI: no fabricated "download" action rendered
    expect(screen.queryByText('下載到本地')).not.toBeInTheDocument()
  })

  it('renders used_by chips only when a strategy references the key', async () => {
    mockApi()
    renderCatalog()
    await waitFor(() => expect(screen.getByText('還原收盤價')).toBeInTheDocument())
    expect(screen.getByText('four_layer')).toBeInTheDocument()
    expect(screen.getByText('momentum')).toBeInTheDocument()
    // 2 of 3 cards have used_by → exactly 2 ⚡ rows (institutional card has none)
    expect(screen.getAllByText('⚡')).toHaveLength(2)
  })

  it('copy button writes the key to the clipboard and confirms', async () => {
    const writeText = vi.fn()
    Object.assign(navigator, { clipboard: { writeText } })
    mockApi()
    renderCatalog()
    await waitFor(() => expect(screen.getByText('還原收盤價')).toBeInTheDocument())
    // first card (etl:adj_close) copy button
    const card = screen.getByText('etl:adj_close').closest('div')?.parentElement as HTMLElement
    fireEvent.click(within(card).getByRole('button', { name: '複製 key' }))
    expect(writeText).toHaveBeenCalledWith('etl:adj_close')
    await waitFor(() => expect(screen.getByText('已複製')).toBeInTheDocument())
  })

  it('empty search result → explicit no-match state (not blank)', async () => {
    mockApi()
    renderCatalog()
    await waitFor(() => expect(screen.getByText('還原收盤價')).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText('搜尋資料 key、名稱或說明…'), { target: { value: 'zzz-nope' } })
    expect(screen.getByText(/找不到符合/)).toBeInTheDocument()
    expect(screen.queryByText('還原收盤價')).not.toBeInTheDocument()
  })

  it('empty catalog → typed-empty label, no fabricated cards', async () => {
    mockApi([])
    renderCatalog()
    await waitFor(() => expect(screen.getByText('資料目錄為空')).toBeInTheDocument())
  })
})
