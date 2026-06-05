/* 頁首：標題 + route + 副說明（對齊 design.pen Section · header）。 */
export function PageHeader({
  title,
  route,
  subtitle,
}: {
  title: string
  route: string
  subtitle?: string
}) {
  return (
    <header className="mb-4">
      <div className="flex items-baseline gap-3">
        <h1 className="text-[22px] font-semibold">{title}</h1>
        <span className="font-mono text-xs text-text-muted tabular">{route}</span>
      </div>
      {subtitle && <p className="mt-0.5 text-sm text-text-secondary">{subtitle}</p>}
    </header>
  )
}
