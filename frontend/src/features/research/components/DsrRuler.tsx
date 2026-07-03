/*
 * DSR 標尺（真偽閘）—— 本平台差異化。一條 0.85–1.00 水平尺，0.90 / 0.95 兩刻度線切三帶：
 * REJECTED(0.85–0.90) / PAPER_WATCH(0.90–0.95) / REAL(0.95–1.00)，PAPER_WATCH 帶著色。
 * truth_gate.verdict_dsr 有值 → 畫指針 + band badge；為 null → 空態（不畫假指針，GOAL #8）。
 * 帶色與定位純函式在 lib/reportViz（可測）；本元件只管呈現。
 */
import { useTranslation } from 'react-i18next'
import { StatusBadge } from '@/components/StatusBadge'
import type { TruthGateBerth } from '../api/report'
import {
  DSR_SCALE_MAX,
  DSR_SCALE_MIN,
  DSR_TICK_PAPER,
  DSR_TICK_REAL,
  bandTone,
  dsrToPercent,
} from '../lib/reportViz'

const TICKS = [DSR_SCALE_MIN, DSR_TICK_PAPER, DSR_TICK_REAL, DSR_SCALE_MAX]

export function DsrRuler({ truthGate }: { truthGate: TruthGateBerth | null | undefined }) {
  const { t } = useTranslation('research')
  const dsr = truthGate?.verdict_dsr ?? null
  const band = truthGate?.band ?? null
  const hasNeedle = dsr != null && Number.isFinite(dsr)

  return (
    <div>
      <div className="mb-2 flex items-center gap-2">
        <span className="text-xs text-text-muted">{t('report.dsr.title')}</span>
        {hasNeedle ? (
          <>
            <StatusBadge tone={bandTone(band)}>
              {band ? t(`report.dsr.band.${band}`, { defaultValue: band }) : '—'}
            </StatusBadge>
            <span className="ml-auto font-mono text-xs text-text-secondary tabular">
              DSR {(dsr as number).toFixed(4)}
            </span>
          </>
        ) : null}
      </div>

      {hasNeedle ? (
        <div
          className="relative"
          role="img"
          aria-label={t('report.dsr.needleAria', { dsr: (dsr as number).toFixed(4) })}
        >
          {/* 三帶軌道：REJECTED 紅 / PAPER_WATCH 琥珀 / REAL 綠（低濃度，讀作刻度非警報）。 */}
          <div className="flex h-2.5 overflow-hidden rounded-full border border-border">
            <span className="h-full flex-1" style={{ backgroundColor: 'color-mix(in srgb, var(--loss) 22%, transparent)' }} />
            <span className="h-full flex-1" style={{ backgroundColor: 'color-mix(in srgb, var(--warning) 30%, transparent)' }} />
            <span className="h-full flex-1" style={{ backgroundColor: 'color-mix(in srgb, var(--gain) 22%, transparent)' }} />
          </div>
          {/* 刻度線 0.90 / 0.95（三分位）。 */}
          {[DSR_TICK_PAPER, DSR_TICK_REAL].map((tk) => (
            <span
              key={tk}
              className="absolute top-0 h-2.5 w-px bg-border"
              style={{ left: `${dsrToPercent(tk)}%` }}
            />
          ))}
          {/* 指針：▼ + 直線，落在 verdict_dsr（夾邊，永不溢出）。 */}
          <span
            data-testid="dsr-needle"
            className="absolute -top-1.5 -translate-x-1/2 text-[10px] leading-none text-text"
            style={{ left: `${dsrToPercent(dsr as number)}%` }}
            aria-hidden
          >
            ▼
          </span>
          {/* 刻度標籤。 */}
          <div className="mt-1 flex justify-between font-mono text-[10px] text-text-muted tabular">
            {TICKS.map((tk) => (
              <span key={tk}>{tk.toFixed(2)}</span>
            ))}
          </div>
        </div>
      ) : (
        <p className="rounded-md border border-dashed border-border/70 bg-base px-3 py-2 text-xs text-text-muted">
          {t('report.dsr.empty')}
        </p>
      )}
    </div>
  )
}
