import { describe, it, expect } from 'vitest'
import { resources } from './index'
import { NAMESPACES } from './config'

function flatKeys(obj: unknown, prefix = ''): string[] {
  if (!obj || typeof obj !== 'object') return [prefix.replace(/\.$/, '')]
  return Object.entries(obj as Record<string, unknown>).flatMap(([k, v]) =>
    v && typeof v === 'object' ? flatKeys(v, `${prefix}${k}.`) : [`${prefix}${k}`],
  )
}

describe('i18n key parity (zh-TW vs en)', () => {
  for (const ns of NAMESPACES) {
    it(`namespace "${ns}" has identical keys in both languages`, () => {
      const zh = flatKeys((resources['zh-TW'] as Record<string, unknown>)[ns]).sort()
      const en = flatKeys((resources.en as Record<string, unknown>)[ns]).sort()
      expect(en).toEqual(zh)
    })
  }
})
