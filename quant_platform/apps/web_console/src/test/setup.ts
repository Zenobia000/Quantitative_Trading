import '@testing-library/jest-dom/vitest'
import { beforeAll } from 'vitest'
import { i18n } from '@/i18n'

// 測試 i18n 固定 zh-TW：未改動的既有中文斷言逐字命中，零修改通過。
beforeAll(() => {
  void i18n.changeLanguage('zh-TW')
})

// jsdom 無 matchMedia：提供最小 mock（ThemeProvider system 模式所需，預設 matches:false → light）
if (typeof window !== 'undefined' && !window.matchMedia) {
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia
}
