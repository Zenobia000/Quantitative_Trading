/*
 * AppShell — 三區 sidebar（Research/Monitor/System + 首頁）+ Cmd-K 佔位 + Outlet。
 * RWD：sidebar 兩態（展開 ↔ drawer @<1024，lg 斷點）。GOAL.md 硬約束 #7。
 */
import { useEffect, useRef, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { HOME, NAV } from '@/app/nav'
import { CommandPalette } from '@/components/CommandPalette'
import { ThemeSwitch } from '@/components/ThemeSwitch'
import { LanguageToggle } from '@/components/LanguageToggle'

function navLinkClass({ isActive }: { isActive: boolean }): string {
  return [
    'block rounded-md px-3 py-1.5 text-sm',
    isActive ? 'bg-input text-text' : 'text-text-secondary hover:text-text hover:bg-surface',
  ].join(' ')
}

function SidebarContent() {
  const { t } = useTranslation('nav')
  return (
    <nav className="flex flex-col gap-4 p-3">
      <NavLink to={HOME.to} className={navLinkClass} end>
        {t(HOME.key)}
      </NavLink>
      {NAV.map((z) => (
        <div key={z.zone}>
          <div className="px-3 pb-1 text-[11px] font-medium tracking-wider text-text-muted">
            {t(`zone.${z.zone}`)}
          </div>
          <div className="flex flex-col gap-0.5">
            {z.items.map((it, i) => (
              <NavLink key={it.to} to={it.to} className={navLinkClass} end>
                {/* RESEARCH 為有序研究迴圈 → 標序號；Monitor/System 為平行子視圖，不標號 */}
                {z.zone === 'research' ? (
                  <span className="flex items-center gap-2">
                    <span className="w-3 shrink-0 font-mono text-[10px] tabular text-text-muted">{i + 1}</span>
                    <span>{t(it.key)}</span>
                  </span>
                ) : (
                  t(it.key)
                )}
              </NavLink>
            ))}
          </div>
        </div>
      ))}
    </nav>
  )
}

export function AppShell() {
  const { t } = useTranslation('common')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [cmdkOpen, setCmdkOpen] = useState(false)
  const drawerRef = useRef<HTMLElement>(null)
  const openerRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setCmdkOpen((o) => !o)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  // Drawer a11y：Escape 關閉 + Tab 焦點鎖在抽屜內 + 開啟時把焦點移入。
  useEffect(() => {
    if (!drawerOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setDrawerOpen(false)
        return
      }
      if (e.key !== 'Tab') return
      const nodes = drawerRef.current?.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
      )
      if (!nodes || nodes.length === 0) return
      const first = nodes[0]
      const last = nodes[nodes.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', onKey)
    const t = window.setTimeout(() => {
      drawerRef.current?.querySelector<HTMLElement>('button, a[href]')?.focus()
    }, 0)
    return () => {
      document.removeEventListener('keydown', onKey)
      window.clearTimeout(t)
      // 關閉時把焦點還給開啟鈕（漢堡），避免焦點掉到 body。
      openerRef.current?.focus()
    }
  }, [drawerOpen])

  return (
    <div className="flex h-full">
      {/* Sidebar — 展開（lg+）；<lg 收起，由 topbar 漢堡開 drawer */}
      <aside className="hidden w-60 shrink-0 border-r border-border bg-base lg:block">
        <div className="flex h-12 items-center border-b border-border px-4 text-sm font-semibold">
          {t('app.wordmark')}
        </div>
        <SidebarContent />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Topbar：漢堡（<lg）+ Cmd-K 佔位 */}
        <header className="flex h-12 items-center gap-3 border-b border-border bg-base px-4">
          <button
            ref={openerRef}
            className="rounded-md border border-border px-2 py-1 text-xs text-text-secondary lg:hidden"
            onClick={() => setDrawerOpen(true)}
            aria-label={t('chrome.navOpen')}
          >
            ☰
          </button>
          <button
            onClick={() => setCmdkOpen(true)}
            className="rounded-pill border border-border px-3 py-1 text-xs text-text-muted hover:text-text"
          >
            {t('cmdk.trigger')}
          </button>
          {/* 右側控制群：語言 + 主題切換 */}
          <div className="ml-auto flex items-center gap-2">
            <LanguageToggle />
            <ThemeSwitch />
          </div>
        </header>

        <main className="min-w-0 flex-1 overflow-auto p-4">
          <Outlet />
        </main>
      </div>

      {/* Drawer（<lg） */}
      {drawerOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-scrim" onClick={() => setDrawerOpen(false)} />
          <aside
            ref={drawerRef}
            role="dialog"
            aria-modal="true"
            aria-label={t('chrome.navLabel')}
            className="absolute left-0 top-0 h-full w-64 border-r border-border bg-base"
          >
            <div className="flex h-12 items-center justify-between border-b border-border px-4 text-sm font-semibold">
              {t('app.wordmark')}
              <button onClick={() => setDrawerOpen(false)} aria-label={t('chrome.navClose')}>
                ✕
              </button>
            </div>
            <div onClick={() => setDrawerOpen(false)}>
              <SidebarContent />
            </div>
          </aside>
        </div>
      )}

      <CommandPalette open={cmdkOpen} onClose={() => setCmdkOpen(false)} />
    </div>
  )
}
