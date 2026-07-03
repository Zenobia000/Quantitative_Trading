/*
 * Cmd-K 命令面板（8.G.6）。⌘K / Ctrl+K 開啟，輸入過濾，↑↓ 選擇，Enter 跳轉，Esc 關閉。
 * 命令源 = nav.ts（HOME + 三區 NAV items），單一真相源，新增頁自動出現。
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { HOME, NAV } from '@/app/nav'

interface Command {
  label: string
  to: string
  zone: string
}

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate()
  const { t, i18n } = useTranslation(['common', 'nav'])
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  // 命令源 = nav.ts；label/zone 依目前語言即時翻譯（語言切換時重算 + 搜尋比對翻譯後文字）。
  const commands = useMemo<Command[]>(
    () => [
      { label: t(`nav:${HOME.key}`), to: HOME.to, zone: t('nav:home') },
      ...NAV.flatMap((z) =>
        z.items.map((it) => ({ label: t(`nav:${it.key}`), to: it.to, zone: t(`nav:zone.${z.zone}`) })),
      ),
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [t, i18n.language],
  )

  const results = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return commands
    return commands.filter(
      (c) => c.label.toLowerCase().includes(q) || c.to.toLowerCase().includes(q) || c.zone.toLowerCase().includes(q),
    )
  }, [query, commands])

  useEffect(() => {
    if (open) {
      setQuery('')
      setActive(0)
      inputRef.current?.focus()
    }
  }, [open])

  useEffect(() => {
    setActive((a) => Math.min(a, Math.max(0, results.length - 1)))
  }, [results.length])

  if (!open) return null

  const go = (to: string) => {
    navigate(to)
    onClose()
  }

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') return onClose()
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActive((a) => (a + 1) % Math.max(1, results.length))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((a) => (a - 1 + results.length) % Math.max(1, results.length))
    } else if (e.key === 'Enter' && results[active]) {
      e.preventDefault()
      go(results[active].to)
    }
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]" role="dialog" aria-label={t('common:cmdk.dialog')}>
      <div className="absolute inset-0 bg-scrim" onClick={onClose} />
      {/* flat：1px border 分層取代陰影（無 shadow-xl，遵 Grok 單色 flat 規則） */}
      <div className="relative w-full max-w-lg rounded-lg border border-border bg-surface" onKeyDown={onKeyDown}>
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t('common:cmdk.placeholder')}
          role="combobox"
          aria-expanded
          aria-controls="cmdk-listbox"
          aria-activedescendant={results[active] ? `cmdk-opt-${active}` : undefined}
          aria-autocomplete="list"
          className="w-full rounded-t-lg border-b border-border bg-transparent px-4 py-3 text-sm text-text outline-none placeholder:text-text-muted"
        />
        <ul id="cmdk-listbox" role="listbox" aria-label={t('common:cmdk.results')} className="max-h-80 overflow-auto py-1">
          {results.length === 0 ? (
            <li className="px-4 py-3 text-sm text-text-muted">{t('common:cmdk.empty')}</li>
          ) : (
            results.map((c, i) => (
              <li key={c.to}>
                <button
                  id={`cmdk-opt-${i}`}
                  role="option"
                  aria-selected={i === active}
                  tabIndex={-1}
                  onMouseEnter={() => setActive(i)}
                  onClick={() => go(c.to)}
                  className={`flex w-full items-center justify-between px-4 py-2 text-left text-sm ${
                    i === active ? 'bg-input text-text' : 'text-text-secondary hover:text-text'
                  }`}
                >
                  <span>{c.label}</span>
                  <span className="font-mono text-[11px] text-text-muted">{c.zone} · {c.to}</span>
                </button>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  )
}
