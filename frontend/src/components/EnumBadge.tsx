/*
 * EnumBadge — 取代散落各頁的 <StatusBadge tone={gateTone(x)}>{x ?? '—'}</StatusBadge> 慣用法。
 * 單一入口把 raw backend enum 本地化 + 上 tone；StatusBadge 維持純呈現、不碰 i18n。
 */
import { StatusBadge } from './StatusBadge'
import { useEnumLabel } from '@/i18n/useEnumLabel'
import type { EnumFamily } from '@/i18n/displayMap'

export function EnumBadge({ family, value }: { family: EnumFamily; value?: string | null }) {
  const { label, tone } = useEnumLabel(family, value)
  return <StatusBadge tone={tone}>{label}</StatusBadge>
}
