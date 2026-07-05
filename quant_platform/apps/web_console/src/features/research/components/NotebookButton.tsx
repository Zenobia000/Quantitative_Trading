/*
 * Open-in-notebook —— 下載預填 .ipynb（GET /runs/{id}/notebook，回 attachment header）。
 * 以 <a href download> 直接指向端點（同源 / dev 走 vite proxy）；採 ops console flat 樣式。
 */
import { useTranslation } from 'react-i18next'
import { notebookHref } from '../api/report'

export function NotebookButton({ runId }: { runId: string }) {
  const { t } = useTranslation('research')
  return (
    <a
      href={notebookHref(runId)}
      download={`run_${runId}.ipynb`}
      className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm text-text-secondary hover:text-text"
    >
      <span aria-hidden>↓</span>
      {t('report.notebook.label')}
      <span className="text-[11px] text-text-muted">{t('report.notebook.hint')}</span>
    </a>
  )
}
