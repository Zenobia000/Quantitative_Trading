/*
 * 資料來源 badge —— 誠實揭露此頁讀的是真 API 還是 bundled fixture（後端 Goal 3/4 未落地時）。
 * fixture 模式用琥珀 warning tone 顯眼提示「尚未接後端」；真 API 用中性 muted。
 */
import { useTranslation } from 'react-i18next'
import { StatusBadge } from '@/components/StatusBadge'
import type { DataSource } from '../../api/reportViewer'

export function DataSourceBadge({ source }: { source: DataSource }) {
  const { t } = useTranslation('research')
  const isFixture = source === 'fixture'
  return (
    <StatusBadge tone={isFixture ? 'warning' : 'muted'}>
      <span aria-hidden>{isFixture ? '◆' : '●'}</span>
      <span>{isFixture ? t('reportViewer.dataSource.fixture') : t('reportViewer.dataSource.api')}</span>
    </StatusBadge>
  )
}
