/*
 * i18n 常數與 localStorage 存取。預設 zh-TW，可切 en，記住選擇。
 * 不使用 language detector：預設鎖 zh-TW，行為可預期、測試同步。
 */
export const SUPPORTED = ['zh-TW', 'en'] as const
export type Lang = (typeof SUPPORTED)[number]

export const DEFAULT_LNG: Lang = 'zh-TW'
export const STORAGE_KEY = 'bt.lang'

export const NAMESPACES = ['common', 'nav', 'home', 'research', 'liveOos', 'monitor', 'system', 'status', 'errors', 'sections'] as const
export const DEFAULT_NS = 'common'

/** i18n 語碼 → <html lang> 屬性值。 */
export function htmlLangFor(lng: string): string {
  return lng.startsWith('zh') ? 'zh-Hant' : 'en'
}

export function readStoredLng(): Lang | null {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    if (v === 'zh-TW' || v === 'en') return v
  } catch {
    /* private mode → null */
  }
  return null
}

export function persistLng(lng: Lang): void {
  try {
    localStorage.setItem(STORAGE_KEY, lng)
  } catch {
    /* ignore */
  }
}
