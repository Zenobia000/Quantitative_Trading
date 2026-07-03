/*
 * Live OOS zone 遷移驗證（rebuild IA §5.2/§5.4/§5.6）：
 * nav 新增 live-oos zone（佇列 + 觀察艙），watch 由 monitor 移入；/monitor/watch → /live-oos/watch client 重導。
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { createMemoryRouter, Navigate, RouterProvider } from 'react-router-dom'
import { NAV } from '@/app/nav'

describe('nav — Live OOS zone migration', () => {
  const zones = Object.fromEntries(NAV.map((z) => [z.zone, z]))

  it('adds a live-oos zone carrying the queue + watch items', () => {
    expect(zones['live-oos']).toBeDefined()
    const tos = zones['live-oos'].items.map((i) => i.to)
    expect(tos).toContain('/live-oos/queue')
    expect(tos).toContain('/live-oos/watch')
  })

  it('removes watch from the monitor zone (it moved to Live OOS)', () => {
    const monitorTos = zones.monitor.items.map((i) => i.to)
    expect(monitorTos).not.toContain('/monitor/watch')
  })

  it('orders zones Research → Live OOS → Deployment → Monitor → System', () => {
    expect(NAV.map((z) => z.zone)).toEqual(['research', 'live-oos', 'deployment', 'monitor', 'system'])
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
