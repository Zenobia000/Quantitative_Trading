/*
 * 候選狀態 badge —— 本頁自有 tone/label（不碰 status.json / displayMap.ts）。
 * 沿用共用 StatusBadge 的純呈現殼；label 走 research namespace `candidates.state.*`。
 */
import { useTranslation } from 'react-i18next'
import { StatusBadge } from '@/components/StatusBadge'
import { candidateStateTone } from './candidateDisplay'
import type { CandidateState } from '../../api/candidates'

export function CandidateStateBadge({ state }: { state: CandidateState }) {
  const { t } = useTranslation('research')
  return (
    <StatusBadge tone={candidateStateTone(state)}>
      {t(`candidates.state.${state}`, { defaultValue: state })}
    </StatusBadge>
  )
}
