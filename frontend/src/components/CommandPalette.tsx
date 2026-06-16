/*
 * Cmd-K 命令面板（8.G.6）。⌘K / Ctrl+K 開啟，輸入過濾，↑↓ 選擇，Enter 跳轉，Esc 關閉。
 * 命令源 = nav.ts（HOME + 三區 NAV items），單一真相源，新增頁自動出現。
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { HOME, NAV } from '@/app/nav'

interface Command {
  label: string
  to: string
  zone: string
}

const COMMANDS: Command[] = [
  { label: HOME.label, to: HOME.to, zone: '首頁' },
  ...NAV.flatMap((z) => z.items.map((it) => ({ label: it.label, to: it.to, zone: z.label }))),
]

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  const results = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return COMMANDS
    return COMMANDS.filter((c) => c.label.toLowerCase().includes(q) || c.to.toLowerCase().includes(q) || c.zone.toLowerCase().includes(q))
  }, [query])

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
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]" role="dialog" aria-label="命令面板">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative w-full max-w-lg rounded-lg border border-border bg-surface shadow-xl" onKeyDown={onKeyDown}>
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="搜尋頁面 / 跳轉…"
          className="w-full rounded-t-lg border-b border-border bg-transparent px-4 py-3 text-sm text-text outline-none placeholder:text-text-muted"
        />
        <ul className="max-h-80 overflow-auto py-1">
          {results.length === 0 ? (
            <li className="px-4 py-3 text-sm text-text-muted">無相符項目</li>
          ) : (
            results.map((c, i) => (
              <li key={c.to}>
                <button
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
