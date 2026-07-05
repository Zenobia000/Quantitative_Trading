/*
 * ThemeProvider — 深/淺/跟隨系統 三模式主題。
 * dark 為預設一等公民（無 JS / 首繪即 dark，靠 tokens.css :root 預設 + index.html inline script）。
 * mode 持久化於 localStorage[THEME_KEY]；resolved 為實際套用的 dark|light（system 由 matchMedia 推導，不持久化）。
 * 套用方式：在 <html> 掛 .dark / .light class + 設 style.colorScheme（native 控件跟隨）。
 */
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

export type ThemeMode = 'dark' | 'light' | 'system'
export type ResolvedTheme = 'dark' | 'light'

/** localStorage key —— index.html 的 inline FOUC script 必須使用相同字面。 */
export const THEME_KEY = 'ui-theme'

const MEDIA = '(prefers-color-scheme: dark)'

function systemResolved(): ResolvedTheme {
  return typeof window !== 'undefined' && window.matchMedia(MEDIA).matches ? 'dark' : 'light'
}

function readStoredMode(): ThemeMode {
  try {
    const v = localStorage.getItem(THEME_KEY)
    if (v === 'dark' || v === 'light' || v === 'system') return v
  } catch {
    /* private mode / no storage → 預設 dark */
  }
  return 'dark'
}

function applyResolved(resolved: ResolvedTheme): void {
  const el = document.documentElement
  el.classList.remove('dark', 'light')
  el.classList.add(resolved)
  el.style.colorScheme = resolved
}

interface ThemeCtx {
  mode: ThemeMode
  resolved: ResolvedTheme
  setMode: (m: ThemeMode) => void
}

const Ctx = createContext<ThemeCtx | null>(null)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<ThemeMode>(readStoredMode)
  const [resolved, setResolved] = useState<ResolvedTheme>(() => {
    const m = readStoredMode()
    return m === 'system' ? systemResolved() : m
  })

  // 解析 + 套用（mode 變即重算；掛載也跑一次，與 inline script 冪等）
  useEffect(() => {
    const next: ResolvedTheme = mode === 'system' ? systemResolved() : mode
    setResolved(next)
    applyResolved(next)
  }, [mode])

  // system 模式即時跟隨 OS 切換（僅 system 時掛監聽，清理冪等 → StrictMode 安全）
  useEffect(() => {
    if (mode !== 'system') return
    const mql = window.matchMedia(MEDIA)
    const onChange = () => {
      const next = systemResolved()
      setResolved(next)
      applyResolved(next)
    }
    mql.addEventListener('change', onChange)
    return () => mql.removeEventListener('change', onChange)
  }, [mode])

  // 持久化 mode（不持久化 resolved）
  useEffect(() => {
    try {
      localStorage.setItem(THEME_KEY, mode)
    } catch {
      /* ignore */
    }
  }, [mode])

  return <Ctx.Provider value={{ mode, resolved, setMode }}>{children}</Ctx.Provider>
}

export function useTheme(): ThemeCtx {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}
