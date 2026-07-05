/*
 * 受控資料視覺化色盤（8.G.6）— 圖表/多序列消費 API，對齊 tokens.css 的 CSS vars。
 * 品牌為單色 dark；此處是「圖表需可區辨」的受控例外，回傳 var() 供 SVG fill/stroke。
 */
export const CATEGORICAL = [
  'var(--cat-1)',
  'var(--cat-2)',
  'var(--cat-3)',
  'var(--cat-4)',
  'var(--cat-5)',
  'var(--cat-6)',
] as const

export const DIVERGING = { neg: 'var(--div-neg)', mid: 'var(--div-mid)', pos: 'var(--div-pos)' } as const

export const SEQUENTIAL = [
  'var(--seq-1)',
  'var(--seq-2)',
  'var(--seq-3)',
  'var(--seq-4)',
  'var(--seq-5)',
] as const

/** 多序列第 ``i`` 條的 categorical 色（循環、支援負 index）。 */
export function categorical(i: number): string {
  const n = CATEGORICAL.length
  return CATEGORICAL[((i % n) + n) % n]
}

/** signed 值的 diverging 端點（neg/0/pos）— 相關性 / 月報酬熱圖格用色。 */
export function divergingColor(value: number): string {
  if (value > 0) return DIVERGING.pos
  if (value < 0) return DIVERGING.neg
  return DIVERGING.mid
}

/** 正規化強度 ``t ∈ [0,1]`` 的 sequential 桶色（熱度）。 */
export function sequentialColor(t: number): string {
  const clamped = Math.max(0, Math.min(1, t))
  const idx = Math.min(SEQUENTIAL.length - 1, Math.floor(clamped * SEQUENTIAL.length))
  return SEQUENTIAL[idx]
}
