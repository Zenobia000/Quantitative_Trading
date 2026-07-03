/*
 * i18n 初始化（side-effect）。靜態 bundle 所有 resource → 無需 http-backend / Suspense，
 * t() 首次 render 即同步解析（測試同步、無需 provider wrapper）。
 * 預設 zh-TW；使用者選擇存 localStorage（見 config）。
 */
import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import { DEFAULT_LNG, DEFAULT_NS, NAMESPACES, readStoredLng } from './config'

import commonZh from './resources/zh-TW/common.json'
import navZh from './resources/zh-TW/nav.json'
import homeZh from './resources/zh-TW/home.json'
import researchZh from './resources/zh-TW/research.json'
import liveOosZh from './resources/zh-TW/liveOos.json'
import monitorZh from './resources/zh-TW/monitor.json'
import systemZh from './resources/zh-TW/system.json'
import statusZh from './resources/zh-TW/status.json'
import errorsZh from './resources/zh-TW/errors.json'
import sectionsZh from './resources/zh-TW/sections.json'

import commonEn from './resources/en/common.json'
import navEn from './resources/en/nav.json'
import homeEn from './resources/en/home.json'
import researchEn from './resources/en/research.json'
import liveOosEn from './resources/en/liveOos.json'
import monitorEn from './resources/en/monitor.json'
import systemEn from './resources/en/system.json'
import statusEn from './resources/en/status.json'
import errorsEn from './resources/en/errors.json'
import sectionsEn from './resources/en/sections.json'

export const resources = {
  'zh-TW': {
    common: commonZh,
    nav: navZh,
    home: homeZh,
    research: researchZh,
    liveOos: liveOosZh,
    monitor: monitorZh,
    system: systemZh,
    status: statusZh,
    errors: errorsZh,
    sections: sectionsZh,
  },
  en: {
    common: commonEn,
    nav: navEn,
    home: homeEn,
    research: researchEn,
    liveOos: liveOosEn,
    monitor: monitorEn,
    system: systemEn,
    status: statusEn,
    errors: errorsEn,
    sections: sectionsEn,
  },
} as const

if (!i18n.isInitialized) {
  void i18n.use(initReactI18next).init({
    resources,
    lng: readStoredLng() ?? DEFAULT_LNG,
    fallbackLng: DEFAULT_LNG,
    ns: NAMESPACES as unknown as string[],
    defaultNS: DEFAULT_NS,
    interpolation: { escapeValue: false },
    react: { useSuspense: false },
  })
}

export { i18n }
export default i18n
