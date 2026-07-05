/*
 * Placeholder：證明路由/殼/token 可跑。後續依
 * dev_docs/product_repositioning/17_frontend_information_architecture.md 逐頁替換。
 */
import { useTranslation } from 'react-i18next'
import { StatusBadge } from './StatusBadge'

export function Placeholder({ title, route, spec }: { title: string; route: string; spec: string }) {
  const { t } = useTranslation('common')
  return (
    <div className="rounded-lg border border-border bg-surface p-6">
      <div className="mb-2 flex items-center gap-3">
        <h1 className="text-[22px] font-semibold">{title}</h1>
        <StatusBadge tone="warning">{t('placeholder.notBuilt')}</StatusBadge>
      </div>
      <p className="font-mono text-sm text-text-secondary tabular">{route}</p>
      <p className="mt-4 text-sm text-text-muted">
        {t('placeholder.ref')}：<span className="font-mono">{spec}</span> ·{' '}
        <span className="font-mono">product_repositioning/17_frontend_information_architecture.md</span>
      </p>
    </div>
  )
}
