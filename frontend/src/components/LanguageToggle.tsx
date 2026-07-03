/*
 * LanguageToggle — 中 / EN 兩段切換。切換即持久化；DocumentLang 監聽 languageChanged 更新 <html lang>/title。
 */
import { useTranslation } from 'react-i18next'
import { persistLng, type Lang } from '@/i18n/config'

export function LanguageToggle({ className = '' }: { className?: string }) {
  const { i18n, t } = useTranslation('common')
  const cur: Lang = i18n.language.startsWith('zh') ? 'zh-TW' : 'en'
  const set = (lng: Lang) => {
    void i18n.changeLanguage(lng)
    persistLng(lng)
  }
  return (
    <div
      role="group"
      aria-label={t('lang.switch')}
      className={`inline-flex items-center rounded-pill border border-border p-0.5 text-xs ${className}`}
    >
      {(['zh-TW', 'en'] as Lang[]).map((lng) => {
        const active = cur === lng
        return (
          <button
            key={lng}
            aria-pressed={active}
            onClick={() => set(lng)}
            className={`rounded-full px-2 py-0.5 ${active ? 'bg-input text-text' : 'text-text-muted hover:text-text'}`}
          >
            {lng === 'zh-TW' ? t('lang.zh') : t('lang.en')}
          </button>
        )
      })}
    </div>
  )
}
