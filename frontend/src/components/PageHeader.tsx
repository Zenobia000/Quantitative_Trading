/* 頁首：可選 back（深頁 wayfinding）+ 標題 + route（弱化 dev chrome）+ 副說明。 */
import { useNavigate } from 'react-router-dom'

export function PageHeader({
  title,
  route,
  subtitle,
  back,
}: {
  title: string
  route: string
  subtitle?: string
  /** 深層頁回上一層的路徑（← 標籤）；不給則不顯示 */
  back?: { label: string; to: string }
}) {
  const navigate = useNavigate()
  return (
    <header className="mb-4">
      {back && (
        <button
          onClick={() => navigate(back.to)}
          className="mb-1 inline-flex items-center gap-1 text-xs text-text-muted hover:text-text"
        >
          <span aria-hidden>←</span> {back.label}
        </button>
      )}
      <div className="flex items-baseline gap-3">
        <h1 className="text-[22px] font-semibold">{title}</h1>
        <span className="hidden font-mono text-xs text-text-muted tabular sm:inline">{route}</span>
      </div>
      {subtitle && <p className="mt-0.5 text-sm text-text-secondary">{subtitle}</p>}
    </header>
  )
}
