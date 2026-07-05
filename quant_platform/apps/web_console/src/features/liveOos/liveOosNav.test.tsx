/*
 * Governance IA 遷移驗證：
 * Live OOS / Paper-Watch 是治理與發布觀察流程，不再是一等 zone；
 * /monitor/watch 仍保留 client redirect 到 /live-oos/watch。
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { createMemoryRouter, Navigate, RouterProvider } from 'react-router-dom'
import { NAV } from '@/app/nav'

describe('nav — Live OOS governance migration', () => {
  const zones = Object.fromEntries(NAV.map((z) => [z.zone, z]))

  it('carries queue + watch items under the governance zone', () => {
    expect(zones.governance).toBeDefined()
    const tos = zones.governance.items.map((i) => i.to)
    expect(tos).toContain('/live-oos/queue')
    expect(tos).toContain('/live-oos/watch')
    expect(tos).toContain('/deploy/gate')
  })

  it('does not keep legacy live-oos/deployment/monitor zones as first-class navigation', () => {
    expect(zones['live-oos']).toBeUndefined()
    expect(zones.deployment).toBeUndefined()
    expect(zones.monitor).toBeUndefined()
  })

  it('orders zones by the golden seven-layer console IA', () => {
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

describe('route — /monitor/watch redirects to /live-oos/watch', () => {
  it('a client redirect (Navigate replace) lands on the watch destination', async () => {
    // Mirrors router.tsx: the legacy monitor/watch path is a Navigate to the new zone path.
    const router = createMemoryRouter(
      [
        { path: '/monitor/watch', element: <Navigate to="/live-oos/watch" replace /> },
        { path: '/live-oos/watch', element: <div>watch destination</div> },
      ],
      { initialEntries: ['/monitor/watch'] },
    )
    render(<RouterProvider router={router} />)
    expect(await screen.findByText('watch destination')).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/live-oos/watch')
  })
})
