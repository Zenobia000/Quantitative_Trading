import { useEffect, useMemo, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { HOME, NAV, type NavZone } from '@/app/nav'
import { CommandPalette } from '@/components/CommandPalette'
import { ThemeSwitch } from '@/components/ThemeSwitch'
import { LanguageToggle } from '@/components/LanguageToggle'

const ZONE_MARK: Record<NavZone['zone'], string> = {
  data: 'D',
  research: 'R',
  governance: 'G',
  trading: 'T',
  risk: 'K',
  operations: 'O',
  system: 'S',
}

function navLinkClass({ isActive }: { isActive: boolean }): string {
  return [
    'group flex items-center justify-between border-l-2 px-3 py-1.5 text-[12px] transition-colors',
    isActive
      ? 'border-info bg-input text-text'
      : 'border-transparent text-text-secondary hover:border-border-strong hover:bg-row hover:text-text',
  ].join(' ')
}

function StatusCell({
  label,
  value,
  tone = 'muted',
}: {
  label: string
  value: string
  tone?: 'gain' | 'warning' | 'error' | 'info' | 'halt' | 'muted'
}) {
  const toneClass: Record<typeof tone, string> = {
    gain: 'text-gain',
    warning: 'text-warning',
    error: 'text-error',
    info: 'text-info',
    halt: 'text-halt',
    muted: 'text-text-secondary',
  }
  return (
    <div className="flex items-center gap-2 border-r border-border px-3 py-1.5">
      <span className="text-[10px] uppercase tracking-[0.16em] text-text-muted">{label}</span>
      <span className={`font-mono text-[11px] font-semibold tabular ${toneClass[tone]}`}>{value}</span>
    </div>
  )
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { t } = useTranslation('nav')
  return (
    <nav className="flex flex-col">
      <NavLink
        to={HOME.to}
        className={({ isActive }) =>
          [
            'flex items-center gap-2 border-b border-border px-4 py-3 text-[12px] font-semibold uppercase tracking-[0.12em]',
            isActive ? 'bg-input text-text' : 'text-text-secondary hover:bg-row hover:text-text',
          ].join(' ')
        }
        end
        onClick={onNavigate}
      >
        <span className="h-2 w-2 rounded-full bg-info" />
        {t(HOME.key)}
      </NavLink>

      {NAV.map((z) => (
        <section key={z.zone} className="border-b border-border/70 py-2">
          <div className="flex items-center gap-2 px-3 pb-1.5">
            <span className="flex h-5 w-5 items-center justify-center border border-border-strong bg-panel font-mono text-[10px] text-info">
              {ZONE_MARK[z.zone]}
            </span>
            <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-text-muted">
              {t(`zone.${z.zone}`)}
            </span>
          </div>
          <div className="flex flex-col">
            {z.items.map((it) => (
              <NavLink key={it.to} to={it.to} className={navLinkClass} end onClick={onNavigate}>
                <span>{t(it.key)}</span>
                <span className="font-mono text-[10px] text-text-muted">›</span>
              </NavLink>
            ))}
          </div>
        </section>
      ))}
    </nav>
  )
}

function useWorkspaceTitle(): string {
  const location = useLocation()
  const { t } = useTranslation('nav')
  return useMemo(() => {
    if (location.pathname === '/') return t(HOME.key)
    const item = NAV.flatMap((z) => z.items).find((it) => location.pathname === it.to)
    if (item) return t(item.key)
    const zone = NAV.find((z) => z.items.some((it) => location.pathname.startsWith(it.to)))
    return zone ? t(`zone.${zone.zone}`) : 'Workspace'
  }, [location.pathname, t])
}

export function AppShell() {
  const { t } = useTranslation('common')
  const workspaceTitle = useWorkspaceTitle()
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
    const timer = window.setTimeout(() => {
      drawerRef.current?.querySelector<HTMLElement>('button, a[href]')?.focus()
    }, 0)
    return () => {
      document.removeEventListener('keydown', onKey)
      window.clearTimeout(timer)
      openerRef.current?.focus()
    }
  }, [drawerOpen])

  return (
    <div className="flex h-full bg-base text-text">
      <aside className="hidden w-[252px] shrink-0 border-r border-border bg-panel lg:flex lg:flex-col">
        <div className="border-b border-border px-4 py-3">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-semibold tracking-[0.18em]">{t('app.wordmark')}</div>
              <div className="mt-0.5 text-[10px] uppercase tracking-[0.16em] text-text-muted">
                Personal EOD Ops
              </div>
            </div>
            <div className="h-2.5 w-2.5 rounded-full bg-gain" title="system clear" />
          </div>
        </div>
        <div className="min-h-0 flex-1 overflow-auto">
          <SidebarContent />
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-b border-border bg-panel">
          <div className="flex h-9 items-center overflow-x-auto border-b border-border">
            <StatusCell label={t('chrome.tradeDate')} value="EOD" tone="info" />
            <StatusCell label={t('chrome.risk')} value={t('chrome.haltClear')} tone="gain" />
            <StatusCell label={t('chrome.data')} value={t('chrome.dataPending')} tone="warning" />
            <StatusCell label={t('chrome.mode')} value={t('chrome.paperMode')} tone="info" />
            <div className="ml-auto flex items-center gap-2 px-3">
              <button
                onClick={() => setCmdkOpen(true)}
                className="border border-border-strong bg-input px-2.5 py-1 font-mono text-[11px] text-text-secondary hover:text-text"
              >
                {t('cmdk.trigger')}
              </button>
              <LanguageToggle />
              <ThemeSwitch />
            </div>
          </div>

          <div className="flex h-11 items-center gap-3 px-3">
            <button
              ref={openerRef}
              className="border border-border-strong bg-input px-2 py-1 text-xs text-text-secondary lg:hidden"
              onClick={() => setDrawerOpen(true)}
              aria-label={t('chrome.navOpen')}
            >
              MENU
            </button>
            <div className="min-w-0">
              <div className="truncate text-[13px] font-semibold uppercase tracking-[0.14em]">{workspaceTitle}</div>
              <div className="text-[10px] uppercase tracking-[0.16em] text-text-muted">
                source: golden seven-layer console
              </div>
            </div>
          </div>
        </header>

        <main className="min-w-0 flex-1 overflow-auto bg-base p-3">
          <Outlet />
        </main>
      </div>

      {drawerOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-scrim" onClick={() => setDrawerOpen(false)} />
          <aside
            ref={drawerRef}
            role="dialog"
            aria-modal="true"
            aria-label={t('chrome.navLabel')}
            className="absolute left-0 top-0 h-full w-72 border-r border-border bg-panel"
          >
            <div className="flex h-12 items-center justify-between border-b border-border px-4 text-sm font-semibold">
              {t('app.wordmark')}
              <button onClick={() => setDrawerOpen(false)} aria-label={t('chrome.navClose')}>
                CLOSE
              </button>
            </div>
            <SidebarContent onNavigate={() => setDrawerOpen(false)} />
          </aside>
        </div>
      )}

      <CommandPalette open={cmdkOpen} onClose={() => setCmdkOpen(false)} />
    </div>
  )
}
