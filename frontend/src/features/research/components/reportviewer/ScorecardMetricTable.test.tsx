/*
 * ScorecardMetricTable：每指標一列（狀態燈 + 原始值 + 門檻 + 出處/原因）——「不只有數字」（UX 驗收 #2）；
 * not_available 指標顯示原因（不留無說明佔位 UX 驗收 #3）；fraction 值 ×100 加 %。
 */
import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { ScorecardMetricTable } from './ScorecardMetricTable'
import type { Scorecard } from '../../api/reportViewer'

afterEach(cleanup)

const RISK_ADJUSTED: Scorecard = {
  category: 'risk_adjusted',
  status: 'warn',
  metrics: [
    { id: 'sharpe', label: 'Sharpe (IS)', value: 1.025, unit: 'ratio', threshold: 1.0, op: '>', status: 'pass', severity: 'info', source_module: 'validation.metrics.sharpe' },
    { id: 'calmar', label: 'Calmar', value: 0.58, unit: 'ratio', threshold: null, op: null, status: 'warn', severity: 'info', source_module: 'm' },
    { id: 'pf', label: 'Profit factor', value: null, unit: 'ratio', threshold: null, op: null, status: 'not_available', severity: 'info', source_module: null, reason: 'panel trades is a rebalance count, no per-trade pnl' },
  ],
}

describe('ScorecardMetricTable', () => {
  it('renders per-metric status light, raw value and threshold (not just numbers)', () => {
    render(<ScorecardMetricTable scorecard={RISK_ADJUSTED} />)
    expect(screen.getByText('Sharpe (IS)')).toBeInTheDocument()
    expect(screen.getByText('1.025')).toBeInTheDocument() // raw value
    expect(screen.getByText('> 1')).toBeInTheDocument() // threshold op+value
    expect(screen.getByText('通過')).toBeInTheDocument() // pass light label
    expect(screen.getByText('警示')).toBeInTheDocument() // warn light label
  })

  it('shows a reason for a not_available metric instead of a blank cell', () => {
    render(<ScorecardMetricTable scorecard={RISK_ADJUSTED} />)
    expect(screen.getByText('無法產出')).toBeInTheDocument()
    expect(screen.getByText(/no per-trade pnl/)).toBeInTheDocument()
  })
})
