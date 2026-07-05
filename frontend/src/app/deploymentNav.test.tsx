/*
 * Codex-style operations console IA:
 * nav 以 golden 七層產品子系統為一等區域；舊 Live OOS / Deployment
 * 語義收斂到 Governance。舊 URL 仍保留 client redirect。
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { NAV } from '@/app/nav'
import { GateRedirect, PromoteRedirect } from '@/app/redirects'

describe('nav — Governance release migration', () => {
  const zones = Object.fromEntries(NAV.map((z) => [z.zone, z]))

  it('moves strict gate under governance', () => {
    expect(zones.governance).toBeDefined()
    const tos = zones.governance.items.map((i) => i.to)
    expect(tos).toContain('/deploy/gate')
  })

  it('does not surface promote as a nav item (per-strategy detail route)', () => {
    const allTos = NAV.flatMap((z) => z.items.map((i) => i.to))
    expect(allTos.some((to) => to.startsWith('/deploy/promote'))).toBe(false)
  })

  it('removes validate from the research zone (it moved to Deployment)', () => {
    const researchTos = zones.research.items.map((i) => i.to)
    expect(researchTos).not.toContain('/research/validate')
  })

  it('orders zones Data → Research → Governance → Trading → Risk → Operations → System', () => {
    expect(NAV.map((z) => z.zone)).toEqual([
      'data',
      'research',
      'governance',
      'trading',
      'risk',
      'operations',
      'system',
    ])
  })
})

describe('route — /research/validate redirects to /deploy/gate (query preserved)', () => {
  it('lands on the gate destination carrying ?run_id=', async () => {
    const router = createMemoryRouter(
      [
        { path: '/research/validate', element: <GateRedirect /> },
        { path: '/deploy/gate', element: <div>gate destination</div> },
      ],
      { initialEntries: ['/research/validate?run_id=abc'] },
    )
    render(<RouterProvider router={router} />)
    expect(await screen.findByText('gate destination')).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/deploy/gate')
    expect(router.state.location.search).toBe('?run_id=abc')
  })
})

describe('route — /research/promote/:id redirects to /deploy/promote/:id (param forwarded)', () => {
  it('forwards the strategyId path param to the deployment path', async () => {
    const router = createMemoryRouter(
      [
        { path: '/research/promote/:strategyId', element: <PromoteRedirect /> },
        { path: '/deploy/promote/:strategyId', element: <div>promote destination</div> },
      ],
      { initialEntries: ['/research/promote/s1'] },
    )
    render(<RouterProvider router={router} />)
    expect(await screen.findByText('promote destination')).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/deploy/promote/s1')
  })
})
