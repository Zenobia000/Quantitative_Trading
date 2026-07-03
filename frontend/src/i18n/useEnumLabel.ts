import { useTranslation } from 'react-i18next'
import { enumTone, type EnumFamily, type Tone } from './displayMap'

/** raw backend enum → { 本地化 label, tone }。未知 token 回退 raw / muted。 */
export function useEnumLabel(family: EnumFamily, raw?: string | null): { label: string; tone: Tone } {
  const { t } = useTranslation('status')
  const tone = enumTone(family, raw)
  if (!raw) return { label: '—', tone }
  return { label: t(`${family}.${raw}`, { defaultValue: raw }), tone }
}
