/*
 * MonthlyHeatmap：cell 著色（正 pos / 負 neg / null|0 none），null cell 顯示破折號、
 * 真實 0.0% 與無資料讀法不同，以及 monthly=null 的空態。
 */
import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { MonthlyHeatmap } from './MonthlyHeatmap'
import type { MonthlyReturns } from '../api/report'

afterEach(cleanup)

// 一列 2023：Jan +5% / Feb -2% / Mar null（無觀察）/ Apr 0.0（真實平月），其餘 null。
const MONTHLY: MonthlyReturns = {
  years: [2023],
  matrix: [[0.05, -0.02, null, 0, null, null, null, null, null, null, null, null]],
  annual: [0.03],
  basis: 'reconstructed_business_days_from_is_start',
}

describe('MonthlyHeatmap', () => {
  it('tints cells by sign (pos / neg / none) and keeps null distinct from a real 0%', () => {
    const { container } = render(<MonthlyHeatmap monthly={MONTHLY} note={null} />)
    const cells = container.querySelectorAll('td[data-sign]')
    expect(cells[0].getAttribute('data-sign')).toBe('pos') // +5%
    expect(cells[0].className).toContain('text-gain')
    expect(cells[1].getAttribute('data-sign')).toBe('neg') // -2%
    expect(cells[1].className).toContain('text-loss-aaa')
    expect(cells[2].getAttribute('data-sign')).toBe('none') // null → no tint
    expect(cells[2].textContent).toBe('—') // no-data reads as a dash
    expect(cells[3].getAttribute('data-sign')).toBe('none') // real 0.0% → no tint…
    expect(cells[3].textContent).toBe('0.0%') // …but a value, never a dash
  })

  it('renders the annual total and the business-day basis hint', () => {
    render(<MonthlyHeatmap monthly={MONTHLY} note={null} />)
    expect(screen.getByText('3.0%')).toBeInTheDocument() // annual
    expect(screen.getByText(/business-day 近似/)).toBeInTheDocument()
  })

  it('shows the empty state (with backend note when present) for null monthly', () => {
    render(<MonthlyHeatmap monthly={null} note="series sidecar not persisted" />)
    expect(screen.getByText('series sidecar not persisted')).toBeInTheDocument()
  })
})
