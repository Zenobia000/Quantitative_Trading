/*
 * 五維 scorecard 摘要燈：一列 5 顆迷你燈（獲利 / 風險 / 風報 / 勝率 / 流動）。
 * 雙編碼 = 形狀字符（●◐✕–）+ tone 色 + 維度短標 + 完整 aria-label/title，不只靠顏色。
 */
import { useTranslation } from 'react-i18next'
import { SCORECARD_KEYS, type ScorecardSummary } from '../../api/candidates'
import { scorecardGlyph, scorecardTone, type Tone } from './candidateDisplay'

const TONE_TEXT: Record<Tone, string> = {
  gain: 'text-gain border-gain/40',
  loss: 'text-loss border-loss/40',
  warning: 'text-warning border-warning/40',
  error: 'text-error border-error/40',
  muted: 'text-text-muted border-border',
}

export function ScorecardLights({ summary }: { summary: ScorecardSummary }) {
  const { t } = useTranslation('research')
  return (
    <div className="flex flex-wrap gap-1.5" role="list" aria-label={t('candidates.scorecard.legend')}>
      {SCORECARD_KEYS.map((key) => {
        const status = summary[key]
        const full = t(`candidates.scorecard.full.${key}`)
        const statusLabel = t(`candidates.scorecard.status.${status}`, { defaultValue: status })
        return (
          <span
            key={key}
            role="listitem"
            title={`${full}: ${statusLabel}`}
            aria-label={`${full}: ${statusLabel}`}
            className={`inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[11px] ${TONE_TEXT[scorecardTone(status)]}`}
          >
            <span aria-hidden>{t(`candidates.scorecard.short.${key}`)}</span>
            <span aria-hidden className="font-mono leading-none">
              {scorecardGlyph(status)}
            </span>
          </span>
        )
      })}
    </div>
  )
}
