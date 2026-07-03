/*
 * DocumentLang — 無渲染；同步 <html lang> 與 document.title 至目前語言。
 * 掛載跑一次 + 監聽 languageChanged（涵蓋切換與初次載入）。
 */
import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { htmlLangFor } from '@/i18n/config'

export function DocumentLang() {
  const { i18n, t } = useTranslation('common')
  useEffect(() => {
    const apply = () => {
      document.documentElement.lang = htmlLangFor(i18n.language)
      document.title = t('app.documentTitle')
    }
    apply()
    i18n.on('languageChanged', apply)
    return () => {
      i18n.off('languageChanged', apply)
    }
  }, [i18n, t])
  return null
}
