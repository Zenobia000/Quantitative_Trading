/*
 * 404 頁 —— router 為 module-level 無法用 hook，故以此小元件承載 i18n 標題。
 */
import { useTranslation } from 'react-i18next'
import { Placeholder } from './Placeholder'

export function NotFoundPage() {
  const { t } = useTranslation('common')
  return <Placeholder title={t('placeholder.notFound')} route="404" spec="—" />
}
