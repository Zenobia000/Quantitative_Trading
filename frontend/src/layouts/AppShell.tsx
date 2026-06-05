/*
 * AppShell — 三區 sidebar（Research/Monitor/System + 首頁）+ Cmd-K 佔位 + Outlet。
 * RWD：sidebar 兩態（展開 ↔ drawer @<1024，lg 斷點）。GOAL.md 硬約束 #7。
 */
import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { HOME, NAV } from '@/app/nav'

function navLinkClass({ isActive }: { isActive: boolean }): string {
  return [
    'block rounded-md px-3 py-1.5 text-sm',
    isActive ? 'bg-input text-text' : 'text-text-secondary hover:text-text hover:bg-surface',
  ].join(' ')
}

function SidebarContent() {
  return (
    <nav className="flex flex-col gap-4 p-3">
      <NavLink to={HOME.to} className={navLinkClass} end>
        {HOME.label}
      </NavLink>
      {NAV.map((z) => (
        <div key={z.zone}>
          <div className="px-3 pb-1 text-[11px] font-medium tracking-wider text-text-muted">
            {z.label}
          </div>
          <div className="flex flex-col gap-0.5">
            {z.items.map((it) => (
              <NavLink key={it.to} to={it.to} className={navLinkClass} end>
                {it.label}
              </NavLink>
            ))}
          </div>
        </div>
      ))}
    </nav>
  )
}

export function AppShell() {
  const [drawerOpen, setDrawerOpen] = useState(false)

  return (
    <div className="flex h-full">
      {/* Sidebar — 展開（lg+）；<lg 收起，由 topbar 漢堡開 drawer */}
      <aside className="hidden w-60 shrink-0 border-r border-border bg-base lg:block">
        <div className="flex h-12 items-center border-b border-border px-4 text-sm font-semibold">
          backtest_platform
        </div>
        <SidebarContent />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Topbar：漢堡（<lg）+ Cmd-K 佔位 */}
        <header className="flex h-12 items-center gap-3 border-b border-border bg-base px-4">
          <button
            className="rounded-md border border-border px-2 py-1 text-xs text-text-secondary lg:hidden"
            onClick={() => setDrawerOpen(true)}
            aria-label="開啟導覽"
          >
            ☰
          </button>
          <button className="rounded-pill border border-border px-3 py-1 text-xs text-text-muted">
            ⌘K 搜尋 / 跳轉
          </button>
        </header>

        <main className="min-w-0 flex-1 overflow-auto p-4">
          <Outlet />
        </main>
      </div>

      {/* Drawer（<lg） */}
      {drawerOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setDrawerOpen(false)} />
          <aside className="absolute left-0 top-0 h-full w-64 border-r border-border bg-base">
            <div className="flex h-12 items-center justify-between border-b border-border px-4 text-sm font-semibold">
              backtest_platform
              <button onClick={() => setDrawerOpen(false)} aria-label="關閉導覽">
                ✕
              </button>
            </div>
            <div onClick={() => setDrawerOpen(false)}>
              <SidebarContent />
            </div>
          </aside>
        </div>
      )}
    </div>
  )
}
