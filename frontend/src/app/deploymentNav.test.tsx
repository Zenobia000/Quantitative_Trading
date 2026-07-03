/*
 * Deployment zone 遷移驗證（rebuild IA §5.1/§5.3/§5.6）：
 * nav 新增 deployment zone（部署嚴格閘），validate 由 research 移出；
 * /research/validate → /deploy/gate（保留 query）、/research/promote/:id → /deploy/promote/:id（轉發參數）client 重導。
 * 純位置搬遷，零 gate 邏輯變更（規格全域驗收 #8：嚴格閘仍可用但不再是第一研究體驗）。
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { NAV } from '@/app/nav'
import { GateRedirect, PromoteRedirect } from '@/app/redirects'

describe('nav — Deployment zone migration', () => {
  const zones = Object.fromEntries(NAV.map((z) => [z.zone, z]))

  it('adds a deployment zone carrying the strict gate item', () => {
    expect(zones.deployment).toBeDefined()
    const tos = zones.deployment.items.map((i) => i.to)
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

  it('orders zones Research → Live OOS → Deployment → Monitor → System', () => {
    expect(NAV.map((z) => z.zone)).toEqual(['research', 'live-oos', 'deployment', 'monitor', 'system'])
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
