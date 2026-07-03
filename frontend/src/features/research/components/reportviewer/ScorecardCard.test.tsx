/*
 * ScorecardCard：狀態燈 + 各指標計數；整卡 not_available 顯示原因（不留無說明佔位）；點卡回呼。
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { ScorecardCard } from './ScorecardCard'
import type { Scorecard } from '../../api/reportViewer'

afterEach(cleanup)

const PROFITABILITY: Scorecard = {
  category: 'profitability',
  status: 'warn',
  metrics: [
    { id: 'cagr', label: 'CAGR', value: 0.16, unit: 'fraction', threshold: 0.18, op: '>', status: 'warn', severity: 'info', source_module: 'm' },
    { id: 'tr', label: 'Total return', value: 4.31, unit: 'fraction', threshold: null, op: null, status: 'pass', severity: 'info', source_module: 'm' },
    { id: 'alpha', label: 'Alpha', value: null, unit: 'fraction', threshold: null, op: null, status: 'not_available', severity: 'info', source_module: null, reason: 'no benchmark' },
  ],
}

const WIN_RATE: Scorecard = {
  category: 'win_rate',
  status: 'not_available',
  note: 'Whole scorecard is not_available for panel strategies (no per-trade pnl).',
  metrics: [
    { id: 'twr', label: 'Trade win rate', value: null, unit: 'fraction', threshold: null, op: null, status: 'not_available', severity: 'info', source_module: null, reason: 'no pnl' },
  ],
}

describe('ScorecardCard', () => {
  it('shows the category label, overall status light and per-status counts', () => {
    render(<ScorecardCard scorecard={PROFITABILITY} active={false} onSelect={() => {}} />)
    expect(screen.getByText('獲利能力')).toBeInTheDocument()
    // warn overall + 1 pass / 1 warn / 1 not_available 計數
    const card = screen.getByTestId('scorecard-profitability')
    expect(within(card).getByText(/1 通過/)).toBeInTheDocument()
    expect(within(card).getByText(/1 無法產出/)).toBeInTheDocument()
  })

  it('honestly explains a not_available card instead of leaving a blank placeholder', () => {
    render(<ScorecardCard scorecard={WIN_RATE} active={false} onSelect={() => {}} />)
    const card = screen.getByTestId('scorecard-win_rate')
    expect(within(card).getByText('無法產出')).toBeInTheDocument()
    expect(within(card).getByText(/no per-trade pnl/)).toBeInTheDocument()
  })

  it('fires onSelect and reflects the active state via aria-pressed', () => {
    const onSelect = vi.fn()
    render(<ScorecardCard scorecard={PROFITABILITY} active onSelect={onSelect} />)
    const card = screen.getByTestId('scorecard-profitability')
    expect(card).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(card)
    expect(onSelect).toHaveBeenCalledOnce()
  })
})
