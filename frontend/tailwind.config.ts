import type { Config } from 'tailwindcss'

// Grok 單色 dark v2.0 — token 真相源 dev_docs/web_design/global/02_backtest_platform_brand_system.md
// 顏色一律走 CSS vars（見 src/styles/tokens.css），這裡只做映射。
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        base: 'var(--bg-base)',
        surface: 'var(--bg-surface)',
        input: 'var(--bg-input)',
        code: 'var(--bg-code)',
        border: 'var(--border-default)',
        text: {
          DEFAULT: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          muted: 'var(--text-muted)',
        },
        gain: 'var(--gain)',
        loss: 'var(--loss)',
        'loss-aaa': 'var(--loss-aaa)',
        warning: 'var(--warning)',
        error: 'var(--error)',
      },
      fontFamily: {
        sans: ['Inter', 'Noto Sans TC', 'system-ui', 'sans-serif'],
        mono: ['Geist Mono', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        pill: '9999px',
        lg: '12px',
        md: '8px',
        sm: '4px',
      },
      boxShadow: {
        // flat 分層：本系統無陰影，一律 1px border
        none: 'none',
      },
      ringColor: {
        focus: 'var(--focus-ring)',
      },
    },
  },
  plugins: [],
} satisfies Config
