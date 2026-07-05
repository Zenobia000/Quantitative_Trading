import { useTranslation } from 'react-i18next'
import { ApiError } from '@/services/http'

/*
 * 統一錯誤文案：ApiError → errors:code.<CODE>（帶 {{status}} 插值），未映射 code 回退 code.default，
 * 再退回後端 message；非 ApiError 的 Error → message；其餘 → errors:unknown。
 * service 層維持 React-free（只帶 code/status/message），本 hook 在 UI 層本地化。
 */
export function useErrorText(): (err: unknown) => string {
  const { t } = useTranslation('errors')
  return (err: unknown): string => {
    if (err instanceof ApiError) {
      const status = err.status
      return t(`code.${err.code}`, {
        status,
        defaultValue: t('code.default', { status, defaultValue: err.message || t('unknown') }),
      })
    }
    if (err instanceof Error && err.message) return err.message
    return t('unknown')
  }
}
