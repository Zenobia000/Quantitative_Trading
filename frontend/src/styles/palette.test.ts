import { describe, expect, it } from 'vitest'
import { CATEGORICAL, SEQUENTIAL, categorical, divergingColor, sequentialColor } from './palette'

describe('palette (8.G.6 controlled data-viz)', () => {
  it('categorical cycles and handles negative index', () => {
    expect(categorical(0)).toBe(CATEGORICAL[0])
    expect(categorical(CATEGORICAL.length)).toBe(CATEGORICAL[0]) // wraps
    expect(categorical(CATEGORICAL.length + 2)).toBe(CATEGORICAL[2])
    expect(categorical(-1)).toBe(CATEGORICAL[CATEGORICAL.length - 1])
  })

  it('divergingColor maps sign to neg/mid/pos', () => {
    expect(divergingColor(0.5)).toBe('var(--div-pos)')
    expect(divergingColor(-0.5)).toBe('var(--div-neg)')
    expect(divergingColor(0)).toBe('var(--div-mid)')
  })

  it('sequentialColor clamps and buckets [0,1]', () => {
    expect(sequentialColor(0)).toBe(SEQUENTIAL[0])
    expect(sequentialColor(1)).toBe(SEQUENTIAL[SEQUENTIAL.length - 1])
    expect(sequentialColor(-5)).toBe(SEQUENTIAL[0]) // clamped low
    expect(sequentialColor(99)).toBe(SEQUENTIAL[SEQUENTIAL.length - 1]) // clamped high
  })

  it('all palette entries are token-driven (var(--…))', () => {
    for (const c of [...CATEGORICAL, ...SEQUENTIAL]) expect(c.startsWith('var(--')).toBe(true)
  })
})
