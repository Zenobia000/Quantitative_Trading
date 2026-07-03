/*
 * ThemeSwitch — 三段主題切換（淺 / 系統 / 深）。
 * ARIA radiogroup：roving tabindex + 方向鍵 + Home/End；僅用既有 token 樣式（flat, 1px border）。
 * 文案走 common:theme.*（i18n）。
 */
import { useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useTheme, type ThemeMode } from '@/app/theme'

const ORDER: ThemeMode[] = ['light', 'system', 'dark']

function ThemeIcon({ mode }: { mode: ThemeMode }) {
  const common = { width: 14, height: 14, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const }
  if (mode === 'light')
    return (
      <svg {...common} aria-hidden>
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
      </svg>
    )
  if (mode === 'dark')
    return (
      <svg {...common} aria-hidden>
        <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
      </svg>
    )
  return (
    <svg {...common} aria-hidden>
      <rect x="2" y="4" width="20" height="14" rx="2" />
      <path d="M8 21h8M12 18v3" />
    </svg>
  )
}

export function ThemeSwitch({ className = '' }: { className?: string }) {
  const { t } = useTranslation('common')
  const { mode, setMode } = useTheme()
  const refs = useRef<(HTMLButtonElement | null)[]>([])

  const onKeyDown = (e: React.KeyboardEvent, i: number) => {
    let ni = i
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') ni = (i + 1) % ORDER.length
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') ni = (i - 1 + ORDER.length) % ORDER.length
    else if (e.key === 'Home') ni = 0
    else if (e.key === 'End') ni = ORDER.length - 1
    else return
    e.preventDefault()
    setMode(ORDER[ni])
    refs.current[ni]?.focus()
  }

  return (
    <div
      role="radiogroup"
      aria-label={t('theme.label')}
      className={`inline-flex items-center gap-0.5 rounded-pill border border-border p-0.5 ${className}`}
    >
      {ORDER.map((m, i) => {
        const active = mode === m
        return (
          <button
            key={m}
            ref={(el) => {
              refs.current[i] = el
            }}
            role="radio"
            aria-checked={active}
            aria-label={t(`theme.${m}`)}
            title={t(`theme.${m}`)}
            tabIndex={active ? 0 : -1}
            onClick={() => setMode(m)}
            onKeyDown={(e) => onKeyDown(e, i)}
            className={`flex h-6 w-6 items-center justify-center rounded-full ${
              active ? 'bg-input text-text' : 'text-text-muted hover:text-text'
            }`}
          >
            <ThemeIcon mode={m} />
          </button>
        )
      })}
    </div>
  )
}
