/*
 * DsrRuler：三 band 各自的 badge + 指針定位，以及 truth_gate=null 的空態（不畫假指針）。
 * 精確定位百分比由 lib/reportViz.dsrToPercent 的單元測試守（此處驗帶別 + 指針存在/缺席）。
 */
import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { DsrRuler } from './DsrRuler'
import { dsrToPercent } from '../lib/reportViz'
import type { TruthGateBerth } from '../api/report'

afterEach(cleanup)

function berth(verdict_dsr: number, band: string): TruthGateBerth {
  return { verdict_dsr, band, source: 'watch_registry' }
}

describe('DsrRuler', () => {
  it('REAL band: shows the REAL badge, a needle, and positions it at dsrToPercent', () => {
    render(<DsrRuler truthGate={berth(0.97, 'REAL')} />)
    expect(screen.getByText(/REAL/)).toBeInTheDocument()
    const needle = screen.getByTestId('dsr-needle')
    expect(needle).toBeInTheDocument()
    expect(needle.style.left).toBe(`${dsrToPercent(0.97)}%`)
  })

  it('PAPER_WATCH band: shows the PAPER_WATCH badge and a needle', () => {
    render(<DsrRuler truthGate={berth(0.92, 'PAPER_WATCH')} />)
    expect(screen.getByText(/PAPER_WATCH/)).toBeInTheDocument()
    expect(screen.getByTestId('dsr-needle')).toBeInTheDocument()
  })

  it('REJECTED band: shows the REJECTED badge and a needle', () => {
    render(<DsrRuler truthGate={berth(0.88, 'REJECTED')} />)
    expect(screen.getByText(/REJECTED/)).toBeInTheDocument()
    expect(screen.getByTestId('dsr-needle')).toBeInTheDocument()
  })

  it('null truth gate: shows the empty state and draws no needle', () => {
    render(<DsrRuler truthGate={null} />)
    expect(screen.getByText(/尚無真偽閘證據/)).toBeInTheDocument()
    expect(screen.queryByTestId('dsr-needle')).not.toBeInTheDocument()
  })

  it('null verdict_dsr: still an empty state, no fabricated needle', () => {
    render(<DsrRuler truthGate={{ verdict_dsr: null, band: null }} />)
    expect(screen.queryByTestId('dsr-needle')).not.toBeInTheDocument()
  })
})
